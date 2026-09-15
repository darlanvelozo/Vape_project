"""Recebimento e cancelamento de compra."""

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import ErroDeNegocio
from apps.estoque.models import TipoMovimento
from apps.estoque.servicos import atualizar_custo_medio, registrar_movimento

from .models import Compra, StatusCompra


@transaction.atomic
def receber_compra(*, compra: Compra, usuario=None) -> Compra:
    """
    Dá entrada no estoque de todos os itens e fecha a compra.

    Gera também a conta a pagar quando a compra tem vencimento — assim o
    financeiro não depende de o lojista lembrar de lançar a nota.
    """
    compra = Compra.objects.select_for_update().get(pk=compra.pk)

    if compra.status != StatusCompra.RASCUNHO:
        raise ErroDeNegocio(
            f"Só é possível receber compra em rascunho (status atual: "
            f"{compra.get_status_display()}).",
            campo="status",
        )

    itens = list(compra.itens.select_related("variacao").all())
    if not itens:
        raise ErroDeNegocio("A compra não tem itens.", campo="itens")

    for item in itens:
        registrar_movimento(
            variacao=item.variacao,
            tipo=TipoMovimento.ENTRADA,
            quantidade=item.quantidade,
            usuario=usuario,
            custo_unitario=item.custo_unitario,
            motivo=f"Compra #{compra.pk} — {compra.fornecedor.nome}",
            documento=compra.numero_documento,
            compra=compra,
        )
        atualizar_custo_medio(
            variacao=item.variacao,
            quantidade_entrada=item.quantidade,
            custo_unitario=item.custo_unitario,
        )

    compra.total = compra.calcular_total()
    compra.status = StatusCompra.RECEBIDA
    compra.recebida_em = timezone.now()
    compra.usuario = usuario or compra.usuario
    compra.save(update_fields=["total", "status", "recebida_em", "usuario", "atualizado_em"])

    _lancar_no_financeiro(compra)

    return compra


def _lancar_no_financeiro(compra: Compra):
    """
    Toda compra recebida vira despesa — com ou sem prazo.

    Antes, só compra com vencimento gerava lançamento, e a compra à vista
    sumia do financeiro: o relatório mostrava a receita das vendas sem o
    dinheiro que saiu para comprar a mercadoria, sugerindo um lucro que não
    existe. O prazo muda apenas o status:

    - **com vencimento** → conta a pagar pendente;
    - **sem vencimento** → pagamento à vista, já baixado na data da compra.
    """
    from apps.financeiro.models import (
        CategoriaFinanceira,
        Lancamento,
        StatusLancamento,
        TipoLancamento,
    )

    if compra.total <= 0:
        return None

    categoria, _ = CategoriaFinanceira.objects.get_or_create(
        loja=compra.loja,
        nome="Compra de mercadoria",
        defaults={"tipo": TipoLancamento.DESPESA},
    )

    a_prazo = bool(compra.vencimento)
    return Lancamento.objects.create(
        loja=compra.loja,
        tipo=TipoLancamento.DESPESA,
        categoria=categoria,
        descricao=f"Compra #{compra.pk} — {compra.fornecedor.nome}",
        valor=compra.total,
        vencimento=compra.vencimento or compra.data,
        pago_em=None if a_prazo else compra.data,
        status=StatusLancamento.PENDENTE if a_prazo else StatusLancamento.PAGO,
        fornecedor=compra.fornecedor,
        compra=compra,
    )


@transaction.atomic
def cancelar_compra(*, compra: Compra, usuario=None, motivo: str = "") -> Compra:
    """
    Cancela a compra; se já recebida, estorna o estoque.

    O estorno usa PERDA (saída) e não um tipo próprio de "estorno de entrada"
    para manter o extrato legível: o que importa é que saiu, e o motivo diz
    por quê.
    """
    compra = Compra.objects.select_for_update().get(pk=compra.pk)

    if compra.status == StatusCompra.CANCELADA:
        raise ErroDeNegocio("Esta compra já está cancelada.", campo="status")

    if compra.status == StatusCompra.RECEBIDA:
        for item in compra.itens.select_related("variacao").all():
            registrar_movimento(
                variacao=item.variacao,
                tipo=TipoMovimento.PERDA,
                quantidade=item.quantidade,
                usuario=usuario,
                custo_unitario=item.custo_unitario,
                motivo=f"Cancelamento da compra #{compra.pk}. {motivo}".strip(),
                documento=compra.numero_documento,
                compra=compra,
                # O estoque pode já ter sido vendido; o estorno não deve travar.
                permitir_negativo=True,
            )

        from apps.financeiro.models import Lancamento, StatusLancamento

        # Inclui a despesa já baixada (compra à vista), senão o cancelamento
        # devolveria a mercadoria mas deixaria a saída no financeiro.
        Lancamento.objects.filter(compra=compra).exclude(
            status=StatusLancamento.CANCELADO
        ).update(status=StatusLancamento.CANCELADO, pago_em=None)

    compra.status = StatusCompra.CANCELADA
    compra.observacoes = f"{compra.observacoes}\n[Cancelada] {motivo}".strip()
    compra.save(update_fields=["status", "observacoes", "atualizado_em"])
    return compra
