from rest_framework import serializers

from apps.clientes.models import Cliente
from apps.core.serializers import CentavosField
from apps.produtos.models import Variacao

from .models import (
    Caixa,
    FormaPagamento,
    ItemVenda,
    MovimentoCaixa,
    Pagamento,
    TipoMovimentoCaixa,
    Venda,
)

# ------------------------------------------------------------------
# Caixa
# ------------------------------------------------------------------


class MovimentoCaixaSerializer(serializers.ModelSerializer):
    valor_centavos = CentavosField(source="valor", read_only=True)
    valor_com_sinal_centavos = CentavosField(source="valor_com_sinal", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    usuario_nome = serializers.CharField(source="usuario.nome", read_only=True)

    class Meta:
        model = MovimentoCaixa
        fields = [
            "id", "caixa", "tipo", "tipo_display", "valor_centavos",
            "valor_com_sinal_centavos", "descricao", "usuario", "usuario_nome",
            "venda", "criado_em",
        ]
        read_only_fields = fields


class CaixaSerializer(serializers.ModelSerializer):
    saldo_inicial_centavos = CentavosField(source="saldo_inicial", read_only=True)
    saldo_informado_centavos = CentavosField(source="saldo_informado", read_only=True)
    saldo_calculado_centavos = CentavosField(source="saldo_calculado", read_only=True)
    diferenca_centavos = CentavosField(source="diferenca", read_only=True)
    usuario_abertura_nome = serializers.CharField(source="usuario_abertura.nome", read_only=True)
    usuario_fechamento_nome = serializers.CharField(
        source="usuario_fechamento.nome", read_only=True, default=""
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Caixa
        fields = [
            "id", "status", "status_display", "aberto_em", "fechado_em",
            "usuario_abertura", "usuario_abertura_nome",
            "usuario_fechamento", "usuario_fechamento_nome",
            "saldo_inicial_centavos", "saldo_informado_centavos",
            "saldo_calculado_centavos", "diferenca_centavos", "observacoes",
        ]
        read_only_fields = fields


class AbrirCaixaSerializer(serializers.Serializer):
    saldo_inicial_centavos = serializers.IntegerField(min_value=0, default=0)


class FecharCaixaSerializer(serializers.Serializer):
    saldo_informado_centavos = serializers.IntegerField(min_value=0)
    observacoes = serializers.CharField(max_length=500, required=False, allow_blank=True)


class MovimentarCaixaSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(
        choices=[TipoMovimentoCaixa.SANGRIA, TipoMovimentoCaixa.SUPRIMENTO]
    )
    valor_centavos = serializers.IntegerField(min_value=1)
    descricao = serializers.CharField(max_length=200, required=False, allow_blank=True)


# ------------------------------------------------------------------
# Venda
# ------------------------------------------------------------------


class ItemVendaSerializer(serializers.ModelSerializer):
    preco_unitario_centavos = CentavosField(source="preco_unitario", read_only=True)
    desconto_centavos = CentavosField(source="desconto", read_only=True)
    total_centavos = CentavosField(source="total", read_only=True)

    class Meta:
        model = ItemVenda
        fields = [
            "id", "variacao", "descricao", "quantidade",
            "preco_unitario_centavos", "desconto_centavos", "total_centavos",
        ]
        read_only_fields = fields


class PagamentoSerializer(serializers.ModelSerializer):
    valor_centavos = CentavosField(source="valor", read_only=True)
    troco_centavos = CentavosField(source="troco", read_only=True)
    forma_display = serializers.CharField(source="get_forma_display", read_only=True)

    class Meta:
        model = Pagamento
        fields = ["id", "forma", "forma_display", "valor_centavos", "troco_centavos",
                  "observacao"]
        read_only_fields = fields


class VendaSerializer(serializers.ModelSerializer):
    itens = ItemVendaSerializer(many=True, read_only=True)
    pagamentos = PagamentoSerializer(many=True, read_only=True)
    subtotal_centavos = CentavosField(source="subtotal", read_only=True)
    desconto_centavos = CentavosField(source="desconto", read_only=True)
    total_centavos = CentavosField(source="total", read_only=True)
    lucro_centavos = CentavosField(source="lucro", read_only=True)
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True, default="")
    vendedor_nome = serializers.CharField(source="usuario.nome", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Venda
        fields = [
            "id", "numero", "status", "status_display", "caixa",
            "cliente", "cliente_nome", "usuario", "vendedor_nome",
            "subtotal_centavos", "desconto_centavos", "total_centavos", "lucro_centavos",
            "observacoes", "itens", "pagamentos",
            "criado_em", "finalizada_em", "cancelada_em", "motivo_cancelamento",
        ]
        read_only_fields = fields


class VendaResumoSerializer(serializers.ModelSerializer):
    total_centavos = CentavosField(source="total", read_only=True)
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True, default="")
    vendedor_nome = serializers.CharField(source="usuario.nome", read_only=True)
    quantidade_itens = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Venda
        fields = [
            "id", "numero", "status", "status_display", "total_centavos",
            "cliente_nome", "vendedor_nome", "quantidade_itens",
            "criado_em", "finalizada_em",
        ]


class ItemEntradaSerializer(serializers.Serializer):
    """Item enviado pelo PDV ao criar a venda."""

    variacao = serializers.PrimaryKeyRelatedField(queryset=Variacao.objects.all())
    quantidade = serializers.IntegerField(min_value=1)
    preco_unitario_centavos = serializers.IntegerField(min_value=0, required=False)
    desconto_centavos = serializers.IntegerField(min_value=0, default=0)


class CriarVendaSerializer(serializers.Serializer):
    cliente = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.all(), required=False, allow_null=True
    )
    itens = ItemEntradaSerializer(many=True)
    desconto_centavos = serializers.IntegerField(min_value=0, default=0)
    observacoes = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_cliente(self, cliente):
        if cliente is None:
            return cliente
        if cliente.loja_id != self.context["request"].loja.id:
            raise serializers.ValidationError("O cliente informado não é desta loja.")
        return cliente

    def validate_itens(self, itens):
        if not itens:
            raise serializers.ValidationError("Informe ao menos um item.")
        loja = self.context["request"].loja
        for item in itens:
            if item["variacao"].loja_id != loja.id:
                raise serializers.ValidationError("Há itens que não pertencem a esta loja.")
        return itens


class PagamentoEntradaSerializer(serializers.Serializer):
    forma = serializers.ChoiceField(choices=FormaPagamento.choices)
    valor_centavos = serializers.IntegerField(min_value=1)
    observacao = serializers.CharField(max_length=140, required=False, allow_blank=True)


class FinalizarVendaSerializer(serializers.Serializer):
    pagamentos = PagamentoEntradaSerializer(many=True)

    def validate_pagamentos(self, pagamentos):
        if not pagamentos:
            raise serializers.ValidationError("Informe ao menos uma forma de pagamento.")
        return pagamentos


class VendaRapidaSerializer(CriarVendaSerializer):
    """
    Criar e finalizar numa chamada só — o caminho normal do balcão.

    Duas requisições para uma venda de 15 segundos é ruim no balcão cheio; o
    fluxo em dois passos continua disponível para venda em espera.
    """

    pagamentos = PagamentoEntradaSerializer(many=True)

    def validate_pagamentos(self, pagamentos):
        if not pagamentos:
            raise serializers.ValidationError("Informe ao menos uma forma de pagamento.")
        return pagamentos


class CancelarVendaSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True)
