from django.utils import timezone
from rest_framework import serializers

from apps.core.serializers import CentavosField

from .models import CategoriaFinanceira, Lancamento


class CategoriaFinanceiraSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaFinanceira
        fields = ["id", "nome", "tipo", "ativo"]


class LancamentoSerializer(serializers.ModelSerializer):
    valor_centavos = CentavosField(source="valor", min_value=1)
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True, default="")
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True, default="")
    fornecedor_nome = serializers.CharField(source="fornecedor.nome", read_only=True, default="")
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    atrasado = serializers.BooleanField(read_only=True)
    dias_de_atraso = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lancamento
        fields = [
            "id", "tipo", "tipo_display", "categoria", "categoria_nome",
            "descricao", "valor_centavos", "vencimento", "pago_em",
            "status", "status_display", "forma_pagamento",
            "cliente", "cliente_nome", "fornecedor", "fornecedor_nome",
            "venda", "compra", "observacoes",
            "atrasado", "dias_de_atraso", "criado_em",
        ]
        # Origem automática (venda/compra) não é editável pela API.
        read_only_fields = ["id", "venda", "compra", "criado_em", "status"]

    def validate(self, dados):
        categoria = dados.get("categoria") or getattr(self.instance, "categoria", None)
        tipo = dados.get("tipo") or getattr(self.instance, "tipo", None)
        if categoria is not None:
            loja = self.context["request"].loja
            if categoria.loja_id != loja.id:
                raise serializers.ValidationError(
                    {"categoria": "A categoria informada não é desta loja."}
                )
            if tipo and categoria.tipo != tipo:
                raise serializers.ValidationError({
                    "categoria": f"A categoria “{categoria.nome}” é de "
                                 f"{categoria.get_tipo_display().lower()}."
                })
        return dados


class BaixarLancamentoSerializer(serializers.Serializer):
    """Dar baixa = marcar como pago/recebido."""

    pago_em = serializers.DateField(required=False)
    forma_pagamento = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_pago_em(self, valor):
        if valor and valor > timezone.localdate():
            raise serializers.ValidationError("A data de pagamento não pode ser futura.")
        return valor
