"""Conversões de dinheiro e validadores — a base de tudo (ADR-0002)."""

from datetime import date
from decimal import Decimal

import pytest

from apps.core.utils import (
    calcular_idade,
    de_centavos,
    para_centavos,
    quantizar,
    validar_cnpj,
    validar_cpf,
)


class TestDinheiro:
    def test_converte_decimal_para_centavos(self):
        assert para_centavos(Decimal("12.34")) == 1234
        assert para_centavos(Decimal("0.01")) == 1
        assert para_centavos(Decimal("0.00")) == 0
        assert para_centavos(None) == 0

    def test_converte_centavos_para_decimal(self):
        assert de_centavos(1234) == Decimal("12.34")
        assert de_centavos(0) == Decimal("0.00")

    def test_ida_e_volta_preserva_o_valor(self):
        for valor in ["0.01", "1.00", "19.99", "1234.56", "99999.99"]:
            assert de_centavos(para_centavos(Decimal(valor))) == Decimal(valor)

    def test_arredondamento_comercial_e_para_cima(self):
        # ROUND_HALF_EVEN (padrão do Python) devolveria 0.12 — indefensável no balcão.
        assert quantizar(Decimal("0.125")) == Decimal("0.13")
        assert quantizar(Decimal("0.135")) == Decimal("0.14")

    def test_nao_usa_float_na_soma_de_precos(self):
        total = sum(Decimal("0.10") for _ in range(3))
        assert total == Decimal("0.30")
        assert para_centavos(total) == 30


class TestIdade:
    def test_calcula_idade_em_anos_completos(self):
        assert calcular_idade(date(2000, 1, 1), date(2026, 1, 1)) == 26
        assert calcular_idade(date(2000, 6, 15), date(2026, 6, 14)) == 25
        assert calcular_idade(date(2000, 6, 15), date(2026, 6, 15)) == 26


class TestDocumentos:
    @pytest.mark.parametrize("cpf", ["529.982.247-25", "52998224725"])
    def test_aceita_cpf_valido(self, cpf):
        assert validar_cpf(cpf)

    @pytest.mark.parametrize("cpf", ["111.111.111-11", "12345678900", "", "123"])
    def test_recusa_cpf_invalido(self, cpf):
        assert not validar_cpf(cpf)

    def test_aceita_cnpj_valido(self):
        assert validar_cnpj("11.222.333/0001-81")

    @pytest.mark.parametrize("cnpj", ["11.111.111/1111-11", "12345678000100", ""])
    def test_recusa_cnpj_invalido(self, cnpj):
        assert not validar_cnpj(cnpj)
