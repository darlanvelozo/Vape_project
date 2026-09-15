"""Clientes da loja."""

from decimal import Decimal

from django.db import models

from apps.core.models import LojaModel
from apps.core.utils import calcular_idade


class Cliente(LojaModel):
    """
    Cliente do balcão.

    `data_nascimento` não é decoração: a venda para menor de idade é bloqueada
    quando o cliente é identificado (ADR-0003). Cliente sem data cadastrada
    não bloqueia — a venda anônima de balcão continua possível.
    """

    nome = models.CharField("nome", max_length=140)
    telefone = models.CharField("telefone", max_length=20, blank=True, db_index=True)
    email = models.EmailField("e-mail", blank=True)
    cpf = models.CharField("CPF", max_length=11, blank=True)
    data_nascimento = models.DateField("data de nascimento", null=True, blank=True)

    endereco = models.CharField("endereço", max_length=200, blank=True)
    cidade = models.CharField("cidade", max_length=80, blank=True)
    observacoes = models.TextField("observações", blank=True)

    limite_credito = models.DecimalField(
        "limite de crédito (fiado)", max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="Zero desativa a venda fiada para este cliente.",
    )
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["loja", "cpf"], condition=~models.Q(cpf=""),
                name="cpf_unico_por_loja",
            ),
        ]
        indexes = [
            models.Index(fields=["loja", "ativo"]),
            models.Index(fields=["loja", "nome"]),
        ]

    def __str__(self):
        return self.nome

    @property
    def idade(self) -> int | None:
        if not self.data_nascimento:
            return None
        return calcular_idade(self.data_nascimento)

    @property
    def saldo_devedor(self) -> Decimal:
        """Total em aberto no fiado (lançamentos de receita pendentes)."""
        from apps.financeiro.models import Lancamento, StatusLancamento, TipoLancamento

        total = Lancamento.objects.filter(
            cliente=self,
            tipo=TipoLancamento.RECEITA,
            status=StatusLancamento.PENDENTE,
        ).aggregate(total=models.Sum("valor"))["total"]
        return total or Decimal("0.00")

    @property
    def credito_disponivel(self) -> Decimal:
        return max(self.limite_credito - self.saldo_devedor, Decimal("0.00"))
