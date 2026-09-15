"""Campos e serializers compartilhados."""

from rest_framework import serializers

from .utils import de_centavos, para_centavos, validar_cnpj, validar_cpf


class CentavosField(serializers.IntegerField):
    """
    Dinheiro na API: inteiro de centavos; no modelo: Decimal. Ver ADR-0002.

    Usar sempre com `source` apontando para o DecimalField do modelo e nome
    de campo terminado em `_centavos`.
    """

    def to_representation(self, valor):
        return para_centavos(valor)

    def to_internal_value(self, dado):
        centavos = super().to_internal_value(dado)
        return de_centavos(centavos)


class CPFField(serializers.CharField):
    """CPF validado e normalizado para 11 dígitos."""

    def to_internal_value(self, dado):
        texto = super().to_internal_value(dado)
        if not texto:
            return ""
        if not validar_cpf(texto):
            raise serializers.ValidationError("CPF inválido.")
        return "".join(c for c in texto if c.isdigit())


class CNPJField(serializers.CharField):
    """CNPJ validado e normalizado para 14 dígitos."""

    def to_internal_value(self, dado):
        texto = super().to_internal_value(dado)
        if not texto:
            return ""
        if not validar_cnpj(texto):
            raise serializers.ValidationError("CNPJ inválido.")
        return "".join(c for c in texto if c.isdigit())
