"""
Isolamento multi-tenant (ADR-0001).

Este arquivo é a rede de segurança do SaaS: se um `get_queryset()` esquecer o
recorte por loja, um teste daqui quebra. **Todo endpoint novo entra aqui.**
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.clientes.models import Cliente
from apps.financeiro.models import Lancamento, TipoLancamento
from apps.fornecedores.models import Fornecedor
from apps.produtos.models import Categoria, Marca
from apps.usuarios.models import Papel, Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def dados_da_outra_loja(outra_loja):
    """Um registro de cada tipo pertencente à loja B."""
    from tests.conftest_helpers import criar_variacao_zerada

    variacao = criar_variacao_zerada(outra_loja, nome="Produto Secreto B")
    return {
        "categoria": Categoria.objects.create(loja=outra_loja, nome="Categoria B"),
        "marca": Marca.objects.create(loja=outra_loja, nome="Marca B"),
        "produto": variacao.produto,
        "variacao": variacao,
        "cliente": Cliente.objects.create(loja=outra_loja, nome="Cliente B"),
        "fornecedor": Fornecedor.objects.create(loja=outra_loja, nome="Fornecedor B"),
        "lancamento": Lancamento.objects.create(
            loja=outra_loja, tipo=TipoLancamento.DESPESA, descricao="Aluguel B",
            valor=Decimal("1000.00"), vencimento="2026-12-01",
        ),
    }


ENDPOINTS_DE_LISTAGEM = [
    "/api/categorias/",
    "/api/marcas/",
    "/api/produtos/",
    "/api/variacoes/",
    "/api/clientes/",
    "/api/fornecedores/",
    "/api/compras/",
    "/api/vendas/",
    "/api/caixas/",
    "/api/estoque/movimentos/",
    "/api/estoque/posicao/",
    "/api/financeiro/lancamentos/",
    "/api/financeiro/categorias/",
    "/api/usuarios/",
]


class TestListagensNaoVazam:
    @pytest.mark.parametrize("url", ENDPOINTS_DE_LISTAGEM)
    def test_listagem_so_mostra_a_propria_loja(self, api_dono, dados_da_outra_loja, url):
        resposta = api_dono.get(url)
        assert resposta.status_code == 200, f"{url} respondeu {resposta.status_code}"

        corpo = resposta.json()
        resultados = corpo["results"] if isinstance(corpo, dict) else corpo
        texto = str(resultados)
        for proibido in ("Categoria B", "Marca B", "Produto Secreto B",
                         "Cliente B", "Fornecedor B", "Aluguel B", "dono@b.com"):
            assert proibido not in texto, f"{url} vazou “{proibido}” da outra loja"


class TestDetalhesNaoVazam:
    def test_produto_de_outra_loja_da_404(self, api_dono, dados_da_outra_loja):
        alvo = dados_da_outra_loja["produto"].id
        assert api_dono.get(f"/api/produtos/{alvo}/").status_code == 404

    def test_cliente_de_outra_loja_da_404(self, api_dono, dados_da_outra_loja):
        alvo = dados_da_outra_loja["cliente"].id
        assert api_dono.get(f"/api/clientes/{alvo}/").status_code == 404

    def test_lancamento_de_outra_loja_da_404(self, api_dono, dados_da_outra_loja):
        alvo = dados_da_outra_loja["lancamento"].id
        assert api_dono.get(f"/api/financeiro/lancamentos/{alvo}/").status_code == 404

    def test_variacao_de_outra_loja_da_404(self, api_dono, dados_da_outra_loja):
        alvo = dados_da_outra_loja["variacao"].id
        assert api_dono.get(f"/api/variacoes/{alvo}/").status_code == 404


class TestEscritaNaoVaza:
    """Vazamento por escrita: apontar meu registro para um id da outra loja."""

    def test_nao_cria_produto_com_categoria_de_outra_loja(self, api_dono, dados_da_outra_loja):
        resposta = api_dono.post("/api/produtos/", {
            "nome": "Tentativa",
            "categoria": dados_da_outra_loja["categoria"].id,
        }, format="json")
        assert resposta.status_code == 400
        assert "categoria" in resposta.json()

    def test_nao_vende_item_de_outra_loja(self, api_dono, dados_da_outra_loja):
        resposta = api_dono.post("/api/vendas/abrir/", {
            "itens": [{"variacao": dados_da_outra_loja["variacao"].id, "quantidade": 1}],
        }, format="json")
        assert resposta.status_code == 400

    def test_nao_vincula_cliente_de_outra_loja_na_venda(self, api_dono, variacao,
                                                        dados_da_outra_loja):
        resposta = api_dono.post("/api/vendas/abrir/", {
            "cliente": dados_da_outra_loja["cliente"].id,
            "itens": [{"variacao": variacao.id, "quantidade": 1}],
        }, format="json")
        assert resposta.status_code == 400

    def test_nao_compra_com_fornecedor_de_outra_loja(self, api_dono, variacao,
                                                     dados_da_outra_loja):
        resposta = api_dono.post("/api/compras/", {
            "fornecedor": dados_da_outra_loja["fornecedor"].id,
            "data": "2026-09-15",
            "itens": [{"variacao": variacao.id, "quantidade": 1,
                       "custo_unitario_centavos": 1000}],
        }, format="json")
        assert resposta.status_code == 400

    def test_nao_edita_registro_de_outra_loja(self, api_dono, dados_da_outra_loja):
        alvo = dados_da_outra_loja["cliente"].id
        resposta = api_dono.patch(f"/api/clientes/{alvo}/", {"nome": "Invadido"},
                                  format="json")
        assert resposta.status_code == 404
        dados_da_outra_loja["cliente"].refresh_from_db()
        assert dados_da_outra_loja["cliente"].nome == "Cliente B"

    def test_nao_exclui_registro_de_outra_loja(self, api_dono, dados_da_outra_loja):
        alvo = dados_da_outra_loja["fornecedor"].id
        assert api_dono.delete(f"/api/fornecedores/{alvo}/").status_code == 404
        assert Fornecedor.objects.filter(id=alvo).exists()

    def test_estoque_de_outra_loja_nao_pode_ser_movimentado(self, api_dono,
                                                            dados_da_outra_loja):
        resposta = api_dono.post("/api/estoque/movimentos/entrada/", {
            "variacao": dados_da_outra_loja["variacao"].id,
            "quantidade": 100,
        }, format="json")
        assert resposta.status_code == 400
        dados_da_outra_loja["variacao"].refresh_from_db()
        assert dados_da_outra_loja["variacao"].saldo == 0


class TestNumeracaoIndependente:
    def test_numero_de_venda_recomeca_em_cada_loja(self, loja, outra_loja, dono, dono_outra):
        from decimal import Decimal

        from apps.vendas.servicos import abrir_caixa, criar_venda
        from tests.conftest_helpers import criar_variacao_zerada

        abrir_caixa(loja=loja, usuario=dono, saldo_inicial=Decimal("0"))
        abrir_caixa(loja=outra_loja, usuario=dono_outra, saldo_inicial=Decimal("0"))

        variacao_a = criar_variacao_zerada(loja)
        variacao_b = criar_variacao_zerada(outra_loja)

        venda_a = criar_venda(loja=loja, usuario=dono,
                              itens=[{"variacao": variacao_a, "quantidade": 1}])
        venda_b = criar_venda(loja=outra_loja, usuario=dono_outra,
                              itens=[{"variacao": variacao_b, "quantidade": 1}])

        assert venda_a.numero == 1
        assert venda_b.numero == 1, "cada loja tem sua própria sequência"


class TestAcesso:
    def test_sem_token_nao_entra(self, dados_da_outra_loja):
        for url in ENDPOINTS_DE_LISTAGEM:
            assert APIClient().get(url).status_code == 401, url

    def test_usuario_de_loja_inativa_nao_entra(self, api, loja, dono):
        loja.ativa = False
        loja.save()
        api.force_authenticate(user=dono)
        assert api.get("/api/produtos/").status_code == 403

    def test_superusuario_sem_loja_nao_acessa_a_api(self, api, db):
        suporte = Usuario.objects.create_superuser(email="suporte@sistema.com",
                                                   password="SenhaForte123", nome="Suporte")
        api.force_authenticate(user=suporte)
        assert api.get("/api/produtos/").status_code == 403

    def test_login_de_loja_inativa_e_recusado(self, api, loja, dono):
        loja.ativa = False
        loja.save()
        resposta = api.post("/api/auth/token/",
                            {"email": "dono@a.com", "password": "SenhaForte123"},
                            format="json")
        assert resposta.status_code == 400


class TestPermissoesPorPapel:
    def test_vendedor_nao_ve_o_financeiro(self, api_vendedor):
        assert api_vendedor.get("/api/financeiro/lancamentos/").status_code == 403

    def test_vendedor_nao_cria_produto(self, api_vendedor):
        resposta = api_vendedor.post("/api/produtos/", {"nome": "Novo"}, format="json")
        assert resposta.status_code == 403

    def test_vendedor_consulta_produtos(self, api_vendedor):
        assert api_vendedor.get("/api/produtos/").status_code == 200

    def test_vendedor_nao_gerencia_usuarios(self, api_vendedor):
        assert api_vendedor.get("/api/usuarios/").status_code == 403

    def test_vendedor_cadastra_cliente_no_balcao(self, api_vendedor):
        resposta = api_vendedor.post("/api/clientes/", {"nome": "Maria"}, format="json")
        assert resposta.status_code == 201

    def test_gerente_nao_cria_usuario_dono(self, api, gerente):
        api.force_authenticate(user=gerente)
        resposta = api.post("/api/usuarios/", {
            "nome": "Falso Dono", "email": "falso@a.com",
            "papel": Papel.DONO, "senha": "SenhaForte123",
        }, format="json")
        assert resposta.status_code == 400
