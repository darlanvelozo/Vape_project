from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import ErroDeNegocio
from apps.core.permissions import EhDonoOuGerente
from apps.core.utils import para_centavos
from apps.core.views import LojaViewSet

from .models import CategoriaFinanceira, Lancamento, StatusLancamento, TipoLancamento
from .serializers import (
    BaixarLancamentoSerializer,
    CategoriaFinanceiraSerializer,
    LancamentoSerializer,
)


class CategoriaFinanceiraViewSet(LojaViewSet):
    queryset = CategoriaFinanceira.objects.all()
    serializer_class = CategoriaFinanceiraSerializer
    permission_classes = [EhDonoOuGerente]
    filterset_fields = ["tipo", "ativo"]
    search_fields = ["nome"]


class LancamentoViewSet(LojaViewSet):
    """
    Contas a pagar e a receber.

    Financeiro é informação sensível do negócio: só dono e gerente acessam.
    """

    queryset = Lancamento.objects.select_related("categoria", "cliente", "fornecedor")
    serializer_class = LancamentoSerializer
    permission_classes = [EhDonoOuGerente]
    filterset_fields = ["tipo", "status", "categoria", "cliente", "fornecedor"]
    search_fields = ["descricao", "observacoes", "cliente__nome", "fornecedor__nome"]
    ordering_fields = ["vencimento", "valor", "criado_em", "pago_em"]

    def get_queryset(self):
        queryset = super().get_queryset()
        parametros = self.request.query_params

        if parametros.get("vencimento_inicio"):
            queryset = queryset.filter(vencimento__gte=parametros["vencimento_inicio"])
        if parametros.get("vencimento_fim"):
            queryset = queryset.filter(vencimento__lte=parametros["vencimento_fim"])
        if parametros.get("atrasados") in ("1", "true", "True"):
            queryset = queryset.filter(
                status=StatusLancamento.PENDENTE, vencimento__lt=timezone.localdate()
            )
        return queryset

    def perform_destroy(self, instancia):
        if instancia.venda_id or instancia.compra_id:
            raise ErroDeNegocio(
                "Lançamento gerado por venda ou compra não pode ser excluído — "
                "cancele a venda/compra de origem.",
                campo="id",
            )
        instancia.delete()

    @extend_schema(request=BaixarLancamentoSerializer, responses=LancamentoSerializer)
    @action(detail=True, methods=["post"])
    def baixar(self, request, pk=None):
        """POST /api/financeiro/lancamentos/{id}/baixar — marca como pago."""
        lancamento = self.get_object()
        if lancamento.status == StatusLancamento.PAGO:
            raise ErroDeNegocio("Este lançamento já está baixado.", campo="status")
        if lancamento.status == StatusLancamento.CANCELADO:
            raise ErroDeNegocio("Lançamento cancelado não pode ser baixado.", campo="status")

        serializer = BaixarLancamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lancamento.status = StatusLancamento.PAGO
        lancamento.pago_em = serializer.validated_data.get("pago_em") or timezone.localdate()
        lancamento.forma_pagamento = serializer.validated_data.get(
            "forma_pagamento", lancamento.forma_pagamento
        )
        lancamento.save(update_fields=["status", "pago_em", "forma_pagamento", "atualizado_em"])
        return Response(self.get_serializer(lancamento).data)

    @extend_schema(responses=LancamentoSerializer)
    @action(detail=True, methods=["post"])
    def estornar(self, request, pk=None):
        """POST /api/financeiro/lancamentos/{id}/estornar — volta para pendente."""
        lancamento = self.get_object()
        if lancamento.status != StatusLancamento.PAGO:
            raise ErroDeNegocio("Só é possível estornar lançamento baixado.", campo="status")

        lancamento.status = StatusLancamento.PENDENTE
        lancamento.pago_em = None
        lancamento.save(update_fields=["status", "pago_em", "atualizado_em"])
        return Response(self.get_serializer(lancamento).data)

    @extend_schema(responses=dict)
    @action(detail=False, methods=["get"])
    def resumo(self, request):
        """
        GET /api/financeiro/lancamentos/resumo — painel do financeiro.

        Recorte padrão: os próximos 30 dias, que é o horizonte que o lojista
        olha para saber se o mês fecha.
        """
        hoje = timezone.localdate()
        limite = hoje + timedelta(days=int(request.query_params.get("dias", 30)))
        base = self.get_queryset()

        def somar(consulta):
            return para_centavos(consulta.aggregate(total=Sum("valor"))["total"] or 0)

        pendentes = base.filter(status=StatusLancamento.PENDENTE)
        pagos_no_mes = base.filter(
            status=StatusLancamento.PAGO, pago_em__year=hoje.year, pago_em__month=hoje.month
        )

        return Response({
            "a_receber_centavos": somar(pendentes.filter(tipo=TipoLancamento.RECEITA)),
            "a_pagar_centavos": somar(pendentes.filter(tipo=TipoLancamento.DESPESA)),
            "a_receber_atrasado_centavos": somar(
                pendentes.filter(tipo=TipoLancamento.RECEITA, vencimento__lt=hoje)
            ),
            "a_pagar_atrasado_centavos": somar(
                pendentes.filter(tipo=TipoLancamento.DESPESA, vencimento__lt=hoje)
            ),
            "a_receber_periodo_centavos": somar(
                pendentes.filter(tipo=TipoLancamento.RECEITA, vencimento__range=(hoje, limite))
            ),
            "a_pagar_periodo_centavos": somar(
                pendentes.filter(tipo=TipoLancamento.DESPESA, vencimento__range=(hoje, limite))
            ),
            "recebido_no_mes_centavos": somar(pagos_no_mes.filter(tipo=TipoLancamento.RECEITA)),
            "pago_no_mes_centavos": somar(pagos_no_mes.filter(tipo=TipoLancamento.DESPESA)),
            "quantidade_atrasados": pendentes.filter(vencimento__lt=hoje).count(),
        })

    @extend_schema(responses=dict)
    @action(detail=False, methods=["get"], url_path="fluxo-de-caixa")
    def fluxo_de_caixa(self, request):
        """GET /api/financeiro/lancamentos/fluxo-de-caixa — realizado por dia."""
        hoje = timezone.localdate()
        inicio = request.query_params.get("inicio") or (hoje - timedelta(days=30)).isoformat()
        fim = request.query_params.get("fim") or hoje.isoformat()

        movimentos = (
            self.get_queryset()
            .filter(status=StatusLancamento.PAGO, pago_em__range=(inicio, fim))
            .values("pago_em", "tipo")
            .annotate(total=Sum("valor"))
            .order_by("pago_em")
        )

        por_dia: dict[str, dict] = {}
        for linha in movimentos:
            dia = linha["pago_em"].isoformat()
            registro = por_dia.setdefault(
                dia, {"data": dia, "entradas_centavos": 0, "saidas_centavos": 0}
            )
            chave = (
                "entradas_centavos"
                if linha["tipo"] == TipoLancamento.RECEITA
                else "saidas_centavos"
            )
            registro[chave] += para_centavos(linha["total"])

        dias = sorted(por_dia.values(), key=lambda linha: linha["data"])
        acumulado = 0
        for dia in dias:
            dia["saldo_centavos"] = dia["entradas_centavos"] - dia["saidas_centavos"]
            acumulado += dia["saldo_centavos"]
            dia["acumulado_centavos"] = acumulado

        return Response({
            "inicio": inicio,
            "fim": fim,
            "dias": dias,
            "total_entradas_centavos": sum(d["entradas_centavos"] for d in dias),
            "total_saidas_centavos": sum(d["saidas_centavos"] for d in dias),
            "saldo_centavos": acumulado,
        })
