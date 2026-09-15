from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import EhDonoOuGerente, PertenceALoja
from apps.core.utils import para_centavos
from apps.core.views import LojaViewSetMixin
from apps.produtos.models import Variacao

from .models import MovimentoEstoque
from .serializers import (
    AjusteInventarioSerializer,
    MovimentoEstoqueSerializer,
    PosicaoEstoqueSerializer,
    RegistrarMovimentoSerializer,
)
from .servicos import ajustar_para_contagem, atualizar_custo_medio, registrar_movimento


class MovimentoEstoqueViewSet(LojaViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Extrato de estoque (somente leitura — movimento é imutável).

    Para criar movimentos use as ações `entrada`, `perda`, `devolucao` e
    `inventario`, que passam pelo serviço transacional.
    """

    queryset = MovimentoEstoque.objects.select_related(
        "variacao", "variacao__produto", "usuario"
    )
    serializer_class = MovimentoEstoqueSerializer
    permission_classes = [PertenceALoja]
    filterset_fields = ["tipo", "variacao", "usuario"]
    search_fields = ["variacao__produto__nome", "variacao__sabor", "motivo", "documento"]
    ordering_fields = ["criado_em"]

    def _registrar(self, request, tipo):
        serializer = RegistrarMovimentoSerializer(
            data={**request.data, "tipo": tipo}, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        custo_centavos = dados.get("custo_unitario_centavos")
        custo = None
        if custo_centavos is not None:
            from apps.core.utils import de_centavos

            custo = de_centavos(custo_centavos)

        movimento = registrar_movimento(
            variacao=dados["variacao"],
            tipo=tipo,
            quantidade=dados["quantidade"],
            usuario=request.user,
            custo_unitario=custo,
            motivo=dados.get("motivo", ""),
            documento=dados.get("documento", ""),
        )

        # Entrada manual com custo informado recalcula o custo médio.
        if tipo == "entrada" and custo is not None:
            atualizar_custo_medio(
                variacao=dados["variacao"],
                quantidade_entrada=dados["quantidade"],
                custo_unitario=custo,
            )

        return Response(MovimentoEstoqueSerializer(movimento).data, status=201)

    @extend_schema(request=RegistrarMovimentoSerializer, responses=MovimentoEstoqueSerializer)
    @action(detail=False, methods=["post"], permission_classes=[EhDonoOuGerente])
    def entrada(self, request):
        """POST /api/estoque/movimentos/entrada — entrada avulsa."""
        return self._registrar(request, "entrada")

    @extend_schema(request=RegistrarMovimentoSerializer, responses=MovimentoEstoqueSerializer)
    @action(detail=False, methods=["post"], permission_classes=[EhDonoOuGerente])
    def perda(self, request):
        """POST /api/estoque/movimentos/perda — quebra, vencimento, furto."""
        return self._registrar(request, "perda")

    @extend_schema(request=RegistrarMovimentoSerializer, responses=MovimentoEstoqueSerializer)
    @action(detail=False, methods=["post"], permission_classes=[PertenceALoja])
    def devolucao(self, request):
        """POST /api/estoque/movimentos/devolucao — cliente devolveu o item."""
        return self._registrar(request, "devolucao")

    @extend_schema(request=AjusteInventarioSerializer, responses=MovimentoEstoqueSerializer)
    @action(detail=False, methods=["post"], permission_classes=[EhDonoOuGerente])
    def inventario(self, request):
        """POST /api/estoque/movimentos/inventario — ajuste por contagem física."""
        serializer = AjusteInventarioSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        movimento = ajustar_para_contagem(
            variacao=dados["variacao"],
            contagem=dados["contagem"],
            usuario=request.user,
            motivo=dados.get("motivo", ""),
        )
        if movimento is None:
            return Response({"detalhe": "A contagem confere com o saldo. Nada a ajustar."})
        return Response(MovimentoEstoqueSerializer(movimento).data, status=201)


class PosicaoEstoqueViewSet(LojaViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """Posição atual do estoque, com valorização a custo e a venda."""

    queryset = Variacao.objects.select_related("produto", "produto__categoria")
    serializer_class = PosicaoEstoqueSerializer
    permission_classes = [PertenceALoja]
    search_fields = ["produto__nome", "sabor", "sku"]
    ordering_fields = ["saldo", "produto__nome"]
    filterset_fields = ["ativo", "produto"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("abaixo_do_minimo") in ("1", "true", "True"):
            queryset = queryset.filter(estoque_minimo__gt=0, saldo__lte=F("estoque_minimo"))
        if self.request.query_params.get("zerados") in ("1", "true", "True"):
            queryset = queryset.filter(saldo__lte=0)
        return queryset

    @extend_schema(responses=dict)
    @action(detail=False, methods=["get"])
    def resumo(self, request):
        """GET /api/estoque/posicao/resumo — totais para o dashboard."""
        base = self.get_queryset().filter(ativo=True)
        decimal = DecimalField(max_digits=16, decimal_places=2)

        agregado = base.filter(saldo__gt=0).aggregate(
            unidades=Sum("saldo"),
            valor_custo=Sum(
                ExpressionWrapper(F("saldo") * F("preco_custo"), output_field=decimal)
            ),
            valor_venda=Sum(
                ExpressionWrapper(F("saldo") * F("preco_venda"), output_field=decimal)
            ),
        )

        return Response({
            "variacoes_ativas": base.count(),
            "unidades_em_estoque": agregado["unidades"] or 0,
            "valor_custo_centavos": para_centavos(agregado["valor_custo"] or 0),
            "valor_venda_centavos": para_centavos(agregado["valor_venda"] or 0),
            "abaixo_do_minimo": base.filter(
                estoque_minimo__gt=0, saldo__lte=F("estoque_minimo")
            ).count(),
            "zerados": base.filter(saldo__lte=0).count(),
        })
