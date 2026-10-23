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

    def test_nao_altera_preco_de_modelo_de_outra_loja(self, api_dono, dados_da_outra_loja):
        variacao = dados_da_outra_loja["variacao"]
        resposta = api_dono.post(f"/api/produtos/{variacao.produto_id}/precos/",
                                 {"preco_venda_centavos": 1}, format="json")
        assert resposta.status_code == 404
        variacao.refresh_from_db()
        assert variacao.preco_venda == Decimal("40.00")

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


class TestViewsQueNaoSaoViewSet:
    """
    Regressão: `request.loja` vem do middleware, que roda **antes** de o DRF
    autenticar o JWT — ali `request.user` ainda é anônimo. Uma APIView que
    confie só nisso enxerga loja nenhuma: `/api/loja/` devolvia campos vazios,
    `/api/loja/configuracao/` estourava 409, e o PATCH criava uma loja nova em
    vez de atualizar a existente.
    """

    def test_dados_da_loja_vem_preenchidos(self, api_dono, loja):
        resposta = api_dono.get("/api/loja/")
        assert resposta.status_code == 200
        assert resposta.json()["nome"] == loja.nome
        assert resposta.json()["id"] == loja.id

    def test_configuracao_da_loja_responde(self, api_dono):
        resposta = api_dono.get("/api/loja/configuracao/")
        assert resposta.status_code == 200
        assert "permitir_fiado" in resposta.json()

    def test_patch_atualiza_a_loja_e_nao_cria_outra(self, api_dono, loja):
        from apps.lojas.models import Loja

        antes = Loja.objects.count()
        resposta = api_dono.patch("/api/loja/", {"cidade": "Campinas"}, format="json")

        assert resposta.status_code == 200
        assert Loja.objects.count() == antes, "nenhuma loja nova pode surgir de um PATCH"
        loja.refresh_from_db()
        assert loja.cidade == "Campinas"
        assert loja.nome, "o nome não pode ser apagado"

    def test_patch_da_configuracao_persiste(self, api_dono, loja):
        resposta = api_dono.patch(
            "/api/loja/configuracao/", {"prazo_fiado_dias": 15}, format="json"
        )
        assert resposta.status_code == 200
        loja.configuracao.refresh_from_db()
        assert loja.configuracao.prazo_fiado_dias == 15

    def test_relatorio_enxerga_so_a_propria_loja(self, api_dono, dados_da_outra_loja):
        resposta = api_dono.get("/api/relatorios/dashboard/")
        assert resposta.status_code == 200
        # A outra loja não tem venda, mas tem produto: o estoque não pode vazar.
        assert resposta.json()["estoque"]["unidades"] == 0

    def test_resultado_nao_soma_numeros_de_outra_loja(self, api_dono, dados_da_outra_loja):
        """O financeiro é o dado mais sensível: nada da loja B pode entrar."""
        corpo = api_dono.get("/api/relatorios/resultado/").json()

        assert corpo["resultado"]["faturamento_centavos"] == 0
        assert corpo["caixa"]["saidas_centavos"] == 0
        assert corpo["estoque"]["unidades"] == 0
        # A loja B tem uma despesa de R$ 1.000 pendente.
        assert corpo["a_pagar"]["total_centavos"] == 0

    def test_vendedor_nao_altera_dados_da_loja(self, api_vendedor):
        resposta = api_vendedor.patch("/api/loja/", {"nome": "Invadida"}, format="json")
        assert resposta.status_code == 400


class TestArquitetura:
    """
    Trava estrutural: toda view de domínio precisa resolver a loja depois da
    autenticação. Sem este teste, a próxima APIView escrita à mão repetiria o
    bug silenciosamente.
    """

    def test_toda_view_de_dominio_resolve_a_loja(self):
        import importlib

        from apps.core.views import ResolverLojaMixin

        # Views de autenticação não têm loja resolvida por definição: o
        # cadastro ainda vai criá-la, e login/refresh são anônimos.
        ISENTAS = {"LoginView", "CadastroLojaView", "AlterarSenhaView"}

        faltando = []
        for app in ("usuarios", "produtos", "estoque", "clientes",
                    "fornecedores", "vendas", "financeiro", "relatorios"):
            modulo = importlib.import_module(f"apps.{app}.views")
            for nome in dir(modulo):
                classe = getattr(modulo, nome)
                if not (isinstance(classe, type) and nome.endswith("View")):
                    continue
                if classe.__module__ != modulo.__name__ or nome in ISENTAS:
                    continue
                if not issubclass(classe, ResolverLojaMixin):
                    faltando.append(f"{app}.{nome}")

        assert not faltando, (
            "Estas views não resolvem a loja e enxergariam request.loja=None: "
            f"{faltando}. Herde de core.views.LojaAPIView."
        )
