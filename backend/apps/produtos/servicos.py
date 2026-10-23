"""
Serviços do catálogo.

Em loja de vape o preço é do modelo, não do sabor: o Ignite V55 custa o mesmo
em qualquer sabor. Guardar o preço em cada variação continua necessário —
é o que o PDV lê e o que permite uma exceção pontual —, mas a alteração do
dia a dia é "o V55 passou a R$ 100", e fazer isso sabor a sabor é onde o
lojista erra e esquece um.
"""

from decimal import Decimal

from django.db import transaction

from apps.core.exceptions import ErroDeNegocio

from .models import Produto, Variacao


@transaction.atomic
def aplicar_precos_ao_modelo(
    *, produto: Produto, preco_custo: Decimal | None = None,
    preco_venda: Decimal | None = None,
) -> int:
    """
    Iguala custo e/ou preço de venda em todas as variações do produto.

    Inclui as inativas: sabor que volta à prateleira volta com o preço atual
    do modelo, não com o de meses atrás. Salva uma a uma — e só os campos de
    preço — para o histórico de auditoria registrar cada mudança sem tocar no
    saldo, que só `apps.estoque.servicos` escreve.

    Vendas já feitas não mudam: o custo fica congelado no item da venda.
    Devolve quantas variações tiveram algum valor alterado.
    """
    if preco_custo is None and preco_venda is None:
        raise ErroDeNegocio("Informe o preço de custo, o de venda ou os dois.")

    alteradas = 0
    for variacao in Variacao.objects.select_for_update().filter(produto=produto):
        campos = []
        if preco_custo is not None and variacao.preco_custo != preco_custo:
            variacao.preco_custo = preco_custo
            campos.append("preco_custo")
        if preco_venda is not None and variacao.preco_venda != preco_venda:
            variacao.preco_venda = preco_venda
            campos.append("preco_venda")
        if campos:
            variacao.save(update_fields=[*campos, "atualizado_em"])
            alteradas += 1
    return alteradas
