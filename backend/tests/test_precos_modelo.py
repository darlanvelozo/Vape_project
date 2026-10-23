"""Preço do modelo aplicado a todos os sabores (POST /api/produtos/{id}/precos)."""

from decimal import Decimal

import pytest

from apps.core.exceptions import ErroDeNegocio
from apps.produtos.models import Produto, Variacao
from apps.produtos.servicos import aplicar_precos_ao_modelo
from apps.vendas.models import ItemVenda

pytestmark = pytest.mark.django_db


@pytest.fixture
def modelo(loja):
    """Ignite V55 com três sabores, um deles inativo e um com saldo."""
    produto = Produto.objects.create(loja=loja, nome="Ignite V55")
    for sabor, saldo, ativo in (("Menthol", 2, True), ("Icy mint", 0, True),
                                ("Grape ice", 0, False)):
        Variacao.objects.create(
            loja=loja, produto=produto, sabor=sabor, saldo=saldo, ativo=ativo,
            preco_custo=Decimal("61.75"), preco_venda=Decimal("95.00"),
        )
    return produto


def precos(produto):
    return sorted(produto.variacoes.values_list("sabor", "preco_custo", "preco_venda"))


class TestServico:
    def test_iguala_custo_e_venda_em_todos_os_sabores_inclusive_inativos(self, modelo):
        alteradas = aplicar_precos_ao_modelo(
            produto=modelo, preco_custo=Decimal("60.00"), preco_venda=Decimal("100.00")
        )
        assert alteradas == 3
        assert {(c, v) for _, c, v in precos(modelo)} == {(Decimal("60.00"), Decimal("100.00"))}

    def test_so_o_custo_mantem_a_venda(self, modelo):
        aplicar_precos_ao_modelo(produto=modelo, preco_custo=Decimal("58.00"))
        assert {(c, v) for _, c, v in precos(modelo)} == {(Decimal("58.00"), Decimal("95.00"))}

    def test_nao_mexe_no_saldo(self, modelo):
        aplicar_precos_ao_modelo(produto=modelo, preco_venda=Decimal("99.00"))
        assert modelo.variacoes.get(sabor="Menthol").saldo == 2

    def test_conta_so_o_que_mudou(self, modelo):
        modelo.variacoes.filter(sabor="Menthol").update(preco_venda=Decimal("110.00"))
        assert aplicar_precos_ao_modelo(produto=modelo, preco_venda=Decimal("110.00")) == 2

    def test_nao_toca_outro_modelo(self, modelo, loja):
        outro = Produto.objects.create(loja=loja, nome="Ignite V155")
        Variacao.objects.create(loja=loja, produto=outro, sabor="Menthol",
                                preco_custo=Decimal("74.75"), preco_venda=Decimal("115.00"))
        aplicar_precos_ao_modelo(produto=modelo, preco_venda=Decimal("100.00"))
        assert outro.variacoes.get().preco_venda == Decimal("115.00")

    def test_sem_nenhum_preco_e_recusado(self, modelo):
        with pytest.raises(ErroDeNegocio):
            aplicar_precos_ao_modelo(produto=modelo)

    def test_registra_no_historico_de_auditoria(self, modelo):
        variacao = modelo.variacoes.get(sabor="Menthol")
        antes = variacao.history.count()
        aplicar_precos_ao_modelo(produto=modelo, preco_venda=Decimal("100.00"))
        assert variacao.history.count() == antes + 1


class TestApi:
    def test_dono_altera_o_preco_do_modelo(self, api_dono, modelo):
        resposta = api_dono.post(f"/api/produtos/{modelo.id}/precos/",
                                 {"preco_venda_centavos": 10000, "preco_custo_centavos": 6500},
                                 format="json")
        assert resposta.status_code == 200, resposta.content
        corpo = resposta.json()
        assert corpo["variacoes_alteradas"] == 3
        assert {v["preco_venda_centavos"] for v in corpo["variacoes"]} == {10000}
        assert {v["preco_custo_centavos"] for v in corpo["variacoes"]} == {6500}

    def test_corpo_vazio_e_recusado(self, api_dono, modelo):
        resposta = api_dono.post(f"/api/produtos/{modelo.id}/precos/", {}, format="json")
        assert resposta.status_code == 400

    def test_preco_negativo_e_recusado(self, api_dono, modelo):
        resposta = api_dono.post(f"/api/produtos/{modelo.id}/precos/",
                                 {"preco_venda_centavos": -1}, format="json")
        assert resposta.status_code == 400

    def test_vendedor_nao_altera_preco(self, api_vendedor, modelo):
        resposta = api_vendedor.post(f"/api/produtos/{modelo.id}/precos/",
                                     {"preco_venda_centavos": 1}, format="json")
        assert resposta.status_code == 403
        assert {v for _, _, v in precos(modelo)} == {Decimal("95.00")}

    def test_venda_ja_feita_mantem_o_custo_congelado(self, api_dono, modelo):
        variacao = modelo.variacoes.get(sabor="Menthol")
        api_dono.post("/api/caixas/abrir/", {"saldo_inicial_centavos": 0}, format="json")
        venda = api_dono.post("/api/vendas/rapida/", {
            "itens": [{"variacao": variacao.id, "quantidade": 1}],
            "pagamentos": [{"forma": "dinheiro", "valor_centavos": 9500}],
        }, format="json")
        assert venda.status_code == 201, venda.content

        api_dono.post(f"/api/produtos/{modelo.id}/precos/",
                      {"preco_custo_centavos": 7000}, format="json")
        assert ItemVenda.objects.get(variacao=variacao).custo_unitario == Decimal("61.75")
