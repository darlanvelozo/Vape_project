"""Auxiliares de construção de dados para os testes."""

from decimal import Decimal

from apps.produtos.models import Produto, Variacao


def criar_variacao_zerada(loja, nome="Produto Novo"):
    produto = Produto.objects.create(loja=loja, nome=nome)
    return Variacao.objects.create(
        loja=loja, produto=produto, sabor="Único",
        preco_venda=Decimal("40.00"), preco_custo=Decimal("0.00"), saldo=0,
    )
