"""Utilitários de domínio."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

DOIS_DIGITOS = Decimal("0.01")


def quantizar(valor) -> Decimal:
    """
    Arredonda para duas casas com ROUND_HALF_UP (arredondamento comercial).

    O padrão do Python é ROUND_HALF_EVEN, que arredonda 0.125 para 0.12 —
    contraintuitivo no balcão. Todo dinheiro passa por aqui. Ver ADR-0002.
    """
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    return valor.quantize(DOIS_DIGITOS, rounding=ROUND_HALF_UP)


def para_centavos(valor) -> int:
    """Decimal('12.34') -> 1234."""
    if valor is None:
        return 0
    return int(quantizar(valor) * 100)


def de_centavos(centavos) -> Decimal:
    """1234 -> Decimal('12.34')."""
    if centavos is None:
        return Decimal("0.00")
    return quantizar(Decimal(int(centavos)) / 100)


def calcular_idade(nascimento: date, hoje: date | None = None) -> int:
    """Idade em anos completos."""
    hoje = hoje or date.today()
    anos = hoje.year - nascimento.year
    if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
        anos -= 1
    return anos


def apenas_digitos(texto: str | None) -> str:
    return "".join(c for c in (texto or "") if c.isdigit())


def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelos dois dígitos verificadores."""
    numeros = apenas_digitos(cpf)
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(numeros[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if digito != int(numeros[tamanho]):
            return False
    return True


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ pelos dois dígitos verificadores."""
    numeros = apenas_digitos(cnpj)
    if len(numeros) != 14 or numeros == numeros[0] * 14:
        return False
    for tamanho in (12, 13):
        # Pesos oficiais: 5,4,3,2,9,8,7,6,5,4,3,2 (e 6,5,... para o 2º dígito).
        pesos = list(range(tamanho - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(numeros[i]) * pesos[i] for i in range(tamanho))
        resto = soma % 11
        digito = 0 if resto < 2 else 11 - resto
        if digito != int(numeros[tamanho]):
            return False
    return True
