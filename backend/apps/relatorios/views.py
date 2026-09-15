"""
Relatórios e dashboard.

Tudo aqui é leitura agregada. Os endpoints recortam pela loja do usuário
usando `request.loja`, populado por `apps.core.views.LojaViewSetMixin` — como
estas views não são ViewSets de modelo, o recorte é aplicado à mão em
`_base_vendas` e companhia.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clientes.models import Cliente
from apps.core.permissions import EhDonoOuGerente, PertenceALoja
from apps.core.utils import para_centavos
from apps.financeiro.models import Lancamento, StatusLancamento, TipoLancamento
from apps.produtos.models import Variacao
from apps.vendas.models import ItemVenda, StatusVenda, Venda
from apps.vendas.servicos import caixa_aberto, calcular_saldo_do_caixa

DECIMAL = DecimalField(max_digits=16, decimal_places=2)


class BaseRelatorioView(APIView):
    """Resolve a loja e o período pedido na querystring."""

    permission_classes = [PertenceALoja]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        request.loja = getattr(request.user, "loja", None)

    def periodo(self, request):
        hoje = timezone.localdate()
        inicio = request.query_params.get("inicio")
        fim = request.query_params.get("fim")
        if not inicio:
            inicio = (hoje - timedelta(days=30)).isoformat()
        if not fim:
            fim = hoje.isoformat()
        return inicio, fim

    def vendas_finalizadas(self, request, inicio=None, fim=None):
        consulta = Venda.objects.filter(loja=request.loja, status=StatusVenda.FINALIZADA)
        if inicio:
            consulta = consulta.filter(finalizada_em__date__gte=inicio)
        if fim:
            consulta = consulta.filter(finalizada_em__date__lte=fim)
        return consulta


class DashboardView(BaseRelatorioView):
    """GET /api/relatorios/dashboard — a primeira tela do sistema."""

    @extend_schema(responses=dict)
    def get(self, request):
        hoje = timezone.localdate()
        inicio_mes = hoje.replace(day=1)

        vendas_hoje = self.vendas_finalizadas(request, hoje, hoje)
        vendas_mes = self.vendas_finalizadas(request, inicio_mes, hoje)

        agregado_hoje = vendas_hoje.aggregate(
            total=Sum("total"), custo=Sum("custo_total"), quantidade=Count("id")
        )
        agregado_mes = vendas_mes.aggregate(
            total=Sum("total"), custo=Sum("custo_total"), quantidade=Count("id")
        )

        total_hoje = agregado_hoje["total"] or Decimal("0.00")
        total_mes = agregado_mes["total"] or Decimal("0.00")
        quantidade_hoje = agregado_hoje["quantidade"] or 0
        quantidade_mes = agregado_mes["quantidade"] or 0

        # --- estoque ---
        variacoes = Variacao.objects.filter(loja=request.loja, ativo=True)
        estoque = variacoes.filter(saldo__gt=0).aggregate(
            unidades=Sum("saldo"),
            valor_custo=Sum(ExpressionWrapper(F("saldo") * F("preco_custo"), output_field=DECIMAL)),
        )

        # --- financeiro ---
        pendentes = Lancamento.objects.filter(
            loja=request.loja, status=StatusLancamento.PENDENTE
        )

        # --- caixa ---
        caixa = caixa_aberto(request.loja)

        return Response({
            "hoje": {
                "vendas": quantidade_hoje,
                "faturamento_centavos": para_centavos(total_hoje),
                "lucro_centavos": para_centavos(total_hoje - (agregado_hoje["custo"] or 0)),
                "ticket_medio_centavos": (
                    para_centavos(total_hoje / quantidade_hoje) if quantidade_hoje else 0
                ),
            },
            "mes": {
                "vendas": quantidade_mes,
                "faturamento_centavos": para_centavos(total_mes),
                "lucro_centavos": para_centavos(total_mes - (agregado_mes["custo"] or 0)),
                "ticket_medio_centavos": (
                    para_centavos(total_mes / quantidade_mes) if quantidade_mes else 0
                ),
            },
            "estoque": {
                "unidades": estoque["unidades"] or 0,
                "valor_custo_centavos": para_centavos(estoque["valor_custo"] or 0),
                "abaixo_do_minimo": variacoes.filter(
                    estoque_minimo__gt=0, saldo__lte=F("estoque_minimo")
                ).count(),
                "zerados": variacoes.filter(saldo__lte=0).count(),
            },
            "financeiro": {
                "a_receber_centavos": para_centavos(
                    pendentes.filter(tipo=TipoLancamento.RECEITA).aggregate(
                        t=Sum("valor"))["t"] or 0
                ),
                "a_pagar_centavos": para_centavos(
                    pendentes.filter(tipo=TipoLancamento.DESPESA).aggregate(
                        t=Sum("valor"))["t"] or 0
                ),
                "atrasados": pendentes.filter(vencimento__lt=hoje).count(),
            },
            "caixa": {
                "aberto": caixa is not None,
                "id": caixa.id if caixa else None,
                "saldo_centavos": para_centavos(calcular_saldo_do_caixa(caixa)) if caixa else 0,
                "aberto_em": caixa.aberto_em if caixa else None,
            },
            "clientes_ativos": Cliente.objects.filter(loja=request.loja, ativo=True).count(),
        })


class VendasPorPeriodoView(BaseRelatorioView):
    """GET /api/relatorios/vendas-por-periodo — série diária para o gráfico."""

    @extend_schema(responses=dict)
    def get(self, request):
        inicio, fim = self.periodo(request)
        vendas = (
            self.vendas_finalizadas(request, inicio, fim)
            .values("finalizada_em__date")
            .annotate(
                faturamento=Sum("total"), custo=Sum("custo_total"), quantidade=Count("id")
            )
            .order_by("finalizada_em__date")
        )

        dias = [
            {
                "data": linha["finalizada_em__date"].isoformat(),
                "vendas": linha["quantidade"],
                "faturamento_centavos": para_centavos(linha["faturamento"]),
                "lucro_centavos": para_centavos(linha["faturamento"] - (linha["custo"] or 0)),
            }
            for linha in vendas
        ]
        return Response({
            "inicio": inicio,
            "fim": fim,
            "dias": dias,
            "total_vendas": sum(d["vendas"] for d in dias),
            "total_faturamento_centavos": sum(d["faturamento_centavos"] for d in dias),
            "total_lucro_centavos": sum(d["lucro_centavos"] for d in dias),
        })


class MaisVendidosView(BaseRelatorioView):
    """GET /api/relatorios/mais-vendidos — ranking por unidade e por receita."""

    @extend_schema(responses=dict)
    def get(self, request):
        inicio, fim = self.periodo(request)
        limite = int(request.query_params.get("limite", 20))

        itens = (
            ItemVenda.objects.filter(venda__in=self.vendas_finalizadas(request, inicio, fim))
            .values("variacao_id", "descricao")
            .annotate(
                unidades=Sum("quantidade"),
                receita=Sum(
                    ExpressionWrapper(
                        F("quantidade") * F("preco_unitario") - F("desconto"),
                        output_field=DECIMAL,
                    )
                ),
                custo=Sum(
                    ExpressionWrapper(F("quantidade") * F("custo_unitario"), output_field=DECIMAL)
                ),
            )
            .order_by("-unidades")[:limite]
        )

        return Response({
            "inicio": inicio,
            "fim": fim,
            "itens": [
                {
                    "variacao": linha["variacao_id"],
                    "descricao": linha["descricao"],
                    "unidades": linha["unidades"],
                    "receita_centavos": para_centavos(linha["receita"]),
                    "lucro_centavos": para_centavos(linha["receita"] - (linha["custo"] or 0)),
                }
                for linha in itens
            ],
        })


class CurvaABCView(BaseRelatorioView):
    """
    GET /api/relatorios/curva-abc — classificação por participação na receita.

    A: até 80% acumulados · B: até 95% · C: o resto. É o corte clássico de
    Pareto e serve para decidir o que nunca pode faltar na prateleira.
    """

    permission_classes = [EhDonoOuGerente]

    @extend_schema(responses=dict)
    def get(self, request):
        inicio, fim = self.periodo(request)

        itens = list(
            ItemVenda.objects.filter(venda__in=self.vendas_finalizadas(request, inicio, fim))
            .values("variacao_id", "descricao")
            .annotate(
                unidades=Sum("quantidade"),
                receita=Sum(
                    ExpressionWrapper(
                        F("quantidade") * F("preco_unitario") - F("desconto"),
                        output_field=DECIMAL,
                    )
                ),
            )
            .order_by("-receita")
        )

        receita_total = sum((linha["receita"] or Decimal("0.00")) for linha in itens)
        resultado = []
        acumulado = Decimal("0.00")

        for linha in itens:
            receita = linha["receita"] or Decimal("0.00")
            acumulado += receita
            participacao = (receita / receita_total * 100) if receita_total else Decimal("0")
            percentual_acumulado = (
                (acumulado / receita_total * 100) if receita_total else Decimal("0")
            )
            # Corte clássico de Pareto: A concentra 80% da receita, B vai até 95%.
            if percentual_acumulado <= 80:
                classe = "A"
            elif percentual_acumulado <= 95:
                classe = "B"
            else:
                classe = "C"

            resultado.append({
                "variacao": linha["variacao_id"],
                "descricao": linha["descricao"],
                "unidades": linha["unidades"],
                "receita_centavos": para_centavos(receita),
                "participacao": float(round(participacao, 2)),
                "acumulado": float(round(percentual_acumulado, 2)),
                "classe": classe,
            })

        return Response({
            "inicio": inicio,
            "fim": fim,
            "receita_total_centavos": para_centavos(receita_total),
            "itens": resultado,
        })


class MargemPorProdutoView(BaseRelatorioView):
    """GET /api/relatorios/margem — margem realizada por item vendido."""

    permission_classes = [EhDonoOuGerente]

    @extend_schema(responses=dict)
    def get(self, request):
        inicio, fim = self.periodo(request)

        itens = (
            ItemVenda.objects.filter(venda__in=self.vendas_finalizadas(request, inicio, fim))
            .values("variacao_id", "descricao")
            .annotate(
                unidades=Sum("quantidade"),
                receita=Sum(
                    ExpressionWrapper(
                        F("quantidade") * F("preco_unitario") - F("desconto"),
                        output_field=DECIMAL,
                    )
                ),
                custo=Sum(
                    ExpressionWrapper(F("quantidade") * F("custo_unitario"), output_field=DECIMAL)
                ),
            )
            .order_by("-receita")
        )

        linhas = []
        for linha in itens:
            receita = linha["receita"] or Decimal("0.00")
            custo = linha["custo"] or Decimal("0.00")
            lucro = receita - custo
            margem = (lucro / receita * 100) if receita else Decimal("0")
            linhas.append({
                "variacao": linha["variacao_id"],
                "descricao": linha["descricao"],
                "unidades": linha["unidades"],
                "receita_centavos": para_centavos(receita),
                "custo_centavos": para_centavos(custo),
                "lucro_centavos": para_centavos(lucro),
                "margem": float(round(margem, 2)),
            })

        return Response({"inicio": inicio, "fim": fim, "itens": linhas})


class GiroDeEstoqueView(BaseRelatorioView):
    """
    GET /api/relatorios/giro — quantas vezes o estoque girou no período.

    Giro = unidades vendidas ÷ saldo atual. Saldo zero com venda no período
    aparece como `None`: é ruptura, não giro infinito.
    """

    permission_classes = [EhDonoOuGerente]

    @extend_schema(responses=dict)
    def get(self, request):
        inicio, fim = self.periodo(request)

        vendidos = {
            linha["variacao_id"]: linha["unidades"]
            for linha in ItemVenda.objects.filter(
                venda__in=self.vendas_finalizadas(request, inicio, fim)
            ).values("variacao_id").annotate(unidades=Sum("quantidade"))
        }

        linhas = []
        variacoes = Variacao.objects.filter(loja=request.loja, ativo=True).select_related("produto")
        for variacao in variacoes:
            unidades = vendidos.get(variacao.id, 0)
            if unidades == 0 and variacao.saldo == 0:
                continue
            giro = round(unidades / variacao.saldo, 2) if variacao.saldo > 0 else None
            linhas.append({
                "variacao": variacao.id,
                "descricao": variacao.descricao_completa,
                "unidades_vendidas": unidades,
                "saldo_atual": variacao.saldo,
                "giro": giro,
                "parado": unidades == 0 and variacao.saldo > 0,
            })

        linhas.sort(key=lambda linha: (linha["giro"] is None, -(linha["giro"] or 0)))
        return Response({"inicio": inicio, "fim": fim, "itens": linhas})


class VendasPorFormaPagamentoView(BaseRelatorioView):
    """GET /api/relatorios/formas-pagamento — composição do recebimento."""

    @extend_schema(responses=dict)
    def get(self, request):
        from apps.vendas.models import FormaPagamento, Pagamento

        inicio, fim = self.periodo(request)
        linhas = (
            Pagamento.objects.filter(venda__in=self.vendas_finalizadas(request, inicio, fim))
            .values("forma")
            .annotate(total=Sum("valor"), troco=Sum("troco"), quantidade=Count("id"))
            .order_by("-total")
        )
        rotulos = dict(FormaPagamento.choices)

        return Response({
            "inicio": inicio,
            "fim": fim,
            "formas": [
                {
                    "forma": linha["forma"],
                    "forma_display": rotulos.get(linha["forma"], linha["forma"]),
                    "quantidade": linha["quantidade"],
                    "total_centavos": para_centavos(
                        (linha["total"] or 0) - (linha["troco"] or 0)
                    ),
                }
                for linha in linhas
            ],
        })


class VendasPorVendedorView(BaseRelatorioView):
    """GET /api/relatorios/vendedores — desempenho da equipe."""

    permission_classes = [EhDonoOuGerente]

    @extend_schema(responses=dict)
    def get(self, request):
        inicio, fim = self.periodo(request)
        linhas = (
            self.vendas_finalizadas(request, inicio, fim)
            .values("usuario_id", "usuario__nome")
            .annotate(quantidade=Count("id"), total=Sum("total"), custo=Sum("custo_total"))
            .order_by("-total")
        )

        return Response({
            "inicio": inicio,
            "fim": fim,
            "vendedores": [
                {
                    "usuario": linha["usuario_id"],
                    "nome": linha["usuario__nome"],
                    "vendas": linha["quantidade"],
                    "faturamento_centavos": para_centavos(linha["total"]),
                    "lucro_centavos": para_centavos(linha["total"] - (linha["custo"] or 0)),
                    "ticket_medio_centavos": para_centavos(
                        linha["total"] / linha["quantidade"]
                    ) if linha["quantidade"] else 0,
                }
                for linha in linhas
            ],
        })
