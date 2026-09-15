"""Contas a pagar e a receber."""

from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.core.models import LojaModel


class TipoLancamento(models.TextChoices):
    RECEITA = "receita", "Receita"
    DESPESA = "despesa", "Despesa"


class StatusLancamento(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    PAGO = "pago", "Pago / recebido"
    CANCELADO = "cancelado", "Cancelado"


class CategoriaFinanceira(LojaModel):
    nome = models.CharField("nome", max_length=80)
    tipo = models.CharField("tipo", max_length=20, choices=TipoLancamento.choices)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "categoria financeira"
        verbose_name_plural = "categorias financeiras"
        ordering = ["tipo", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["loja", "nome"], name="categoria_financeira_unica_por_loja"
            )
        ]

    def __str__(self):
        return self.nome


class Lancamento(LojaModel):
    """
    Uma conta a pagar ou a receber.

    As vendas e as compras criam lançamentos automaticamente (ver
    `vendas.servicos` e `fornecedores.servicos`); o lojista lança à mão o
    resto — aluguel, energia, retirada.
    """

    tipo = models.CharField("tipo", max_length=20, choices=TipoLancamento.choices)
    categoria = models.ForeignKey(
        CategoriaFinanceira, on_delete=models.PROTECT, related_name="lancamentos",
        verbose_name="categoria", null=True, blank=True,
    )
    descricao = models.CharField("descrição", max_length=200)
    valor = models.DecimalField("valor", max_digits=12, decimal_places=2)

    vencimento = models.DateField("vencimento", db_index=True)
    pago_em = models.DateField("pago/recebido em", null=True, blank=True)
    status = models.CharField(
        "status", max_length=20, choices=StatusLancamento.choices,
        default=StatusLancamento.PENDENTE,
    )
    forma_pagamento = models.CharField("forma de pagamento", max_length=20, blank=True)

    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="lancamentos",
        verbose_name="cliente", null=True, blank=True,
    )
    fornecedor = models.ForeignKey(
        "fornecedores.Fornecedor", on_delete=models.PROTECT, related_name="lancamentos",
        verbose_name="fornecedor", null=True, blank=True,
    )
    venda = models.ForeignKey(
        "vendas.Venda", on_delete=models.PROTECT, related_name="lancamentos",
        null=True, blank=True,
    )
    compra = models.ForeignKey(
        "fornecedores.Compra", on_delete=models.PROTECT, related_name="lancamentos",
        null=True, blank=True,
    )
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        verbose_name = "lançamento"
        verbose_name_plural = "lançamentos"
        ordering = ["vencimento", "-id"]
        indexes = [
            models.Index(fields=["loja", "status", "vencimento"]),
            models.Index(fields=["loja", "tipo", "status"]),
            models.Index(fields=["loja", "pago_em"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.descricao} — R$ {self.valor}"

    @property
    def atrasado(self) -> bool:
        return self.status == StatusLancamento.PENDENTE and self.vencimento < timezone.localdate()

    @property
    def dias_de_atraso(self) -> int:
        if not self.atrasado:
            return 0
        return (timezone.localdate() - self.vencimento).days

    @property
    def valor_com_sinal(self) -> Decimal:
        return self.valor if self.tipo == TipoLancamento.RECEITA else -self.valor
