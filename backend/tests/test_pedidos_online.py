"""
Pedido on-line com Pix estático (ADR-0004).

O que importa aqui: o Pix sai certo (o banco recusa código com CRC errado),
a reserva não deixa vender a mesma unidade duas vezes, só a aprovação da
loja vira venda, e o cliente acompanha a entrega sem ver o que não deve.
"""

from datetime import timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.core.exceptions import CaixaFechado, ErroDeNegocio
from apps.financeiro.models import Lancamento
from apps.pedidos import servicos
from apps.pedidos.models import PedidoOnline, StatusPedido
from apps.pedidos.pix import crc16, gerar_brcode, normalizar_chave
from apps.vendas.models import FormaPagamento, StatusVenda
from apps.vendas.servicos import criar_venda, finalizar_venda

pytestmark = pytest.mark.django_db

CHAVE = "123e4567-e12b-12d1-a456-426655440000"


@pytest.fixture
def publico():
    return APIClient()


@pytest.fixture
def venda_online(loja):
    configuracao = loja.configuracao
    configuracao.vitrine_publica = True
    configuracao.vitrine_whatsapp = "86999998888"
    configuracao.venda_online = True
    configuracao.pix_chave = CHAVE
    configuracao.pix_nome = "Vaporize"
    configuracao.pix_cidade = "Teresina"
    configuracao.save()
    return configuracao


def _corpo(variacao, quantidade=1, **extra):
    corpo = {
        "telefone": "(86) 99567-5461",
        "codinome": "Pjuan",
        "declarou_maioridade": True,
        "tipo_entrega": "retirada",
        "itens": [{"variacao": variacao.pk, "quantidade": quantidade}],
    }
    corpo.update(extra)
    return corpo


def _criar(publico, loja, variacao, quantidade=1, **extra):
    return publico.post(
        f"/api/vitrine/{loja.slug}/pedidos/", _corpo(variacao, quantidade, **extra), format="json"
    )


def _imagem():
    saida = BytesIO()
    Image.new("RGB", (40, 40), (0, 120, 0)).save(saida, format="PNG")
    return SimpleUploadedFile("comprovante.png", saida.getvalue(), content_type="image/png")


# ------------------------------------------------------------------
# Pix
# ------------------------------------------------------------------


class TestPix:
    def test_crc_bate_com_o_exemplo_do_banco_central(self):
        # Exemplo do Manual de Padrões para Iniciação do Pix (BCB).
        payload = (
            "00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-426655440000"
            "5204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***6304"
        )
        assert crc16(payload) == "1D3D"

    def test_brcode_leva_chave_valor_e_codigo(self):
        codigo = gerar_brcode(chave=CHAVE, nome="Vaporizé Ltda", cidade="Teresina",
                              valor=Decimal("125"), identificador="K7Q2MX")
        assert CHAVE in codigo
        assert "5406125.00" in codigo
        assert "5913VAPORIZE LTDA" in codigo
        assert "6008TERESINA" in codigo
        assert "0506K7Q2MX" in codigo
        assert codigo[-8:-4] == "6304"
        assert crc16(codigo[:-4]) == codigo[-4:]

    def test_nome_e_cidade_longos_sao_cortados_no_limite(self):
        codigo = gerar_brcode(chave=CHAVE, nome="N" * 40, cidade="C" * 30, valor=Decimal("1"))
        assert "5925" + "N" * 25 in codigo
        assert "6015" + "C" * 15 in codigo

    @pytest.mark.parametrize("entrada,esperado", [
        (CHAVE.upper(), CHAVE),
        ("Loja@Exemplo.com", "loja@exemplo.com"),
        ("+55 (86) 99567-5461", "+5586995675461"),
        ("123.456.789-09", "12345678909"),
        ("12.345.678/0001-90", "12345678000190"),
    ])
    def test_normaliza_chave(self, entrada, esperado):
        assert normalizar_chave(entrada) == esperado

    def test_telefone_sem_ddi_e_recusado(self):
        with pytest.raises(ErroDeNegocio):
            normalizar_chave("86 99567-546")

    def test_sem_configuracao_nao_gera(self):
        with pytest.raises(ErroDeNegocio):
            gerar_brcode(chave="", nome="X", cidade="Y", valor=Decimal("1"))


# ------------------------------------------------------------------
# Criação e reserva
# ------------------------------------------------------------------


class TestCriarPedido:
    def test_cria_pedido_com_pix_e_reserva(self, publico, loja, venda_online, variacao):
        resposta = _criar(publico, loja, variacao, 2)
        assert resposta.status_code == 201, resposta.content
        corpo = resposta.json()
        assert corpo["status"] == "aguardando_pagamento"
        assert corpo["total_centavos"] == 10000
        assert corpo["pix_copia_cola"].startswith("000201")
        assert "540"+"6100.00" in corpo["pix_copia_cola"]
        assert len(corpo["token"]) >= 20

        pedido = PedidoOnline.objects.get(token=corpo["token"])
        assert pedido.telefone == "86995675461"
        variacao.refresh_from_db()
        assert variacao.saldo == 10, "reserva não pode escrever no saldo"
        assert servicos.reservas_ativas(loja) == {variacao.pk: 2}

    def test_preco_vem_do_servidor(self, publico, loja, venda_online, variacao):
        corpo = _corpo(variacao)
        corpo["itens"][0]["preco_unitario_centavos"] = 1
        resposta = publico.post(f"/api/vitrine/{loja.slug}/pedidos/", corpo, format="json")
        assert resposta.json()["total_centavos"] == 5000

    def test_venda_online_desligada_recusa(self, publico, loja, venda_online, variacao):
        venda_online.venda_online = False
        venda_online.save()
        assert _criar(publico, loja, variacao).status_code == 400

    def test_vitrine_desligada_da_404(self, publico, loja, venda_online, variacao):
        venda_online.vitrine_publica = False
        venda_online.save()
        assert _criar(publico, loja, variacao).status_code == 404

    def test_exige_declaracao_de_maioridade(self, publico, loja, venda_online, variacao):
        resposta = _criar(publico, loja, variacao, declarou_maioridade=False)
        assert resposta.status_code == 400
        assert "declarou_maioridade" in resposta.json()

    def test_exige_telefone_com_ddd(self, publico, loja, venda_online, variacao):
        assert _criar(publico, loja, variacao, telefone="9956-5461").status_code == 400

    def test_entrega_exige_localizacao_ou_endereco(self, publico, loja, venda_online, variacao):
        assert _criar(publico, loja, variacao, tipo_entrega="entrega").status_code == 400
        com_gps = _criar(
            publico, loja, variacao, tipo_entrega="entrega",
            latitude=-5.0919234567891, longitude=-42.8034123456789, precisao_m=12.7,
            referencia="Portão azul",
        )
        assert com_gps.status_code == 201, com_gps.content
        pedido = PedidoOnline.objects.get(token=com_gps.json()["token"])
        assert pedido.latitude == Decimal("-5.091923")
        assert pedido.precisao_m == 12

    def test_loja_sem_entrega_recusa_entrega(self, publico, loja, venda_online, variacao):
        venda_online.aceita_entrega = False
        venda_online.save()
        resposta = _criar(publico, loja, variacao, tipo_entrega="entrega", endereco="Rua A, 1")
        assert resposta.status_code == 400

    def test_nao_reserva_mais_que_o_disponivel(self, publico, loja, venda_online, variacao):
        assert _criar(publico, loja, variacao, 8).status_code == 201
        segundo = _criar(publico, loja, variacao, 3, telefone="86988887777")
        assert segundo.status_code == 400
        assert "Só restam 2" in str(segundo.json())

    def test_reserva_vencida_libera_a_unidade(self, publico, loja, venda_online, variacao):
        _criar(publico, loja, variacao, 10)
        PedidoOnline.objects.update(expira_em=timezone.now() - timedelta(seconds=1))
        assert _criar(publico, loja, variacao, 10, telefone="86988887777").status_code == 201

    def test_comprovante_enviado_continua_reservando(self, publico, loja, venda_online, variacao):
        token = _criar(publico, loja, variacao, 10).json()["token"]
        publico.post(f"/api/vitrine/{loja.slug}/pedidos/{token}/pagamento/")
        PedidoOnline.objects.update(expira_em=timezone.now() - timedelta(minutes=5))
        assert _criar(publico, loja, variacao, 1, telefone="86988887777").status_code == 400

    def test_limite_de_pedidos_pendentes_por_telefone(self, publico, loja, venda_online, variacao):
        for _ in range(servicos.MAXIMO_PENDENTES_POR_TELEFONE):
            assert _criar(publico, loja, variacao).status_code == 201
        assert _criar(publico, loja, variacao).status_code == 400

    def test_item_de_outra_loja_e_recusado(self, publico, loja, venda_online, outra_loja):
        from tests.conftest_helpers import criar_variacao_zerada

        alheia = criar_variacao_zerada(outra_loja)
        assert _criar(publico, loja, alheia).status_code == 400

    def test_vitrine_esconde_o_que_esta_todo_reservado(self, publico, loja, venda_online, variacao):
        _criar(publico, loja, variacao, 10)
        corpo = publico.get(f"/api/vitrine/{loja.slug}/").json()
        assert corpo["total_itens"] == 0
        assert corpo["venda_online"]["aceita_retirada"] is True


# ------------------------------------------------------------------
# Cliente: pagamento, consulta e cancelamento
# ------------------------------------------------------------------


class TestClienteAcompanha:
    def test_envia_comprovante(self, publico, loja, venda_online, variacao):
        token = _criar(publico, loja, variacao).json()["token"]
        resposta = publico.post(
            f"/api/vitrine/{loja.slug}/pedidos/{token}/pagamento/",
            {"comprovante": _imagem()}, format="multipart",
        )
        assert resposta.status_code == 200, resposta.content
        assert resposta.json()["status"] == "aguardando_conferencia"
        pedido = PedidoOnline.objects.get(token=token)
        assert pedido.comprovante
        assert "/media/" not in pedido.comprovante.path

    def test_comprovante_que_nao_e_imagem_e_recusado(self, publico, loja, venda_online, variacao):
        token = _criar(publico, loja, variacao).json()["token"]
        falso = SimpleUploadedFile("x.png", b"nao sou imagem", content_type="image/png")
        resposta = publico.post(
            f"/api/vitrine/{loja.slug}/pedidos/{token}/pagamento/",
            {"comprovante": falso}, format="multipart",
        )
        assert resposta.status_code == 400

    def test_pagina_do_pedido_nao_expoe_localizacao(self, publico, loja, venda_online, variacao):
        token = _criar(
            publico, loja, variacao, tipo_entrega="entrega", latitude=-5.09, longitude=-42.8,
            endereco="Rua Secreta, 10",
        ).json()["token"]
        texto = str(publico.get(f"/api/vitrine/{loja.slug}/pedidos/{token}/").json())
        assert "Rua Secreta" not in texto
        assert "-42.8" not in texto
        assert "99567" not in texto  # telefone sai mascarado

    def test_token_inexistente_da_404(self, publico, loja, venda_online):
        assert publico.get(f"/api/vitrine/{loja.slug}/pedidos/xyz/").status_code == 404

    def test_consulta_por_telefone(self, publico, loja, venda_online, variacao):
        _criar(publico, loja, variacao)
        _criar(publico, loja, variacao, telefone="86988887777")
        resposta = publico.post(
            f"/api/vitrine/{loja.slug}/meus-pedidos/", {"telefone": "+55 86 99567-5461"},
            format="json",
        )
        assert resposta.status_code == 200
        assert len(resposta.json()) == 1
        assert resposta.json()[0]["quantidade_itens"] == 1

    def test_consulta_nao_mostra_pedido_de_outra_loja(
        self, publico, loja, venda_online, outra_loja
    ):
        PedidoOnline.objects.create(
            loja=outra_loja, codigo="ZZZZZZ", telefone="86995675461", codinome="X",
            total=Decimal("1"), expira_em=timezone.now(),
        )
        resposta = publico.post(
            f"/api/vitrine/{loja.slug}/meus-pedidos/", {"telefone": "86995675461"}, format="json"
        )
        assert resposta.json() == []

    def test_cliente_cancela_antes_de_pagar_e_libera(self, publico, loja, venda_online, variacao):
        token = _criar(publico, loja, variacao, 10).json()["token"]
        resposta = publico.post(f"/api/vitrine/{loja.slug}/pedidos/{token}/cancelar/")
        assert resposta.json()["status"] == "cancelado"
        assert servicos.reservas_ativas(loja) == {}


# ------------------------------------------------------------------
# Loja: aprovação e entrega
# ------------------------------------------------------------------


@pytest.fixture
def pedido(publico, loja, venda_online, variacao):
    token = _criar(publico, loja, variacao, 2, tipo_entrega="entrega",
                   endereco="Rua A, 1").json()["token"]
    return PedidoOnline.objects.get(token=token)


class TestAprovacao:
    def test_aprovar_vira_venda_pix_sem_caixa_aberto(self, api_vendedor, pedido, variacao):
        resposta = api_vendedor.post(f"/api/pedidos-online/{pedido.pk}/aprovar/")
        assert resposta.status_code == 200, resposta.content
        assert resposta.json()["status"] == "preparando"

        pedido.refresh_from_db()
        venda = pedido.venda
        assert venda.status == StatusVenda.FINALIZADA
        assert venda.caixa is None
        assert venda.total == Decimal("100.00")
        assert list(venda.pagamentos.values_list("forma", flat=True)) == [FormaPagamento.PIX]
        assert venda.cliente.telefone == "86995675461"
        assert venda.cliente.nome == "Pjuan"
        variacao.refresh_from_db()
        assert variacao.saldo == 8
        assert Lancamento.objects.filter(venda=venda).count() == 1
        assert servicos.reservas_ativas(pedido.loja) == {}

    def test_aprovar_reaproveita_cliente_do_mesmo_telefone(self, api_dono, pedido, cliente):
        cliente.telefone = "86995675461"
        cliente.save()
        api_dono.post(f"/api/pedidos-online/{pedido.pk}/aprovar/")
        pedido.refresh_from_db()
        assert pedido.venda.cliente == cliente

    def test_nao_aprova_duas_vezes(self, api_dono, pedido):
        api_dono.post(f"/api/pedidos-online/{pedido.pk}/aprovar/")
        assert api_dono.post(f"/api/pedidos-online/{pedido.pk}/aprovar/").status_code == 400

    def test_aprova_pedido_expirado_se_cliente_pagou_atrasado(self, api_dono, pedido):
        PedidoOnline.objects.filter(pk=pedido.pk).update(
            expira_em=timezone.now() - timedelta(minutes=10)
        )
        assert api_dono.post(f"/api/pedidos-online/{pedido.pk}/aprovar/").status_code == 200

    def test_venda_no_balcao_continua_exigindo_caixa(self, loja, dono, variacao):
        itens = [{"variacao": variacao, "quantidade": 1}]
        venda = criar_venda(loja=loja, usuario=dono, itens=itens)
        with pytest.raises(CaixaFechado):
            finalizar_venda(venda=venda, usuario=dono,
                            pagamentos=[{"forma": "pix", "valor": Decimal("50.00")}])

    def test_dinheiro_sem_caixa_continua_recusado(self, loja, dono, variacao):
        itens = [{"variacao": variacao, "quantidade": 1}]
        venda = criar_venda(loja=loja, usuario=dono, itens=itens)
        with pytest.raises(CaixaFechado):
            finalizar_venda(venda=venda, usuario=dono, exigir_caixa=False,
                            pagamentos=[{"forma": "dinheiro", "valor": Decimal("50.00")}])

    def test_painel_baixa_o_comprovante(self, api_dono, publico, loja, pedido):
        publico.post(f"/api/vitrine/{loja.slug}/pedidos/{pedido.token}/pagamento/",
                     {"comprovante": _imagem()}, format="multipart")
        resposta = api_dono.get(f"/api/pedidos-online/{pedido.pk}/comprovante/")
        assert resposta.status_code == 200
        assert resposta["Content-Type"] == "image/jpeg"

    def test_resumo_conta_pendentes(self, api_dono, pedido):
        assert api_dono.get("/api/pedidos-online/resumo/").json()["aguardando_pagamento"] == 1


class TestEntrega:
    def test_fluxo_completo_que_o_cliente_ve(self, api_dono, publico, loja, pedido):
        api_dono.post(f"/api/pedidos-online/{pedido.pk}/aprovar/")
        previsao = (timezone.now() + timedelta(hours=1)).isoformat()
        resposta = api_dono.post(
            f"/api/pedidos-online/{pedido.pk}/entrega/",
            {"status": "saiu_entrega", "previsao_entrega": previsao,
             "recado_loja": "Motoboy de moto vermelha"},
            format="json",
        )
        assert resposta.status_code == 200, resposta.content

        visto = publico.get(f"/api/vitrine/{loja.slug}/pedidos/{pedido.token}/").json()
        assert visto["status"] == "saiu_entrega"
        assert visto["previsao_entrega"]
        assert visto["recado_loja"] == "Motoboy de moto vermelha"
        assert visto["pix_copia_cola"] is None
        assert visto["venda_numero"] == 1

        api_dono.post(f"/api/pedidos-online/{pedido.pk}/entrega/",
                      {"status": "entregue"}, format="json")
        pedido.refresh_from_db()
        assert pedido.entregue_em is not None

    def test_entrega_nao_vira_pronto_para_retirada(self, api_dono, pedido):
        api_dono.post(f"/api/pedidos-online/{pedido.pk}/aprovar/")
        resposta = api_dono.post(f"/api/pedidos-online/{pedido.pk}/entrega/",
                                 {"status": "pronto_retirada"}, format="json")
        assert resposta.status_code == 400

    def test_sem_pagamento_nao_tem_entrega(self, api_dono, pedido):
        resposta = api_dono.post(f"/api/pedidos-online/{pedido.pk}/entrega/",
                                 {"status": "saiu_entrega"}, format="json")
        assert resposta.status_code == 400

    def test_lista_de_entregas_para_a_rota(self, api_dono, pedido):
        assert api_dono.get("/api/pedidos-online/?entregas=1").json()["count"] == 0
        api_dono.post(f"/api/pedidos-online/{pedido.pk}/aprovar/")
        corpo = api_dono.get("/api/pedidos-online/?entregas=1").json()
        assert corpo["count"] == 1
        assert corpo["results"][0]["maps_url"].startswith("https://www.google.com/maps")


class TestCancelamento:
    def test_cancelar_pedido_pago_estorna_a_venda(self, api_dono, pedido, variacao):
        api_dono.post(f"/api/pedidos-online/{pedido.pk}/aprovar/")
        resposta = api_dono.post(f"/api/pedidos-online/{pedido.pk}/cancelar/",
                                 {"motivo": "Cliente desistiu"}, format="json")
        assert resposta.status_code == 200
        pedido.refresh_from_db()
        assert pedido.status == StatusPedido.CANCELADO
        assert pedido.venda.status == StatusVenda.CANCELADA
        variacao.refresh_from_db()
        assert variacao.saldo == 10

    def test_vendedor_nao_cancela_pedido_pago(self, api_vendedor, pedido):
        api_vendedor.post(f"/api/pedidos-online/{pedido.pk}/aprovar/")
        assert api_vendedor.post(f"/api/pedidos-online/{pedido.pk}/cancelar/").status_code == 400

    def test_vendedor_cancela_pedido_nao_pago(self, api_vendedor, pedido):
        assert api_vendedor.post(f"/api/pedidos-online/{pedido.pk}/cancelar/").status_code == 200


class TestConfiguracao:
    def test_ligar_venda_online_exige_pix(self, api_dono, loja):
        loja.configuracao.vitrine_publica = True
        loja.configuracao.save()
        resposta = api_dono.patch("/api/loja/configuracao/", {"venda_online": True}, format="json")
        assert resposta.status_code == 400

    def test_chave_e_normalizada_ao_salvar(self, api_dono, loja):
        resposta = api_dono.patch(
            "/api/loja/configuracao/",
            {"vitrine_publica": True, "venda_online": True, "pix_chave": CHAVE.upper(),
             "pix_nome": "Vaporize", "pix_cidade": "Teresina"},
            format="json",
        )
        assert resposta.status_code == 200, resposta.content
        loja.configuracao.refresh_from_db()
        assert loja.configuracao.pix_chave == CHAVE
