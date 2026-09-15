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

    if compra.vencimento:
        _criar_conta_a_pagar(compra)

    return compra


def _criar_conta_a_pagar(compra: Compra):
    from apps.financeiro.models import (
        CategoriaFinanceira,
        Lancamento,
        StatusLancamento,
        TipoLancamento,
    )

    categoria, _ = CategoriaFinanceira.objects.get_or_create(
        loja=compra.loja,
        nome="Compra de mercadoria",
        defaults={"tipo": TipoLancamento.DESPESA},
    )
    Lancamento.objects.create(
        loja=compra.loja,
        tipo=TipoLancamento.DESPESA,
        categoria=categoria,
        descricao=f"Compra #{compra.pk} — {compra.fornecedor.nome}",
        valor=compra.total,
        vencimento=compra.vencimento,
        status=StatusLancamento.PENDENTE,
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

        Lancamento.objects.filter(compra=compra, status=StatusLancamento.PENDENTE).update(
            status=StatusLancamento.CANCELADO
        )

    compra.status = StatusCompra.CANCELADA
    compra.observacoes = f"{compra.observacoes}\n[Cancelada] {motivo}".strip()
    compra.save(update_fields=["status", "observacoes", "atualizado_em"])
    return compra
