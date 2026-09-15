"""
Importação da operação inicial de uma loja.

O risco central aqui é silencioso: importar o histórico com o custo errado
produz margem errada para sempre, porque o item de venda guarda o custo em
snapshot. Por isso o foco dos testes é a consistência de custo e saldo.
"""

import json
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.estoque.models import MovimentoEstoque
from apps.financeiro.models import Lancamento, StatusLancamento
from apps.lojas.models import Loja
from apps.produtos.models import Variacao
from apps.vendas.models import Caixa, StatusCaixa, StatusVenda, Venda

pytestmark = pytest.mark.django_db


def escrever(tmp_path, dados):
    caminho = tmp_path / "operacao.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return str(caminho)


@pytest.fixture
def operacao():
    """
    Duas compras do mesmo item a custos diferentes, com as vendas do primeiro
    lote entre elas — o formato que expõe erro de custo médio.
    """
    return {
        "loja": {"nome": "Loja Importada"},
        "usuario": {
            "nome": "Dono", "email": "dono@importada.com", "senha": "SenhaForte123",
        },
        "fornecedores": ["Distribuidora"],
        "produtos": [{
            "nome": "Pod X",
            "marca": "Marca X",
            "categoria": "Descartáveis",
            "variacoes": [
                {"sabor": "Menta", "preco_venda": "120.00", "preco_custo": "60.00"},
                {"sabor": "Uva", "preco_venda": "120.00", "preco_custo": "60.00"},
            ],
        }],
        "compras": [
            {"data": "2026-09-07", "fornecedor": "Distribuidora", "itens": [
                {"produto": "Pod X", "sabor": "Menta",
                 "quantidade": 2, "custo_unitario": "55.00"},
                {"produto": "Pod X", "sabor": "Uva",
                 "quantidade": 1, "custo_unitario": "55.00"},
            ]},
            {"data": "2026-09-13", "fornecedor": "Distribuidora", "itens": [
                {"produto": "Pod X", "sabor": "Menta",
                 "quantidade": 2, "custo_unitario": "70.00"},
            ]},
        ],
        "vendas": [
            {"data": "2026-09-08", "forma_pagamento": "pix", "itens": [
                {"produto": "Pod X", "sabor": "Menta",
                 "quantidade": 1, "preco_unitario": "120.00"},
            ]},
            {"data": "2026-09-09", "forma_pagamento": "dinheiro", "itens": [
                {"produto": "Pod X", "sabor": "Menta",
                 "quantidade": 1, "preco_unitario": "110.00"},
            ]},
        ],
    }


class TestImportacao:
    def test_cria_loja_usuario_e_catalogo(self, tmp_path, operacao):
        call_command("importar_operacao", escrever(tmp_path, operacao))

        loja = Loja.objects.get(nome="Loja Importada")
        assert loja.usuarios.get().email == "dono@importada.com"
        assert loja.usuarios.get().papel == "dono"
        assert Variacao.objects.filter(loja=loja).count() == 2

    def test_saldo_reflete_compras_menos_vendas(self, tmp_path, operacao):
        call_command("importar_operacao", escrever(tmp_path, operacao))

        menta = Variacao.objects.get(sabor="Menta")
        uva = Variacao.objects.get(sabor="Uva")
        assert menta.saldo == 2, "2 compradas + 2 recompradas − 2 vendidas"
        assert uva.saldo == 1

    def test_venda_usa_o_custo_vigente_na_data_e_nao_o_do_cadastro(self, tmp_path, operacao):
        """
        Regressão: o catálogo nasce com custo 60, a compra baixa para 55 e a
        recompra sobe para 70. As duas vendas aconteceram quando o custo era
        55 — é esse valor que tem de estar no snapshot.
        """
        call_command("importar_operacao", escrever(tmp_path, operacao))

        for venda in Venda.objects.filter(status=StatusVenda.FINALIZADA):
            for item in venda.itens.all():
                assert item.custo_unitario == Decimal("55.00")

    def test_lucro_realizado_bate_com_a_conta_manual(self, tmp_path, operacao):
        call_command("importar_operacao", escrever(tmp_path, operacao))

        vendas = Venda.objects.filter(status=StatusVenda.FINALIZADA)
        faturamento = sum(venda.total for venda in vendas)
        lucro = sum(venda.lucro for venda in vendas)

        assert faturamento == Decimal("230.00")  # 120 + 110
        assert lucro == Decimal("120.00")  # 230 − (2 × 55)

    def test_custo_medio_atual_reflete_a_ultima_compra(self, tmp_path, operacao):
        """Estoque zerado antes da recompra: o custo novo substitui o antigo."""
        call_command("importar_operacao", escrever(tmp_path, operacao))
        assert Variacao.objects.get(sabor="Menta").preco_custo == Decimal("70.00")

    def test_extrato_de_estoque_fecha_com_o_saldo(self, tmp_path, operacao):
        call_command("importar_operacao", escrever(tmp_path, operacao))

        for variacao in Variacao.objects.all():
            ultimo = (
                MovimentoEstoque.objects.filter(variacao=variacao)
                .order_by("-criado_em", "-id").first()
            )
            assert ultimo.saldo_apos == variacao.saldo

    def test_historico_fica_nas_datas_informadas(self, tmp_path, operacao):
        call_command("importar_operacao", escrever(tmp_path, operacao))

        datas = sorted(
            venda.finalizada_em.date().isoformat()
            for venda in Venda.objects.filter(status=StatusVenda.FINALIZADA)
        )
        assert datas == ["2026-09-08", "2026-09-09"]

    def test_um_caixa_fechado_por_dia_de_venda(self, tmp_path, operacao):
        call_command("importar_operacao", escrever(tmp_path, operacao))

        caixas = Caixa.objects.all()
        assert caixas.count() == 2
        assert all(caixa.status == StatusCaixa.FECHADO for caixa in caixas)
        assert all(caixa.diferenca == Decimal("0.00") for caixa in caixas)

    def test_so_o_dinheiro_entra_no_caixa(self, tmp_path, operacao):
        """A venda em Pix não passa pela gaveta; a em dinheiro, sim."""
        call_command("importar_operacao", escrever(tmp_path, operacao))

        saldos = sorted(caixa.saldo_calculado for caixa in Caixa.objects.all())
        assert saldos == [Decimal("0.00"), Decimal("110.00")]

    def test_vendas_geram_receita_no_financeiro(self, tmp_path, operacao):
        call_command("importar_operacao", escrever(tmp_path, operacao))

        receitas = Lancamento.objects.filter(tipo="receita", status=StatusLancamento.PAGO)
        assert receitas.count() == 2
        assert sum(lancamento.valor for lancamento in receitas) == Decimal("230.00")


class TestConferencia:
    def test_recusa_quando_os_totais_nao_batem(self, tmp_path, operacao):
        operacao["conferencia"] = {"total_vendas": "999.00"}
        with pytest.raises(CommandError, match="Conferência falhou"):
            call_command("importar_operacao", escrever(tmp_path, operacao))

    def test_aceita_quando_os_totais_batem(self, tmp_path, operacao):
        operacao["conferencia"] = {
            "total_compras": "305.00",  # 3 × 55 + 2 × 70
            "total_vendas": "230.00",
            "unidades_em_estoque": "3",
        }
        call_command("importar_operacao", escrever(tmp_path, operacao))
        assert Loja.objects.filter(nome="Loja Importada").exists()

    def test_recusa_item_fora_do_catalogo(self, tmp_path, operacao):
        operacao["vendas"][0]["itens"][0]["sabor"] = "Sabor Inexistente"
        with pytest.raises(CommandError, match="não está na seção produtos"):
            call_command("importar_operacao", escrever(tmp_path, operacao))

    def test_recusa_loja_duplicada_sem_recriar(self, tmp_path, operacao):
        arquivo = escrever(tmp_path, operacao)
        call_command("importar_operacao", arquivo)
        with pytest.raises(CommandError, match="já existe"):
            call_command("importar_operacao", arquivo)

    def test_conferir_nao_grava_nada(self, tmp_path, operacao):
        call_command("importar_operacao", escrever(tmp_path, operacao), "--conferir")
        assert not Loja.objects.filter(nome="Loja Importada").exists()

    def test_venda_sem_estoque_suficiente_e_recusada(self, tmp_path, operacao):
        """Erro de digitação na quantidade não pode virar saldo negativo."""
        operacao["vendas"][0]["itens"][0]["quantidade"] = 99
        with pytest.raises(CommandError, match="recusada"):
            call_command("importar_operacao", escrever(tmp_path, operacao))
