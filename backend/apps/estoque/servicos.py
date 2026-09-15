"""
Serviços de estoque.

**Única porta de escrita do saldo.** Nenhuma view, serializer ou signal
altera `Variacao.saldo` diretamente: tudo passa por `registrar_movimento`,
que trava a linha da variação (`select_for_update`) antes de ler o saldo.
Sem essa trava, duas vendas simultâneas da última unidade leriam saldo 1 e
gravariam 0 as duas — vendendo o que não existe.
"""

from decimal import Decimal

from django.db import transaction

from apps.core.exceptions import ErroDeNegocio, EstoqueInsuficiente
from apps.produtos.models import Variacao

from .models import MOVIMENTOS_DE_ENTRADA, MovimentoEstoque, TipoMovimento


@transaction.atomic
def registrar_movimento(
    *,
    variacao,
    tipo: str,
    quantidade: int,
    usuario=None,
    custo_unitario: Decimal | None = None,
    motivo: str = "",
    documento: str = "",
    venda=None,
    compra=None,
    permitir_negativo: bool = False,
) -> MovimentoEstoque:
    """
    Registra um movimento e atualiza o saldo da variação atomicamente.

    `permitir_negativo` existe para a loja que trabalha com pré-venda
    (`ConfiguracaoLoja.permitir_venda_sem_estoque`); o padrão é recusar.
    """
    if quantidade <= 0:
        raise ErroDeNegocio("A quantidade do movimento deve ser maior que zero.",
                            campo="quantidade")

    # Trava a variação até o fim da transação: serializa movimentos concorrentes.
    variacao_travada = Variacao.objects.select_for_update().get(pk=variacao.pk)

    eh_entrada = tipo in MOVIMENTOS_DE_ENTRADA
    delta = quantidade if eh_entrada else -quantidade
    saldo_novo = variacao_travada.saldo + delta

    if saldo_novo < 0 and not permitir_negativo:
        raise EstoqueInsuficiente(
            f"Estoque insuficiente de “{variacao_travada.descricao_completa}”: "
            f"saldo {variacao_travada.saldo}, saída de {quantidade}.",
            campo="quantidade",
        )

    movimento = MovimentoEstoque.objects.create(
        loja=variacao_travada.loja,
        variacao=variacao_travada,
        tipo=tipo,
        quantidade=quantidade,
        saldo_apos=saldo_novo,
        custo_unitario=(
            custo_unitario if custo_unitario is not None else variacao_travada.preco_custo
        ),
        motivo=motivo,
        documento=documento,
        usuario=usuario,
        venda=venda,
        compra=compra,
    )

    variacao_travada.saldo = saldo_novo
    variacao_travada.save(update_fields=["saldo", "atualizado_em"])
    # Mantém em sincronia o objeto que o chamador já tinha em mãos.
    variacao.saldo = saldo_novo

    return movimento


@transaction.atomic
def ajustar_para_contagem(*, variacao, contagem: int, usuario=None, motivo: str = ""):
    """
    Ajuste de inventário: informa-se o que **foi contado**, não a diferença.

    É assim que o inventário acontece na prática — o operador conta 7 e digita
    7. Devolve None quando não há divergência (nada a registrar).
    """
    if contagem < 0:
        raise ErroDeNegocio("A contagem não pode ser negativa.", campo="contagem")

    variacao_travada = Variacao.objects.select_for_update().get(pk=variacao.pk)
    diferenca = contagem - variacao_travada.saldo
    if diferenca == 0:
        return None

    movimento = MovimentoEstoque.objects.create(
        loja=variacao_travada.loja,
        variacao=variacao_travada,
        tipo=TipoMovimento.AJUSTE,
        quantidade=abs(diferenca),
        saldo_apos=contagem,
        custo_unitario=variacao_travada.preco_custo,
        motivo=motivo or f"Inventário: saldo {variacao_travada.saldo} → {contagem}",
        usuario=usuario,
    )
    variacao_travada.saldo = contagem
    variacao_travada.save(update_fields=["saldo", "atualizado_em"])
    variacao.saldo = contagem
    return movimento


def atualizar_custo_medio(*, variacao, quantidade_entrada: int, custo_unitario: Decimal):
    """
    Custo médio ponderado após uma entrada.

    Com saldo anterior negativo ou zero, o custo novo simplesmente substitui o
    antigo — média ponderada com peso negativo não tem sentido econômico.
    """
    saldo_anterior = max(variacao.saldo - quantidade_entrada, 0)
    if saldo_anterior <= 0:
        novo_custo = custo_unitario
    else:
        total_anterior = variacao.preco_custo * saldo_anterior
        total_entrada = custo_unitario * quantidade_entrada
        novo_custo = (total_anterior + total_entrada) / (saldo_anterior + quantidade_entrada)

    variacao.preco_custo = novo_custo.quantize(Decimal("0.01"))
    variacao.save(update_fields=["preco_custo", "atualizado_em"])
    return variacao.preco_custo
