"""Regras de estoque: saldo, concorrência e inventário."""

from decimal import Decimal

import pytest

from apps.core.exceptions import ErroDeNegocio, EstoqueInsuficiente
from apps.estoque.models import MovimentoEstoque, TipoMovimento
from apps.estoque.servicos import (
    ajustar_para_contagem,
    atualizar_custo_medio,
    registrar_movimento,
)

pytestmark = pytest.mark.django_db


class TestRegistrarMovimento:
    def test_entrada_soma_saldo(self, variacao, dono):
        registrar_movimento(
            variacao=variacao, tipo=TipoMovimento.ENTRADA, quantidade=5, usuario=dono
        )
        variacao.refresh_from_db()
        assert variacao.saldo == 15

    def test_saida_subtrai_saldo(self, variacao, dono):
        registrar_movimento(
            variacao=variacao, tipo=TipoMovimento.SAIDA, quantidade=3, usuario=dono
        )
        variacao.refresh_from_db()
        assert variacao.saldo == 7

    def test_saida_maior_que_saldo_e_recusada(self, variacao, dono):
        with pytest.raises(EstoqueInsuficiente):
            registrar_movimento(
                variacao=variacao, tipo=TipoMovimento.SAIDA, quantidade=11, usuario=dono
            )
        variacao.refresh_from_db()
        assert variacao.saldo == 10, "saldo não pode ter mudado após recusa"

    def test_saida_negativa_permitida_quando_a_loja_autoriza(self, variacao, dono):
        registrar_movimento(
            variacao=variacao, tipo=TipoMovimento.SAIDA, quantidade=15,
            usuario=dono, permitir_negativo=True,
        )
        variacao.refresh_from_db()
        assert variacao.saldo == -5

    def test_quantidade_zero_e_recusada(self, variacao, dono):
        with pytest.raises(ErroDeNegocio):
            registrar_movimento(
                variacao=variacao, tipo=TipoMovimento.ENTRADA, quantidade=0, usuario=dono
            )

    def test_saldo_apos_registra_o_resultado_de_cada_movimento(self, variacao, dono):
        """O extrato precisa ser auditável sem recalcular a série inteira."""
        registrar_movimento(variacao=variacao, tipo=TipoMovimento.ENTRADA, quantidade=5,
                            usuario=dono)
        registrar_movimento(variacao=variacao, tipo=TipoMovimento.SAIDA, quantidade=2,
                            usuario=dono)

        saldos = list(
            MovimentoEstoque.objects.filter(variacao=variacao)
            .order_by("id").values_list("saldo_apos", flat=True)
        )
        assert saldos == [15, 13]

    def test_sequencia_de_movimentos_bate_com_o_saldo_final(self, variacao, dono):
        for tipo, quantidade in [
            (TipoMovimento.ENTRADA, 20),
            (TipoMovimento.SAIDA, 7),
            (TipoMovimento.PERDA, 3),
            (TipoMovimento.DEVOLUCAO, 2),
        ]:
            registrar_movimento(variacao=variacao, tipo=tipo, quantidade=quantidade,
                                usuario=dono)

        variacao.refresh_from_db()
        # 10 + 20 - 7 - 3 + 2
        assert variacao.saldo == 22
        ultimo = MovimentoEstoque.objects.filter(variacao=variacao).order_by("-id").first()
        assert ultimo.saldo_apos == variacao.saldo


class TestInventario:
    def test_contagem_maior_gera_ajuste_de_entrada(self, variacao, dono):
        movimento = ajustar_para_contagem(variacao=variacao, contagem=13, usuario=dono)
        variacao.refresh_from_db()
        assert variacao.saldo == 13
        assert movimento.quantidade == 3
        assert movimento.saldo_apos == 13

    def test_contagem_menor_reduz_o_saldo(self, variacao, dono):
        ajustar_para_contagem(variacao=variacao, contagem=4, usuario=dono)
        variacao.refresh_from_db()
        assert variacao.saldo == 4

    def test_contagem_igual_nao_gera_movimento(self, variacao, dono):
        assert ajustar_para_contagem(variacao=variacao, contagem=10, usuario=dono) is None
        assert MovimentoEstoque.objects.filter(variacao=variacao).count() == 0

    def test_contagem_negativa_e_recusada(self, variacao, dono):
        with pytest.raises(ErroDeNegocio):
            ajustar_para_contagem(variacao=variacao, contagem=-1, usuario=dono)


class TestCustoMedio:
    def test_pondera_pelo_saldo_anterior(self, variacao, dono):
        """10 unidades a 30,00 + 10 a 40,00 = custo médio 35,00."""
        registrar_movimento(
            variacao=variacao, tipo=TipoMovimento.ENTRADA, quantidade=10,
            usuario=dono, custo_unitario=Decimal("40.00"),
        )
        variacao.refresh_from_db()
        novo = atualizar_custo_medio(
            variacao=variacao, quantidade_entrada=10, custo_unitario=Decimal("40.00")
        )
        assert novo == Decimal("35.00")

    def test_saldo_anterior_zero_adota_o_custo_da_entrada(self, loja, dono):
        from tests.conftest_helpers import criar_variacao_zerada

        variacao = criar_variacao_zerada(loja)
        registrar_movimento(
            variacao=variacao, tipo=TipoMovimento.ENTRADA, quantidade=5,
            usuario=dono, custo_unitario=Decimal("25.00"),
        )
        variacao.refresh_from_db()
        novo = atualizar_custo_medio(
            variacao=variacao, quantidade_entrada=5, custo_unitario=Decimal("25.00")
        )
        assert novo == Decimal("25.00")
