"""Regras do PDV: venda, pagamento, caixa e cancelamento."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.core.exceptions import CaixaFechado, ErroDeNegocio
from apps.financeiro.models import Lancamento, StatusLancamento, TipoLancamento
from apps.vendas.models import (
    FormaPagamento,
    MovimentoCaixa,
    StatusCaixa,
    StatusVenda,
    TipoMovimentoCaixa,
)
from apps.vendas.servicos import (
    abrir_caixa,
    calcular_saldo_do_caixa,
    cancelar_venda,
    criar_venda,
    fechar_caixa,
    finalizar_venda,
    movimentar_caixa,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def caixa(loja, dono):
    return abrir_caixa(loja=loja, usuario=dono, saldo_inicial=Decimal("100.00"))


def vender(loja, usuario, variacao, quantidade=2, cliente=None, desconto=Decimal("0.00")):
    return criar_venda(
        loja=loja, usuario=usuario, cliente=cliente, desconto=desconto,
        itens=[{"variacao": variacao, "quantidade": quantidade}],
    )


class TestCaixa:
    def test_abre_com_saldo_inicial_como_suprimento(self, loja, dono):
        caixa = abrir_caixa(loja=loja, usuario=dono, saldo_inicial=Decimal("150.00"))
        assert caixa.status == StatusCaixa.ABERTO
        assert calcular_saldo_do_caixa(caixa) == Decimal("150.00")

    def test_nao_permite_dois_caixas_abertos(self, loja, dono, caixa):
        with pytest.raises(ErroDeNegocio):
            abrir_caixa(loja=loja, usuario=dono, saldo_inicial=Decimal("0.00"))

    def test_sangria_reduz_o_saldo(self, caixa, dono):
        movimentar_caixa(
            caixa=caixa, usuario=dono, tipo=TipoMovimentoCaixa.SANGRIA,
            valor=Decimal("40.00"), descricao="Retirada para o banco",
        )
        assert calcular_saldo_do_caixa(caixa) == Decimal("60.00")

    def test_sangria_maior_que_o_saldo_e_recusada(self, caixa, dono):
        with pytest.raises(ErroDeNegocio):
            movimentar_caixa(
                caixa=caixa, usuario=dono, tipo=TipoMovimentoCaixa.SANGRIA,
                valor=Decimal("500.00"),
            )

    def test_fechamento_calcula_a_diferenca(self, caixa, dono):
        fechado = fechar_caixa(
            caixa=caixa, usuario=dono, saldo_informado=Decimal("95.00")
        )
        assert fechado.saldo_calculado == Decimal("100.00")
        assert fechado.diferenca == Decimal("-5.00"), "faltaram 5 reais na gaveta"
        assert fechado.status == StatusCaixa.FECHADO

    def test_nao_fecha_com_venda_aberta(self, loja, dono, variacao, caixa):
        vender(loja, dono, variacao)
        with pytest.raises(ErroDeNegocio):
            fechar_caixa(caixa=caixa, usuario=dono, saldo_informado=Decimal("100.00"))


class TestVenda:
    def test_venda_aberta_nao_baixa_estoque(self, loja, dono, variacao, caixa):
        vender(loja, dono, variacao, quantidade=3)
        variacao.refresh_from_db()
        assert variacao.saldo == 10, "estoque só cai ao finalizar"

    def test_calcula_totais_e_custo(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=3)
        assert venda.subtotal == Decimal("150.00")  # 3 × 50,00
        assert venda.total == Decimal("150.00")
        assert venda.custo_total == Decimal("90.00")  # 3 × 30,00
        assert venda.lucro == Decimal("60.00")

    def test_desconto_abate_do_total(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=2, desconto=Decimal("10.00"))
        assert venda.subtotal == Decimal("100.00")
        assert venda.total == Decimal("90.00")

    def test_desconto_maior_que_subtotal_e_recusado(self, loja, dono, variacao, caixa):
        with pytest.raises(ErroDeNegocio):
            vender(loja, dono, variacao, quantidade=1, desconto=Decimal("999.00"))

    def test_numero_da_venda_e_sequencial_por_loja(self, loja, dono, variacao, caixa):
        primeira = vender(loja, dono, variacao, quantidade=1)
        segunda = vender(loja, dono, variacao, quantidade=1)
        assert (primeira.numero, segunda.numero) == (1, 2)

    def test_venda_sem_itens_e_recusada(self, loja, dono, caixa):
        with pytest.raises(ErroDeNegocio):
            criar_venda(loja=loja, usuario=dono, itens=[])

    def test_item_de_outra_loja_e_recusado(self, loja, dono, outra_loja, caixa):
        from tests.conftest_helpers import criar_variacao_zerada

        alheia = criar_variacao_zerada(outra_loja)
        with pytest.raises(ErroDeNegocio):
            criar_venda(
                loja=loja, usuario=dono,
                itens=[{"variacao": alheia, "quantidade": 1}],
            )

    def test_preco_do_item_e_snapshot(self, loja, dono, variacao, caixa):
        """Mudar o preço depois não pode reescrever a venda passada."""
        venda = vender(loja, dono, variacao, quantidade=1)
        variacao.preco_venda = Decimal("99.00")
        variacao.save()

        item = venda.itens.first()
        assert item.preco_unitario == Decimal("50.00")


class TestFinalizacao:
    def test_finaliza_baixa_estoque_e_move_o_caixa(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=2)
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.DINHEIRO, "valor": Decimal("100.00")}],
        )

        variacao.refresh_from_db()
        venda.refresh_from_db()
        assert variacao.saldo == 8
        assert venda.status == StatusVenda.FINALIZADA
        assert calcular_saldo_do_caixa(caixa) == Decimal("200.00")  # 100 inicial + 100

    def test_pagamento_insuficiente_e_recusado(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=2)
        with pytest.raises(ErroDeNegocio):
            finalizar_venda(
                venda=venda, usuario=dono,
                pagamentos=[{"forma": FormaPagamento.DINHEIRO, "valor": Decimal("50.00")}],
            )
        variacao.refresh_from_db()
        assert variacao.saldo == 10, "estoque intacto quando a finalização falha"

    def test_troco_em_dinheiro(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=2)  # 100,00
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.DINHEIRO, "valor": Decimal("150.00")}],
        )
        pagamento = venda.pagamentos.first()
        assert pagamento.troco == Decimal("50.00")
        # Na gaveta entram só os 100 líquidos.
        assert calcular_saldo_do_caixa(caixa) == Decimal("200.00")

    def test_excesso_no_cartao_nao_vira_troco(self, loja, dono, variacao, caixa):
        """Pagar 150 no cartão numa venda de 100 é erro de digitação."""
        venda = vender(loja, dono, variacao, quantidade=2)
        with pytest.raises(ErroDeNegocio):
            finalizar_venda(
                venda=venda, usuario=dono,
                pagamentos=[{"forma": FormaPagamento.DEBITO, "valor": Decimal("150.00")}],
            )

    def test_pagamento_dividido(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=2)  # 100,00
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[
                {"forma": FormaPagamento.DINHEIRO, "valor": Decimal("30.00")},
                {"forma": FormaPagamento.PIX, "valor": Decimal("70.00")},
            ],
        )
        assert venda.pagamentos.count() == 2
        # Pix não entra na gaveta.
        assert calcular_saldo_do_caixa(caixa) == Decimal("130.00")

    def test_sem_caixa_aberto_nao_finaliza(self, loja, dono, variacao):
        venda = vender(loja, dono, variacao, quantidade=1)
        with pytest.raises(CaixaFechado):
            finalizar_venda(
                venda=venda, usuario=dono,
                pagamentos=[{"forma": FormaPagamento.DINHEIRO, "valor": Decimal("50.00")}],
            )

    def test_estoque_insuficiente_bloqueia_a_venda(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=50)
        with pytest.raises(ErroDeNegocio):
            finalizar_venda(
                venda=venda, usuario=dono,
                pagamentos=[{"forma": FormaPagamento.DINHEIRO, "valor": Decimal("2500.00")}],
            )

    def test_gera_receita_no_financeiro(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=2)
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.PIX, "valor": Decimal("100.00")}],
        )
        lancamento = Lancamento.objects.get(venda=venda)
        assert lancamento.tipo == TipoLancamento.RECEITA
        assert lancamento.status == StatusLancamento.PAGO
        assert lancamento.valor == Decimal("100.00")


class TestFiado:
    def test_fiado_gera_conta_a_receber_pendente(self, loja, dono, variacao, cliente, caixa):
        venda = vender(loja, dono, variacao, quantidade=2, cliente=cliente)
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.FIADO, "valor": Decimal("100.00")}],
        )
        lancamento = Lancamento.objects.get(venda=venda)
        assert lancamento.status == StatusLancamento.PENDENTE
        assert lancamento.cliente == cliente
        # E não entra dinheiro na gaveta.
        assert calcular_saldo_do_caixa(caixa) == Decimal("100.00")

    def test_fiado_sem_cliente_e_recusado(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=2)
        with pytest.raises(ErroDeNegocio):
            finalizar_venda(
                venda=venda, usuario=dono,
                pagamentos=[{"forma": FormaPagamento.FIADO, "valor": Decimal("100.00")}],
            )

    def test_fiado_acima_do_limite_e_recusado(self, loja, dono, variacao, cliente, caixa):
        cliente.limite_credito = Decimal("50.00")
        cliente.save()
        venda = vender(loja, dono, variacao, quantidade=2, cliente=cliente)
        with pytest.raises(ErroDeNegocio):
            finalizar_venda(
                venda=venda, usuario=dono,
                pagamentos=[{"forma": FormaPagamento.FIADO, "valor": Decimal("100.00")}],
            )

    def test_limite_considera_o_que_ja_esta_em_aberto(self, loja, dono, variacao, cliente, caixa):
        primeira = vender(loja, dono, variacao, quantidade=2, cliente=cliente)  # 100
        finalizar_venda(
            venda=primeira, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.FIADO, "valor": Decimal("100.00")}],
        )
        # Limite 200, já deve 100 — a segunda de 150 estoura.
        segunda = vender(loja, dono, variacao, quantidade=3, cliente=cliente)
        with pytest.raises(ErroDeNegocio):
            finalizar_venda(
                venda=segunda, usuario=dono,
                pagamentos=[{"forma": FormaPagamento.FIADO, "valor": Decimal("150.00")}],
            )


class TestIdadeMinima:
    def test_menor_de_idade_nao_compra(self, loja, dono, variacao, cliente, caixa):
        cliente.data_nascimento = date.today() - timedelta(days=365 * 16)
        cliente.save()
        with pytest.raises(ErroDeNegocio):
            vender(loja, dono, variacao, quantidade=1, cliente=cliente)

    def test_cliente_sem_data_de_nascimento_nao_bloqueia(self, loja, dono, variacao,
                                                         cliente, caixa):
        cliente.data_nascimento = None
        cliente.save()
        venda = vender(loja, dono, variacao, quantidade=1, cliente=cliente)
        assert venda.status == StatusVenda.ABERTA


class TestCancelamento:
    def test_cancelamento_devolve_estoque_e_dinheiro(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=2)
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.DINHEIRO, "valor": Decimal("100.00")}],
        )
        cancelar_venda(venda=venda, usuario=dono, motivo="Cliente desistiu")

        variacao.refresh_from_db()
        venda.refresh_from_db()
        assert variacao.saldo == 10, "estoque voltou ao original"
        assert venda.status == StatusVenda.CANCELADA
        assert calcular_saldo_do_caixa(caixa) == Decimal("100.00"), "dinheiro saiu da gaveta"

    def test_cancelamento_cancela_o_lancamento_financeiro(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=2)
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.PIX, "valor": Decimal("100.00")}],
        )
        cancelar_venda(venda=venda, usuario=dono)
        assert Lancamento.objects.get(venda=venda).status == StatusLancamento.CANCELADO

    def test_cancelar_venda_aberta_nao_mexe_no_estoque(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=2)
        cancelar_venda(venda=venda, usuario=dono)
        variacao.refresh_from_db()
        assert variacao.saldo == 10
        assert not MovimentoCaixa.objects.filter(venda=venda).exists()

    def test_nao_cancela_duas_vezes(self, loja, dono, variacao, caixa):
        venda = vender(loja, dono, variacao, quantidade=1)
        cancelar_venda(venda=venda, usuario=dono)
        with pytest.raises(ErroDeNegocio):
            cancelar_venda(venda=venda, usuario=dono)


class TestPrazoDoFiado:
    """O fiado não pode nascer vencido — seria alarme falso de atraso."""

    def test_fiado_vence_conforme_prazo_da_loja(self, loja, dono, variacao, cliente, caixa):
        from datetime import timedelta

        from django.utils import timezone

        venda = vender(loja, dono, variacao, quantidade=2, cliente=cliente)
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.FIADO, "valor": Decimal("100.00")}],
        )
        lancamento = Lancamento.objects.get(venda=venda)
        assert lancamento.vencimento == timezone.localdate() + timedelta(days=30)
        assert not lancamento.atrasado

    def test_prazo_zero_faz_vencer_no_mesmo_dia(self, loja, dono, variacao, cliente, caixa):
        from django.utils import timezone

        configuracao = loja.configuracao
        configuracao.prazo_fiado_dias = 0
        configuracao.save()

        venda = vender(loja, dono, variacao, quantidade=1, cliente=cliente)
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.FIADO, "valor": Decimal("50.00")}],
        )
        assert Lancamento.objects.get(venda=venda).vencimento == timezone.localdate()

    def test_venda_a_vista_continua_vencendo_no_dia(self, loja, dono, variacao, caixa):
        from django.utils import timezone

        venda = vender(loja, dono, variacao, quantidade=1)
        finalizar_venda(
            venda=venda, usuario=dono,
            pagamentos=[{"forma": FormaPagamento.PIX, "valor": Decimal("50.00")}],
        )
        lancamento = Lancamento.objects.get(venda=venda)
        assert lancamento.vencimento == timezone.localdate()
        assert lancamento.pago_em == timezone.localdate()
