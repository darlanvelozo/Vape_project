"""
Financeiro na visão de gestão.

O erro mais caro aqui é silencioso: um número que fecha sozinho mas mente
sobre o negócio. Dois exemplos cobertos abaixo:

- compra à vista que não vira despesa faz a loja parecer mais lucrativa do
  que é;
- contar a compra como despesa **e** o custo da mercadoria vendida cobra o
  mesmo custo duas vezes, e no mês errado.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.financeiro.models import (
    CategoriaFinanceira,
    Lancamento,
    StatusLancamento,
    TipoLancamento,
)
from apps.fornecedores.models import Compra, Fornecedor, ItemCompra, StatusCompra
from apps.fornecedores.servicos import cancelar_compra, receber_compra
from apps.vendas.models import FormaPagamento
from apps.vendas.servicos import abrir_caixa, criar_venda, finalizar_venda

pytestmark = pytest.mark.django_db


@pytest.fixture
def fornecedor(loja):
    return Fornecedor.objects.create(loja=loja, nome="Distribuidora")


def comprar(loja, fornecedor, dono, variacao, quantidade, custo, vencimento=None):
    compra = Compra.objects.create(
        loja=loja, fornecedor=fornecedor, data=timezone.localdate(),
        vencimento=vencimento, usuario=dono, status=StatusCompra.RASCUNHO,
    )
    ItemCompra.objects.create(
        compra=compra, variacao=variacao,
        quantidade=quantidade, custo_unitario=Decimal(custo),
    )
    return receber_compra(compra=compra, usuario=dono)


class TestCompraNoFinanceiro:
    def test_compra_a_vista_vira_despesa_ja_paga(self, loja, dono, fornecedor, variacao):
        """Regressão: compra sem vencimento não gerava lançamento nenhum."""
        compra = comprar(loja, fornecedor, dono, variacao, 10, "55.00")

        lancamento = Lancamento.objects.get(compra=compra)
        assert lancamento.tipo == TipoLancamento.DESPESA
        assert lancamento.status == StatusLancamento.PAGO
        assert lancamento.valor == Decimal("550.00")
        assert lancamento.pago_em == compra.data

    def test_compra_a_prazo_vira_conta_a_pagar(self, loja, dono, fornecedor, variacao):
        vencimento = timezone.localdate() + timedelta(days=30)
        compra = comprar(loja, fornecedor, dono, variacao, 10, "55.00", vencimento)

        lancamento = Lancamento.objects.get(compra=compra)
        assert lancamento.status == StatusLancamento.PENDENTE
        assert lancamento.pago_em is None
        assert lancamento.vencimento == vencimento

    def test_cancelar_compra_anula_a_despesa_ja_baixada(self, loja, dono, fornecedor, variacao):
        """Sem isto, cancelar devolvia o estoque mas deixava a saída no caixa."""
        compra = comprar(loja, fornecedor, dono, variacao, 5, "55.00")
        cancelar_compra(compra=compra, usuario=dono, motivo="Nota errada")

        lancamento = Lancamento.objects.get(compra=compra)
        assert lancamento.status == StatusLancamento.CANCELADO
        assert lancamento.pago_em is None


class TestResultado:
    """
    Cenário do teste: compra 10 a R$ 55 (R$ 550), vende 4 a R$ 120 (R$ 480),
    e paga R$ 100 de aluguel.

        Resultado:  480 − (4 × 55) − 100 = 160
        Caixa:      480 − 550 − 100      = −170
        Estoque:    6 × 55               =  330

    Os dois primeiros números divergem de propósito: o caixa fica negativo
    porque R$ 330 viraram mercadoria na prateleira, o que não é prejuízo.
    """

    @pytest.fixture
    def cenario(self, loja, dono, fornecedor, variacao):
        variacao.preco_venda = Decimal("120.00")
        variacao.saldo = 0
        variacao.save()

        comprar(loja, fornecedor, dono, variacao, 10, "55.00")
        abrir_caixa(loja=loja, usuario=dono, saldo_inicial=Decimal("0.00"))

        venda = criar_venda(
            loja=loja, usuario=dono,
            itens=[{"variacao": variacao, "quantidade": 4}],
        )
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.PIX, "valor": Decimal("480.00")}],
        )

        categoria = CategoriaFinanceira.objects.create(
            loja=loja, nome="Aluguel", tipo=TipoLancamento.DESPESA
        )
        Lancamento.objects.create(
            loja=loja, tipo=TipoLancamento.DESPESA, categoria=categoria,
            descricao="Aluguel", valor=Decimal("100.00"),
            vencimento=timezone.localdate(), pago_em=timezone.localdate(),
            status=StatusLancamento.PAGO,
        )
        return venda

    def test_lucro_bruto_desconta_o_custo_do_que_saiu(self, api_dono, cenario):
        corpo = api_dono.get("/api/relatorios/resultado/").json()["resultado"]

        assert corpo["faturamento_centavos"] == 48000
        assert corpo["custo_mercadoria_centavos"] == 22000, "4 unidades × R$ 55"
        assert corpo["lucro_bruto_centavos"] == 26000

    def test_resultado_desconta_as_despesas_da_loja(self, api_dono, cenario):
        corpo = api_dono.get("/api/relatorios/resultado/").json()["resultado"]

        assert corpo["despesas_operacionais_centavos"] == 10000
        assert corpo["resultado_centavos"] == 16000

    def test_compra_de_mercadoria_nao_entra_como_despesa_operacional(self, api_dono, cenario):
        """
        Regressão do custo em dobro: a compra aparece no caixa, mas o custo
        no resultado é o CMV — R$ 220, não os R$ 550 comprados.
        """
        corpo = api_dono.get("/api/relatorios/resultado/").json()

        assert corpo["resultado"]["despesas_operacionais_centavos"] == 10000
        assert corpo["caixa"]["compras_centavos"] == 55000

    def test_caixa_mostra_a_compra_inteira_no_periodo(self, api_dono, cenario):
        corpo = api_dono.get("/api/relatorios/resultado/").json()["caixa"]

        assert corpo["entradas_centavos"] == 48000
        assert corpo["saidas_centavos"] == 65000, "R$ 550 de compra + R$ 100 de aluguel"
        assert corpo["saldo_centavos"] == -17000

    def test_estoque_explica_a_diferenca_entre_lucro_e_caixa(self, api_dono, cenario):
        corpo = api_dono.get("/api/relatorios/resultado/").json()

        estoque = corpo["estoque"]
        assert estoque["unidades"] == 6
        assert estoque["custo_centavos"] == 33000

        # lucro 160 − caixa (−170) = 330, exatamente o que virou mercadoria
        diferenca = corpo["resultado"]["resultado_centavos"] - corpo["caixa"]["saldo_centavos"]
        assert diferenca == estoque["custo_centavos"]

    def test_margem_bruta(self, api_dono, cenario):
        corpo = api_dono.get("/api/relatorios/resultado/").json()["resultado"]
        assert corpo["margem_bruta"] == pytest.approx(54.17, abs=0.01)


class TestPendencias:
    def test_fiado_aparece_como_a_receber(self, api_dono, loja, dono, variacao, cliente):
        abrir_caixa(loja=loja, usuario=dono, saldo_inicial=Decimal("0.00"))
        venda = criar_venda(
            loja=loja, usuario=dono, cliente=cliente,
            itens=[{"variacao": variacao, "quantidade": 2}],
        )
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.FIADO, "valor": Decimal("100.00")}],
        )

        corpo = api_dono.get("/api/relatorios/resultado/").json()
        assert corpo["a_receber"]["total_centavos"] == 10000
        assert corpo["a_receber"]["quantidade"] == 1
        assert corpo["a_receber"]["atrasado_centavos"] == 0, "vence em 30 dias"

    def test_compra_a_prazo_aparece_como_a_pagar(self, api_dono, loja, dono,
                                                 fornecedor, variacao):
        comprar(loja, fornecedor, dono, variacao, 4, "50.00",
                timezone.localdate() + timedelta(days=15))

        corpo = api_dono.get("/api/relatorios/resultado/").json()
        assert corpo["a_pagar"]["total_centavos"] == 20000
        assert corpo["a_pagar"]["quantidade"] == 1

    def test_conta_vencida_entra_no_atrasado(self, api_dono, loja):
        categoria = CategoriaFinanceira.objects.create(
            loja=loja, nome="Energia", tipo=TipoLancamento.DESPESA
        )
        Lancamento.objects.create(
            loja=loja, tipo=TipoLancamento.DESPESA, categoria=categoria,
            descricao="Energia", valor=Decimal("300.00"),
            vencimento=timezone.localdate() - timedelta(days=5),
            status=StatusLancamento.PENDENTE,
        )

        corpo = api_dono.get("/api/relatorios/resultado/").json()
        assert corpo["a_pagar"]["atrasado_centavos"] == 30000

    def test_vendedor_nao_ve_o_resultado(self, api_vendedor):
        assert api_vendedor.get("/api/relatorios/resultado/").status_code == 403

    def test_periodo_vazio_nao_quebra(self, api_dono):
        corpo = api_dono.get(
            "/api/relatorios/resultado/?inicio=2020-01-01&fim=2020-01-31"
        ).json()
        assert corpo["resultado"]["faturamento_centavos"] == 0
        assert corpo["resultado"]["margem_bruta"] == 0
        assert corpo["caixa"]["saldo_centavos"] == 0
