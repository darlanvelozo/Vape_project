"""
Vitrine pública.

É o único endpoint que responde sem autenticação com dados de uma loja, então
o foco aqui é o que **não** pode sair: custo, margem, saldo exato, itens sem
estoque, e qualquer coisa de outra loja.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.produtos.models import Produto, Variacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def publico():
    """Cliente sem token — como o cliente da loja acessa."""
    return APIClient()


@pytest.fixture
def vitrine_ligada(loja):
    configuracao = loja.configuracao
    configuracao.vitrine_publica = True
    configuracao.vitrine_whatsapp = "11999998888"
    configuracao.save()
    return configuracao


@pytest.fixture
def catalogo(loja):
    """Um item com estoque, um esgotado e um inativo."""
    produto = Produto.objects.create(loja=loja, nome="Elf Bar BC10000")
    com_estoque = Variacao.objects.create(
        loja=loja, produto=produto, sabor="Blue Razz",
        preco_custo=Decimal("38.00"), preco_venda=Decimal("75.00"), saldo=7,
    )
    esgotado = Variacao.objects.create(
        loja=loja, produto=produto, sabor="Watermelon",
        preco_custo=Decimal("38.00"), preco_venda=Decimal("75.00"), saldo=0,
    )
    inativo = Variacao.objects.create(
        loja=loja, produto=produto, sabor="Descontinuado",
        preco_custo=Decimal("38.00"), preco_venda=Decimal("75.00"), saldo=5, ativo=False,
    )
    return {"com_estoque": com_estoque, "esgotado": esgotado, "inativo": inativo}


class TestAcesso:
    def test_abre_sem_token(self, publico, loja, vitrine_ligada, catalogo):
        assert publico.get(f"/api/vitrine/{loja.slug}/").status_code == 200

    def test_vitrine_desligada_da_404(self, publico, loja, catalogo):
        assert publico.get(f"/api/vitrine/{loja.slug}/").status_code == 404

    def test_loja_inativa_da_404(self, publico, loja, vitrine_ligada):
        loja.ativa = False
        loja.save()
        assert publico.get(f"/api/vitrine/{loja.slug}/").status_code == 404

    def test_slug_inexistente_da_404(self, publico):
        assert publico.get("/api/vitrine/nao-existe/").status_code == 404

    def test_loja_existente_com_vitrine_off_responde_igual_a_inexistente(
        self, publico, loja, catalogo
    ):
        """A URL não pode servir para descobrir quais lojas existem."""
        existente = publico.get(f"/api/vitrine/{loja.slug}/")
        inventada = publico.get("/api/vitrine/loja-que-nao-existe/")
        assert existente.status_code == inventada.status_code == 404
        assert existente.json() == inventada.json()


class TestExposicaoDeDados:
    def test_nao_vaza_custo_nem_margem(self, publico, loja, vitrine_ligada, catalogo):
        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        texto = str(corpo)
        assert "custo" not in texto.lower()
        assert "margem" not in texto.lower()
        assert "3800" not in texto, "o preço de custo não pode aparecer nem em centavos"

    def test_nao_vaza_saldo_exato(self, publico, loja, vitrine_ligada, catalogo):
        """Saldo exato entrega o giro da loja ao concorrente."""
        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        opcao = corpo["produtos"][0]["opcoes"][0]
        assert "saldo" not in opcao
        assert opcao["disponibilidade"] == "disponivel"

    def test_mostra_o_preco_de_venda(self, publico, loja, vitrine_ligada, catalogo):
        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        assert corpo["produtos"][0]["opcoes"][0]["preco_centavos"] == 7500

    def test_esconde_o_preco_quando_a_loja_pede(self, publico, loja, vitrine_ligada, catalogo):
        vitrine_ligada.vitrine_mostrar_preco = False
        vitrine_ligada.save()

        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        assert "preco_centavos" not in corpo["produtos"][0]["opcoes"][0]
        assert corpo["mostrar_preco"] is False

    def test_traz_o_aviso_de_idade(self, publico, loja, vitrine_ligada, catalogo):
        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        assert "18" in corpo["aviso_idade"]


class TestSomenteDisponivel:
    def test_lista_so_o_que_tem_estoque(self, publico, loja, vitrine_ligada, catalogo):
        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        sabores = [
            opcao["sabor"]
            for produto in corpo["produtos"]
            for opcao in produto["opcoes"]
        ]
        assert sabores == ["Blue Razz"]
        assert corpo["total_itens"] == 1

    def test_item_esgotado_some_da_vitrine(self, publico, loja, vitrine_ligada, catalogo):
        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        assert "Watermelon" not in str(corpo)

    def test_item_inativo_some_mesmo_com_saldo(self, publico, loja, vitrine_ligada, catalogo):
        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        assert "Descontinuado" not in str(corpo)

    def test_produto_inativo_some_com_todas_as_variacoes(
        self, publico, loja, vitrine_ligada, catalogo
    ):
        produto = catalogo["com_estoque"].produto
        produto.ativo = False
        produto.save()

        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        assert corpo["produtos"] == []
        assert corpo["total_itens"] == 0

    def test_vender_tudo_tira_o_item_da_vitrine(self, publico, loja, vitrine_ligada, catalogo):
        catalogo["com_estoque"].saldo = 0
        catalogo["com_estoque"].save()

        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        assert corpo["total_itens"] == 0

    @pytest.mark.parametrize(
        "saldo,esperado",
        [(1, "ultima_unidade"), (2, "poucas_unidades"), (3, "poucas_unidades"),
         (4, "disponivel"), (50, "disponivel")],
    )
    def test_faixas_de_disponibilidade(self, publico, loja, vitrine_ligada,
                                       catalogo, saldo, esperado):
        catalogo["com_estoque"].saldo = saldo
        catalogo["com_estoque"].save()

        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        assert corpo["produtos"][0]["opcoes"][0]["disponibilidade"] == esperado


class TestIsolamento:
    def test_vitrine_de_uma_loja_nao_mostra_produto_de_outra(
        self, publico, loja, outra_loja, vitrine_ligada, catalogo
    ):
        configuracao = outra_loja.configuracao
        configuracao.vitrine_publica = True
        configuracao.save()

        produto = Produto.objects.create(loja=outra_loja, nome="Produto Secreto B")
        Variacao.objects.create(
            loja=outra_loja, produto=produto, sabor="Sabor B",
            preco_custo=Decimal("10.00"), preco_venda=Decimal("20.00"), saldo=9,
        )

        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        assert "Produto Secreto B" not in str(corpo)
        assert corpo["total_itens"] == 1

    def test_nao_expoe_clientes_nem_usuarios(
        self, publico, loja, vitrine_ligada, catalogo, cliente, dono
    ):
        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        texto = str(corpo)
        assert cliente.nome not in texto
        assert cliente.telefone not in texto
        assert dono.email not in texto
        assert dono.nome not in texto

    def test_a_resposta_tem_exatamente_as_chaves_previstas(
        self, publico, loja, vitrine_ligada, catalogo
    ):
        """
        Trava contra vazamento futuro: um campo novo no serializer não entra
        na resposta pública sem que este teste seja atualizado de propósito.
        """
        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()

        assert set(corpo) == {
            "loja", "mensagem", "mostrar_preco", "produtos", "total_itens", "aviso_idade",
        }
        assert set(corpo["loja"]) == {"nome", "cidade", "uf", "whatsapp"}
        assert set(corpo["produtos"][0]) == {
            "nome", "marca", "categoria", "descricao", "opcoes",
        }
        assert set(corpo["produtos"][0]["opcoes"][0]) == {
            "sabor", "nicotina_mg", "puffs", "disponibilidade", "preco_centavos",
        }
