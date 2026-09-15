from rest_framework import serializers

from apps.core.serializers import CentavosField
from apps.produtos.models import Variacao

from .models import MovimentoEstoque, TipoMovimento


class MovimentoEstoqueSerializer(serializers.ModelSerializer):
    custo_unitario_centavos = CentavosField(source="custo_unitario", read_only=True)
    variacao_descricao = serializers.CharField(source="variacao.descricao_completa", read_only=True)
    usuario_nome = serializers.CharField(source="usuario.nome", read_only=True, default="")
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    quantidade_com_sinal = serializers.IntegerField(read_only=True)

    class Meta:
        model = MovimentoEstoque
        fields = [
            "id", "variacao", "variacao_descricao", "tipo", "tipo_display",
            "quantidade", "quantidade_com_sinal", "saldo_apos",
            "custo_unitario_centavos", "motivo", "documento",
            "usuario", "usuario_nome", "venda", "compra", "criado_em",
        ]
        read_only_fields = fields


class RegistrarMovimentoSerializer(serializers.Serializer):
    """Entrada manual, perda ou devolução — venda e compra têm fluxo próprio."""

    variacao = serializers.PrimaryKeyRelatedField(queryset=Variacao.objects.all())
    tipo = serializers.ChoiceField(
        choices=[
            TipoMovimento.ENTRADA,
            TipoMovimento.PERDA,
            TipoMovimento.DEVOLUCAO,
        ]
    )
    quantidade = serializers.IntegerField(min_value=1)
    custo_unitario_centavos = serializers.IntegerField(min_value=0, required=False)
    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True)
    documento = serializers.CharField(max_length=60, required=False, allow_blank=True)

    def validate_variacao(self, variacao):
        loja = self.context["request"].loja
        if variacao.loja_id != loja.id:
            raise serializers.ValidationError("A variação informada não é desta loja.")
        return variacao


class AjusteInventarioSerializer(serializers.Serializer):
    """Inventário: informa-se a contagem física, não a diferença."""

    variacao = serializers.PrimaryKeyRelatedField(queryset=Variacao.objects.all())
    contagem = serializers.IntegerField(min_value=0)
    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_variacao(self, variacao):
        loja = self.context["request"].loja
        if variacao.loja_id != loja.id:
            raise serializers.ValidationError("A variação informada não é desta loja.")
        return variacao


class PosicaoEstoqueSerializer(serializers.ModelSerializer):
    """Linha do relatório de posição de estoque."""

    descricao_completa = serializers.CharField(read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    categoria_nome = serializers.CharField(source="produto.categoria.nome",
                                           read_only=True, default="")
    preco_custo_centavos = CentavosField(source="preco_custo", read_only=True)
    preco_venda_centavos = CentavosField(source="preco_venda", read_only=True)
    valor_custo_total_centavos = serializers.SerializerMethodField()
    valor_venda_total_centavos = serializers.SerializerMethodField()
    abaixo_do_minimo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Variacao
        fields = [
            "id", "produto_nome", "categoria_nome", "descricao_completa", "sku",
            "saldo", "estoque_minimo", "abaixo_do_minimo",
            "preco_custo_centavos", "preco_venda_centavos",
            "valor_custo_total_centavos", "valor_venda_total_centavos",
        ]

    def get_valor_custo_total_centavos(self, variacao) -> int:
        from apps.core.utils import para_centavos

        return para_centavos(variacao.preco_custo * max(variacao.saldo, 0))

    def get_valor_venda_total_centavos(self, variacao) -> int:
        from apps.core.utils import para_centavos

        return para_centavos(variacao.preco_venda * max(variacao.saldo, 0))
