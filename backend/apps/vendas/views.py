from django.db import transaction
from django.db.models import Count, Sum
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import ErroDeNegocio
from apps.core.permissions import EhDonoOuGerente, PertenceALoja
from apps.core.utils import de_centavos, para_centavos
from apps.core.views import LojaViewSetMixin

from .models import Caixa, StatusVenda, Venda
from .serializers import (
    AbrirCaixaSerializer,
    CaixaSerializer,
    CancelarVendaSerializer,
    CriarVendaSerializer,
    FecharCaixaSerializer,
    FinalizarVendaSerializer,
    MovimentarCaixaSerializer,
    MovimentoCaixaSerializer,
    VendaRapidaSerializer,
    VendaResumoSerializer,
    VendaSerializer,
)
from .servicos import (
    abrir_caixa,
    caixa_aberto,
    calcular_saldo_do_caixa,
    cancelar_venda,
    criar_venda,
    fechar_caixa,
    finalizar_venda,
    movimentar_caixa,
)


def _converter_itens(itens):
    """Traduz os centavos da API para os Decimais que o serviço espera."""
    convertidos = []
    for item in itens:
        entrada = {"variacao": item["variacao"], "quantidade": item["quantidade"]}
        if item.get("preco_unitario_centavos") is not None:
            entrada["preco_unitario"] = de_centavos(item["preco_unitario_centavos"])
        entrada["desconto"] = de_centavos(item.get("desconto_centavos", 0))
        convertidos.append(entrada)
    return convertidos


def _converter_pagamentos(pagamentos):
    return [
        {
            "forma": pagamento["forma"],
            "valor": de_centavos(pagamento["valor_centavos"]),
            "observacao": pagamento.get("observacao", ""),
        }
        for pagamento in pagamentos
    ]


class CaixaViewSet(LojaViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """Sessões de caixa. Abertura e fechamento são ações, não CRUD."""

    queryset = Caixa.objects.select_related("usuario_abertura", "usuario_fechamento")
    serializer_class = CaixaSerializer
    permission_classes = [PertenceALoja]
    filterset_fields = ["status"]
    ordering_fields = ["aberto_em", "fechado_em"]

    @extend_schema(responses=CaixaSerializer)
    @action(detail=False, methods=["get"])
    def atual(self, request):
        """GET /api/caixas/atual — o caixa aberto, com saldo em tempo real."""
        caixa = caixa_aberto(request.loja)
        if caixa is None:
            return Response({"aberto": False, "caixa": None})

        dados = CaixaSerializer(caixa).data
        return Response({
            "aberto": True,
            "caixa": dados,
            "saldo_atual_centavos": para_centavos(calcular_saldo_do_caixa(caixa)),
            "vendas_no_caixa": caixa.vendas.filter(status=StatusVenda.FINALIZADA).count(),
        })

    @extend_schema(request=AbrirCaixaSerializer, responses=CaixaSerializer)
    @action(detail=False, methods=["post"])
    def abrir(self, request):
        """POST /api/caixas/abrir — inicia a sessão de caixa."""
        serializer = AbrirCaixaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        caixa = abrir_caixa(
            loja=request.loja,
            usuario=request.user,
            saldo_inicial=de_centavos(serializer.validated_data["saldo_inicial_centavos"]),
        )
        return Response(CaixaSerializer(caixa).data, status=201)

    @extend_schema(request=FecharCaixaSerializer, responses=CaixaSerializer)
    @action(detail=True, methods=["post"])
    def fechar(self, request, pk=None):
        """POST /api/caixas/{id}/fechar — confere a gaveta e encerra."""
        serializer = FecharCaixaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        caixa = fechar_caixa(
            caixa=self.get_object(),
            usuario=request.user,
            saldo_informado=de_centavos(serializer.validated_data["saldo_informado_centavos"]),
            observacoes=serializer.validated_data.get("observacoes", ""),
        )
        return Response(CaixaSerializer(caixa).data)

    @extend_schema(request=MovimentarCaixaSerializer, responses=MovimentoCaixaSerializer)
    @action(detail=True, methods=["post"])
    def movimentar(self, request, pk=None):
        """POST /api/caixas/{id}/movimentar — sangria ou suprimento."""
        serializer = MovimentarCaixaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movimento = movimentar_caixa(
            caixa=self.get_object(),
            usuario=request.user,
            tipo=serializer.validated_data["tipo"],
            valor=de_centavos(serializer.validated_data["valor_centavos"]),
            descricao=serializer.validated_data.get("descricao", ""),
        )
        return Response(MovimentoCaixaSerializer(movimento).data, status=201)

    @extend_schema(responses=dict)
    @action(detail=True, methods=["get"])
    def conferencia(self, request, pk=None):
        """
        GET /api/caixas/{id}/conferencia — relatório de fechamento.

        Separa o que está na gaveta (dinheiro) do que caiu em Pix, cartão e
        fiado, que é exatamente a conta que o lojista faz no fim do dia.
        """
        from .models import FormaPagamento, Pagamento

        caixa = self.get_object()
        vendas = caixa.vendas.filter(status=StatusVenda.FINALIZADA)

        por_forma = (
            Pagamento.objects.filter(venda__in=vendas)
            .values("forma")
            .annotate(total=Sum("valor"), troco=Sum("troco"), quantidade=Count("id"))
        )
        formas = {
            linha["forma"]: {
                "forma": linha["forma"],
                "forma_display": dict(FormaPagamento.choices)[linha["forma"]],
                "total_centavos": para_centavos(linha["total"]),
                "troco_centavos": para_centavos(linha["troco"] or 0),
                "quantidade": linha["quantidade"],
            }
            for linha in por_forma
        }

        movimentos = caixa.movimentos.select_related("usuario").all()
        return Response({
            "caixa": CaixaSerializer(caixa).data,
            "saldo_atual_centavos": para_centavos(calcular_saldo_do_caixa(caixa)),
            "total_vendas": vendas.count(),
            "total_vendido_centavos": para_centavos(
                vendas.aggregate(total=Sum("total"))["total"] or 0
            ),
            "por_forma_pagamento": list(formas.values()),
            "movimentos": MovimentoCaixaSerializer(movimentos, many=True).data,
        })


class VendaViewSet(LojaViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Vendas. Criação e finalização passam por ações que usam os serviços —
    não há `POST /api/vendas` genérico, porque venda não é um CRUD.
    """

    queryset = Venda.objects.select_related("cliente", "usuario", "caixa").prefetch_related(
        "itens", "pagamentos"
    )
    serializer_class = VendaSerializer
    permission_classes = [PertenceALoja]
    filterset_fields = ["status", "cliente", "usuario", "caixa"]
    search_fields = ["numero", "cliente__nome", "observacoes"]
    ordering_fields = ["criado_em", "finalizada_em", "total", "numero"]

    def get_serializer_class(self):
        if self.action == "list":
            return VendaResumoSerializer
        return VendaSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            queryset = queryset.annotate(quantidade_itens=Count("itens"))
        parametros = self.request.query_params
        if parametros.get("data_inicio"):
            queryset = queryset.filter(criado_em__date__gte=parametros["data_inicio"])
        if parametros.get("data_fim"):
            queryset = queryset.filter(criado_em__date__lte=parametros["data_fim"])
        return queryset

    @extend_schema(request=CriarVendaSerializer, responses=VendaSerializer)
    @action(detail=False, methods=["post"])
    def abrir(self, request):
        """POST /api/vendas/abrir — cria venda em aberto (sem baixar estoque)."""
        serializer = CriarVendaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        venda = criar_venda(
            loja=request.loja,
            usuario=request.user,
            itens=_converter_itens(dados["itens"]),
            cliente=dados.get("cliente"),
            desconto=de_centavos(dados.get("desconto_centavos", 0)),
            observacoes=dados.get("observacoes", ""),
        )
        return Response(VendaSerializer(venda).data, status=201)

    @extend_schema(request=FinalizarVendaSerializer, responses=VendaSerializer)
    @action(detail=True, methods=["post"])
    def finalizar(self, request, pk=None):
        """POST /api/vendas/{id}/finalizar — baixa estoque e recebe."""
        serializer = FinalizarVendaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        venda = finalizar_venda(
            venda=self.get_object(),
            usuario=request.user,
            pagamentos=_converter_pagamentos(serializer.validated_data["pagamentos"]),
        )
        return Response(VendaSerializer(venda).data)

    @extend_schema(request=VendaRapidaSerializer, responses=VendaSerializer)
    @action(detail=False, methods=["post"], url_path="rapida")
    @transaction.atomic
    def rapida(self, request):
        """POST /api/vendas/rapida — cria e finaliza em uma chamada (balcão)."""
        serializer = VendaRapidaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        venda = criar_venda(
            loja=request.loja,
            usuario=request.user,
            itens=_converter_itens(dados["itens"]),
            cliente=dados.get("cliente"),
            desconto=de_centavos(dados.get("desconto_centavos", 0)),
            observacoes=dados.get("observacoes", ""),
        )
        venda = finalizar_venda(
            venda=venda,
            usuario=request.user,
            pagamentos=_converter_pagamentos(dados["pagamentos"]),
        )
        return Response(VendaSerializer(venda).data, status=201)

    @extend_schema(request=CancelarVendaSerializer, responses=VendaSerializer)
    @action(detail=True, methods=["post"], permission_classes=[EhDonoOuGerente])
    def cancelar(self, request, pk=None):
        """POST /api/vendas/{id}/cancelar — estorna estoque, caixa e financeiro."""
        serializer = CancelarVendaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        venda = cancelar_venda(
            venda=self.get_object(),
            usuario=request.user,
            motivo=serializer.validated_data.get("motivo", ""),
        )
        return Response(VendaSerializer(venda).data)

    @extend_schema(responses=dict)
    @action(detail=True, methods=["get"])
    def recibo(self, request, pk=None):
        """
        GET /api/vendas/{id}/recibo — dados do comprovante.

        Documento **não fiscal** (ADR-0003); a ressalva vai impressa.
        """
        venda = self.get_object()
        if venda.status != StatusVenda.FINALIZADA:
            raise ErroDeNegocio("Só é possível emitir recibo de venda finalizada.")

        configuracao = getattr(venda.loja, "configuracao", None)
        return Response({
            "loja": {
                "nome": venda.loja.nome,
                "telefone": venda.loja.telefone,
                "endereco": venda.loja.endereco,
                "cidade": venda.loja.cidade,
            },
            "venda": VendaSerializer(venda).data,
            "mensagem": getattr(configuracao, "mensagem_recibo", ""),
            "aviso": "Documento sem valor fiscal.",
        })
