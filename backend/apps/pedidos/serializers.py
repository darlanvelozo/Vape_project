from decimal import Decimal

from rest_framework import serializers

from apps.core.serializers import CentavosField

from .models import ItemPedidoOnline, PedidoOnline, StatusPedido, TipoEntrega
from .pix import gerar_brcode

# ------------------------------------------------------------------
# Entrada (vitrine)
# ------------------------------------------------------------------


class ItemEntradaSerializer(serializers.Serializer):
    variacao = serializers.IntegerField()
    quantidade = serializers.IntegerField(min_value=1, max_value=20)


class CriarPedidoSerializer(serializers.Serializer):
    telefone = serializers.CharField(max_length=30)
    codinome = serializers.CharField(max_length=60)
    declarou_maioridade = serializers.BooleanField()
    tipo_entrega = serializers.ChoiceField(choices=TipoEntrega.choices)
    itens = ItemEntradaSerializer(many=True)
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
        min_value=Decimal("-90"), max_value=Decimal("90"),
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True,
        min_value=Decimal("-180"), max_value=Decimal("180"),
    )
    precisao_m = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    endereco = serializers.CharField(max_length=200, required=False, allow_blank=True)
    referencia = serializers.CharField(max_length=200, required=False, allow_blank=True)
    observacoes = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def to_internal_value(self, dados):
        # O GPS do celular manda 15 casas; o banco guarda 6 (~10 cm).
        dados = dados.copy() if hasattr(dados, "copy") else dict(dados)
        for campo in ("latitude", "longitude"):
            valor = dados.get(campo)
            if valor not in (None, ""):
                try:
                    dados[campo] = round(float(valor), 6)
                except (TypeError, ValueError):
                    pass
        if dados.get("precisao_m") not in (None, ""):
            try:
                dados["precisao_m"] = int(float(dados["precisao_m"]))
            except (TypeError, ValueError):
                pass
        return super().to_internal_value(dados)


class ConsultaTelefoneSerializer(serializers.Serializer):
    telefone = serializers.CharField(max_length=30)


# ------------------------------------------------------------------
# Saída
# ------------------------------------------------------------------


class ItemPedidoSerializer(serializers.ModelSerializer):
    preco_unitario_centavos = CentavosField(source="preco_unitario")
    total_centavos = CentavosField(source="total")

    class Meta:
        model = ItemPedidoOnline
        fields = ["descricao", "quantidade", "preco_unitario_centavos", "total_centavos"]


def _telefone_mascarado(telefone: str) -> str:
    return f"({telefone[:2]}) •••••-{telefone[-4:]}" if len(telefone) >= 6 else ""


class PedidoPublicoSerializer(serializers.ModelSerializer):
    """
    O que o cliente vê pelo link do pedido.

    Não sai localização, endereço nem telefone completo: o link circula por
    WhatsApp e pode ser encaminhado.
    """

    itens = ItemPedidoSerializer(many=True, read_only=True)
    total_centavos = CentavosField(source="total")
    status_display = serializers.CharField(source="get_status_display")
    tipo_entrega_display = serializers.CharField(source="get_tipo_entrega_display")
    telefone = serializers.SerializerMethodField()
    pix_copia_cola = serializers.SerializerMethodField()
    comprovante_enviado = serializers.SerializerMethodField()
    venda_numero = serializers.SerializerMethodField()
    loja = serializers.SerializerMethodField()

    class Meta:
        model = PedidoOnline
        fields = [
            "codigo", "token", "codinome", "telefone", "status", "status_display",
            "tipo_entrega", "tipo_entrega_display", "itens", "total_centavos",
            "criado_em", "expira_em", "pix_copia_cola", "comprovante_enviado",
            "pago_em", "venda_numero", "previsao_entrega", "recado_loja",
            "saiu_em", "entregue_em", "cancelado_em", "motivo_cancelamento", "loja",
        ]

    def get_telefone(self, pedido):
        return _telefone_mascarado(pedido.telefone)

    def get_pix_copia_cola(self, pedido):
        if pedido.status not in (
            StatusPedido.AGUARDANDO_PAGAMENTO,
            StatusPedido.AGUARDANDO_CONFERENCIA,
            StatusPedido.EXPIRADO,
        ):
            return None
        configuracao = pedido.loja.configuracao
        try:
            return gerar_brcode(
                chave=configuracao.pix_chave, nome=configuracao.pix_nome,
                cidade=configuracao.pix_cidade, valor=pedido.total,
                identificador=pedido.codigo,
            )
        except Exception:  # noqa: BLE001 — chave mal configurada não derruba a página
            return None

    def get_comprovante_enviado(self, pedido):
        return bool(pedido.comprovante)

    def get_venda_numero(self, pedido):
        return pedido.venda.numero if pedido.venda_id else None

    def get_loja(self, pedido):
        configuracao = pedido.loja.configuracao
        dados = {
            "nome": pedido.loja.nome,
            "slug": pedido.loja.slug,
            "whatsapp": configuracao.vitrine_whatsapp,
            "pix_nome": configuracao.pix_nome,
        }
        if pedido.tipo_entrega == TipoEntrega.RETIRADA:
            dados["texto_retirada"] = configuracao.texto_retirada
        return dados


class PedidoResumoPublicoSerializer(serializers.ModelSerializer):
    """Linha da consulta por telefone: só o bastante para achar o pedido."""

    total_centavos = CentavosField(source="total")
    status_display = serializers.CharField(source="get_status_display")
    quantidade_itens = serializers.SerializerMethodField()

    class Meta:
        model = PedidoOnline
        fields = [
            "codigo", "token", "status", "status_display", "tipo_entrega",
            "total_centavos", "quantidade_itens", "criado_em", "previsao_entrega",
        ]

    def get_quantidade_itens(self, pedido):
        return sum(item.quantidade for item in pedido.itens.all())


class PedidoPainelSerializer(serializers.ModelSerializer):
    """O que a loja vê: tudo, incluindo localização e comprovante."""

    itens = ItemPedidoSerializer(many=True, read_only=True)
    total_centavos = CentavosField(source="total")
    status_display = serializers.CharField(source="get_status_display")
    tipo_entrega_display = serializers.CharField(source="get_tipo_entrega_display")
    tem_comprovante = serializers.SerializerMethodField()
    venda_numero = serializers.SerializerMethodField()
    aprovado_por_nome = serializers.SerializerMethodField()
    maps_url = serializers.SerializerMethodField()

    class Meta:
        model = PedidoOnline
        fields = [
            "id", "codigo", "token", "telefone", "codinome", "status", "status_display",
            "tipo_entrega", "tipo_entrega_display", "latitude", "longitude", "precisao_m",
            "endereco", "referencia", "observacoes", "maps_url", "itens", "total_centavos",
            "criado_em", "expira_em", "tem_comprovante", "comprovante_enviado_em",
            "venda", "venda_numero", "pago_em", "aprovado_por_nome",
            "previsao_entrega", "recado_loja", "saiu_em", "entregue_em",
            "cancelado_em", "motivo_cancelamento",
        ]

    def get_tem_comprovante(self, pedido):
        return bool(pedido.comprovante)

    def get_venda_numero(self, pedido):
        return pedido.venda.numero if pedido.venda_id else None

    def get_aprovado_por_nome(self, pedido):
        return pedido.aprovado_por.nome if pedido.aprovado_por_id else None

    def get_maps_url(self, pedido):
        if pedido.latitude is not None and pedido.longitude is not None:
            return f"https://www.google.com/maps?q={pedido.latitude},{pedido.longitude}"
        if pedido.endereco:
            from urllib.parse import quote

            return f"https://www.google.com/maps/search/?api=1&query={quote(pedido.endereco)}"
        return None


class AtualizarEntregaSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[StatusPedido.PREPARANDO, StatusPedido.PRONTO_RETIRADA,
                 StatusPedido.SAIU_ENTREGA, StatusPedido.ENTREGUE],
        required=False,
    )
    previsao_entrega = serializers.DateTimeField(required=False, allow_null=True)
    recado_loja = serializers.CharField(max_length=200, required=False, allow_blank=True)


class CancelarPedidoSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True)
