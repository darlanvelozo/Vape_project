from datetime import date

from django.conf import settings
from rest_framework import serializers

from apps.core.serializers import CentavosField, CPFField
from apps.core.utils import calcular_idade

from .models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    cpf = CPFField(required=False, allow_blank=True, max_length=14)
    limite_credito_centavos = CentavosField(source="limite_credito", required=False, min_value=0)
    saldo_devedor_centavos = CentavosField(source="saldo_devedor", read_only=True)
    credito_disponivel_centavos = CentavosField(source="credito_disponivel", read_only=True)
    idade = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id", "nome", "telefone", "email", "cpf", "data_nascimento", "idade",
            "endereco", "cidade", "observacoes",
            "limite_credito_centavos", "saldo_devedor_centavos",
            "credito_disponivel_centavos", "ativo", "criado_em",
        ]
        read_only_fields = ["id", "criado_em"]

    def validate_data_nascimento(self, valor):
        if valor is None:
            return valor
        if valor > date.today():
            raise serializers.ValidationError("A data de nascimento não pode ser futura.")
        idade = calcular_idade(valor)
        if idade > 120:
            raise serializers.ValidationError("Data de nascimento improvável.")
        minima = getattr(settings, "IDADE_MINIMA_COMPRA", 18)
        if minima and idade < minima:
            raise serializers.ValidationError(
                f"Cliente menor de {minima} anos não pode ser cadastrado para compra."
            )
        return valor


class ClienteResumoSerializer(serializers.ModelSerializer):
    """Versão enxuta para o autocomplete do PDV."""

    credito_disponivel_centavos = CentavosField(source="credito_disponivel", read_only=True)

    class Meta:
        model = Cliente
        fields = ["id", "nome", "telefone", "cpf", "credito_disponivel_centavos", "ativo"]
