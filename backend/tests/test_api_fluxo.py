"""
Fluxo ponta a ponta pela API, como o frontend usa.

Cobre o caminho real: cadastrar loja → criar produto → dar entrada →
abrir caixa → vender → conferir estoque, caixa, financeiro e relatórios.
"""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


class TestCadastroELogin:
    def test_cadastro_cria_loja_dono_e_ja_devolve_token(self, api):
        resposta = api.post("/api/auth/cadastrar/", {
            "loja_nome": "Vape do Zé",
            "nome": "José",
            "email": "ze@vape.com",
            "senha": "SenhaMuitoForte123",
        }, format="json")

        assert resposta.status_code == 201
        corpo = resposta.json()
        assert corpo["access"] and corpo["refresh"]
        assert corpo["usuario"]["papel"] == "dono"
        assert corpo["usuario"]["loja"]["nome"] == "Vape do Zé"
        assert corpo["usuario"]["loja"]["slug"] == "vape-do-ze"

    def test_email_duplicado_e_recusado(self, api, dono):
        resposta = api.post("/api/auth/cadastrar/", {
            "loja_nome": "Outra", "nome": "X",
            "email": "dono@a.com", "senha": "SenhaMuitoForte123",
        }, format="json")
        assert resposta.status_code == 400
        assert "email" in resposta.json()

    def test_senha_fraca_e_recusada(self, api):
        resposta = api.post("/api/auth/cadastrar/", {
            "loja_nome": "Loja", "nome": "X",
            "email": "x@x.com", "senha": "123",
        }, format="json")
        assert resposta.status_code == 400

    def test_login_devolve_token_e_usuario(self, api, dono):
        resposta = api.post("/api/auth/token/", {
            "email": "dono@a.com", "password": "SenhaForte123",
        }, format="json")
        assert resposta.status_code == 200
        assert resposta.json()["usuario"]["email"] == "dono@a.com"

    def test_token_funciona_no_header(self, api, dono):
        token = api.post("/api/auth/token/", {
            "email": "dono@a.com", "password": "SenhaForte123",
        }, format="json").json()["access"]

        autenticado = APIClient()
        autenticado.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        assert autenticado.get("/api/auth/eu/").status_code == 200


class TestFluxoCompleto:
    def test_do_cadastro_do_produto_ao_relatorio(self, api_dono, loja):
        # 1. cadastro do produto com uma variação
        produto = api_dono.post("/api/produtos/", {
            "nome": "Ignite V150",
            "tipo": "descartavel",
            "variacoes": [{
                "sabor": "Mint",
                "nicotina_mg": "5.00",
                "puffs": 15000,
                "sku": "IGN-V150-MINT",
                "preco_custo_centavos": 4000,
                "preco_venda_centavos": 9000,
                "estoque_minimo": 3,
            }],
        }, format="json")
        assert produto.status_code == 201, produto.json()
        variacao_id = produto.json()["variacoes"][0]["id"]

        # 2. entrada de estoque
        entrada = api_dono.post("/api/estoque/movimentos/entrada/", {
            "variacao": variacao_id, "quantidade": 10,
            "custo_unitario_centavos": 4000, "documento": "NF 123",
        }, format="json")
        assert entrada.status_code == 201
        assert entrada.json()["saldo_apos"] == 10

        # 3. abertura do caixa
        caixa = api_dono.post("/api/caixas/abrir/", {"saldo_inicial_centavos": 10000},
                              format="json")
        assert caixa.status_code == 201

        # 4. venda rápida: 2 unidades, pago em dinheiro com troco
        venda = api_dono.post("/api/vendas/rapida/", {
            "itens": [{"variacao": variacao_id, "quantidade": 2}],
            "pagamentos": [{"forma": "dinheiro", "valor_centavos": 20000}],
        }, format="json")
        assert venda.status_code == 201, venda.json()
        corpo = venda.json()
        assert corpo["total_centavos"] == 18000
        assert corpo["status"] == "finalizada"
        assert corpo["pagamentos"][0]["troco_centavos"] == 2000
        assert corpo["lucro_centavos"] == 10000  # 18000 − 8000 de custo

        # 5. estoque baixou
        posicao = api_dono.get(f"/api/variacoes/{variacao_id}/").json()
        assert posicao["saldo"] == 8

        # 6. caixa recebeu só o líquido (100 inicial + 180 da venda)
        atual = api_dono.get("/api/caixas/atual/").json()
        assert atual["aberto"] is True
        assert atual["saldo_atual_centavos"] == 28000

        # 7. financeiro registrou a receita
        financeiro = api_dono.get("/api/financeiro/lancamentos/resumo/").json()
        assert financeiro["recebido_no_mes_centavos"] == 18000

        # 8. dashboard reflete a venda
        painel = api_dono.get("/api/relatorios/dashboard/").json()
        assert painel["hoje"]["vendas"] == 1
        assert painel["hoje"]["faturamento_centavos"] == 18000
        assert painel["estoque"]["unidades"] == 8
        assert painel["caixa"]["aberto"] is True

        # 9. mais vendidos
        ranking = api_dono.get("/api/relatorios/mais-vendidos/").json()
        assert ranking["itens"][0]["unidades"] == 2

        # 10. fechamento do caixa conferindo o valor certo
        caixa_id = caixa.json()["id"]
        fechamento = api_dono.post(f"/api/caixas/{caixa_id}/fechar/",
                                   {"saldo_informado_centavos": 28000}, format="json")
        assert fechamento.status_code == 200
        assert fechamento.json()["diferenca_centavos"] == 0

    def test_venda_e_cancelamento_restauram_o_estado(self, api_dono, variacao):
        api_dono.post("/api/caixas/abrir/", {"saldo_inicial_centavos": 0}, format="json")

        venda = api_dono.post("/api/vendas/rapida/", {
            "itens": [{"variacao": variacao.id, "quantidade": 3}],
            "pagamentos": [{"forma": "pix", "valor_centavos": 15000}],
        }, format="json").json()

        assert api_dono.get(f"/api/variacoes/{variacao.id}/").json()["saldo"] == 7

        cancelamento = api_dono.post(f"/api/vendas/{venda['id']}/cancelar/",
                                     {"motivo": "Cliente desistiu"}, format="json")
        assert cancelamento.status_code == 200
        assert api_dono.get(f"/api/variacoes/{variacao.id}/").json()["saldo"] == 10

    def test_busca_do_pdv_prioriza_codigo_de_barras(self, api_dono, loja):
        api_dono.post("/api/produtos/", {
            "nome": "Oxbar G8000",
            "variacoes": [
                {"sabor": "Grape", "codigo_barras": "7891234567890",
                 "preco_venda_centavos": 7000, "preco_custo_centavos": 4000},
                {"sabor": "Cherry", "preco_venda_centavos": 7000,
                 "preco_custo_centavos": 4000},
            ],
        }, format="json")

        exato = api_dono.get("/api/variacoes/busca-pdv/?q=7891234567890").json()
        assert len(exato) == 1
        assert exato[0]["sabor"] == "Grape"

        por_nome = api_dono.get("/api/variacoes/busca-pdv/?q=oxbar").json()
        assert len(por_nome) == 2


class TestCompras:
    def test_receber_compra_da_entrada_e_gera_conta_a_pagar(self, api_dono, variacao):
        fornecedor = api_dono.post("/api/fornecedores/",
                                   {"nome": "Distribuidora X"}, format="json").json()

        compra = api_dono.post("/api/compras/", {
            "fornecedor": fornecedor["id"],
            "data": "2026-09-15",
            "vencimento": "2026-10-15",
            "numero_documento": "NF 998",
            "itens": [{"variacao": variacao.id, "quantidade": 20,
                       "custo_unitario_centavos": 2500}],
        }, format="json")
        assert compra.status_code == 201, compra.json()
        assert compra.json()["status"] == "rascunho"
        assert compra.json()["total_centavos"] == 50000

        # rascunho não mexe no estoque
        assert api_dono.get(f"/api/variacoes/{variacao.id}/").json()["saldo"] == 10

        recebimento = api_dono.post(f"/api/compras/{compra.json()['id']}/receber/",
                                    {}, format="json")
        assert recebimento.status_code == 200
        assert recebimento.json()["status"] == "recebida"
        assert api_dono.get(f"/api/variacoes/{variacao.id}/").json()["saldo"] == 30

        # conta a pagar criada
        contas = api_dono.get("/api/financeiro/lancamentos/?tipo=despesa").json()
        assert contas["count"] == 1
        assert contas["results"][0]["valor_centavos"] == 50000

    def test_cancelar_compra_recebida_estorna(self, api_dono, variacao):
        fornecedor = api_dono.post("/api/fornecedores/", {"nome": "Dist Y"},
                                   format="json").json()
        compra = api_dono.post("/api/compras/", {
            "fornecedor": fornecedor["id"], "data": "2026-09-15",
            "itens": [{"variacao": variacao.id, "quantidade": 5,
                       "custo_unitario_centavos": 3000}],
        }, format="json").json()

        api_dono.post(f"/api/compras/{compra['id']}/receber/", {}, format="json")
        assert api_dono.get(f"/api/variacoes/{variacao.id}/").json()["saldo"] == 15

        api_dono.post(f"/api/compras/{compra['id']}/cancelar/",
                      {"motivo": "Nota errada"}, format="json")
        assert api_dono.get(f"/api/variacoes/{variacao.id}/").json()["saldo"] == 10


class TestFinanceiro:
    def test_lancamento_manual_e_baixa(self, api_dono):
        categoria = api_dono.post("/api/financeiro/categorias/",
                                  {"nome": "Aluguel", "tipo": "despesa"},
                                  format="json").json()

        lancamento = api_dono.post("/api/financeiro/lancamentos/", {
            "tipo": "despesa", "categoria": categoria["id"],
            "descricao": "Aluguel de setembro", "valor_centavos": 250000,
            "vencimento": "2026-09-30",
        }, format="json")
        assert lancamento.status_code == 201
        assert lancamento.json()["status"] == "pendente"

        baixa = api_dono.post(f"/api/financeiro/lancamentos/{lancamento.json()['id']}/baixar/",
                              {"forma_pagamento": "pix"}, format="json")
        assert baixa.status_code == 200
        assert baixa.json()["status"] == "pago"
        assert baixa.json()["pago_em"] is not None

    def test_categoria_de_tipo_incompativel_e_recusada(self, api_dono):
        categoria = api_dono.post("/api/financeiro/categorias/",
                                  {"nome": "Serviços", "tipo": "despesa"},
                                  format="json").json()
        resposta = api_dono.post("/api/financeiro/lancamentos/", {
            "tipo": "receita", "categoria": categoria["id"],
            "descricao": "Errado", "valor_centavos": 1000,
            "vencimento": "2026-09-30",
        }, format="json")
        assert resposta.status_code == 400


class TestDocumentacao:
    def test_schema_openapi_e_gerado(self, api_dono):
        resposta = api_dono.get("/api/schema/")
        assert resposta.status_code == 200


class TestProtecaoContraForcaBruta:
    def test_login_tem_limite_de_tentativas(self, api, dono, monkeypatch):
        """
        O throttle fica desligado na suíte (senão atravessaria testes); aqui
        ele é religado de propósito para provar que protege o login.

        A taxa é trocada na classe, e não via settings, porque
        `SimpleRateThrottle.THROTTLE_RATES` é lido uma única vez na
        importação do módulo.
        """
        from django.core.cache import cache
        from rest_framework.throttling import SimpleRateThrottle

        cache.clear()
        monkeypatch.setattr(
            SimpleRateThrottle, "THROTTLE_RATES", {"login": "3/min", "cadastro": "5/hour"}
        )

        codigos = [
            api.post("/api/auth/token/",
                     {"email": "dono@a.com", "password": "errada"}, format="json").status_code
            for _ in range(5)
        ]
        assert 429 in codigos, "o login precisa barrar tentativas repetidas"
        cache.clear()
