"""Fixtures compartilhadas pelos testes."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.clientes.models import Cliente
from apps.lojas.models import ConfiguracaoLoja, Loja
from apps.produtos.models import Categoria, Produto, Variacao
from apps.usuarios.models import Papel, Usuario


@pytest.fixture
def api():
    return APIClient()


def criar_loja(nome="Loja Teste"):
    loja = Loja.objects.create(nome=nome)
    ConfiguracaoLoja.objects.create(loja=loja)
    return loja


def criar_usuario(loja, email="dono@teste.com", papel=Papel.DONO, nome="Dono"):
    return Usuario.objects.create_user(
        email=email, password="SenhaForte123", nome=nome, loja=loja, papel=papel
    )


def criar_variacao(loja, nome="Elf Bar 10000", sabor="Blue Razz",
                   venda="50.00", custo="30.00", saldo=0):
    produto = Produto.objects.create(loja=loja, nome=nome)
    variacao = Variacao.objects.create(
        loja=loja, produto=produto, sabor=sabor,
        preco_venda=Decimal(venda), preco_custo=Decimal(custo), saldo=saldo,
    )
    return variacao


@pytest.fixture
def loja(db):
    return criar_loja("Vape Store A")


@pytest.fixture
def outra_loja(db):
    return criar_loja("Vape Store B")


@pytest.fixture
def dono(loja):
    return criar_usuario(loja, "dono@a.com", Papel.DONO, "Dono A")


@pytest.fixture
def gerente(loja):
    return criar_usuario(loja, "gerente@a.com", Papel.GERENTE, "Gerente A")


@pytest.fixture
def vendedor(loja):
    return criar_usuario(loja, "vendedor@a.com", Papel.VENDEDOR, "Vendedor A")


@pytest.fixture
def dono_outra(outra_loja):
    return criar_usuario(outra_loja, "dono@b.com", Papel.DONO, "Dono B")


@pytest.fixture
def variacao(loja):
    return criar_variacao(loja, saldo=10)


@pytest.fixture
def categoria(loja):
    return Categoria.objects.create(loja=loja, nome="Descartáveis")


@pytest.fixture
def cliente(loja):
    return Cliente.objects.create(
        loja=loja,
        nome="João da Silva",
        telefone="11999990000",
        data_nascimento=date.today() - timedelta(days=365 * 30),
        limite_credito=Decimal("200.00"),
    )


@pytest.fixture
def api_dono(api, dono):
    api.force_authenticate(user=dono)
    return api


@pytest.fixture
def api_vendedor(api, vendedor):
    api.force_authenticate(user=vendedor)
    return api


@pytest.fixture
def api_outra_loja(dono_outra):
    cliente = APIClient()
    cliente.force_authenticate(user=dono_outra)
    return cliente
