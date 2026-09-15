"""Fornecedores e compras (entrada de mercadoria)."""

from decimal import Decimal

from django.db import models

from apps.core.models import LojaModel


class Fornecedor(LojaModel):
    nome = models.CharField("nome", max_length=140)
    cnpj = models.CharField("CNPJ", max_length=14, blank=True)
    contato = models.CharField("pessoa de contato", max_length=120, blank=True)
    telefone = models.CharField("telefone", max_length=20, blank=True)
    email = models.EmailField("e-mail", blank=True)
    endereco = models.CharField("endereço", max_length=200, blank=True)
    cidade = models.CharField("cidade", max_length=80, blank=True)
    observacoes = models.TextField("observações", blank=True)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "fornecedor"
        verbose_name_plural = "fornecedores"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["loja", "cnpj"], condition=~models.Q(cnpj=""),
                name="cnpj_fornecedor_unico_por_loja",
            ),
        ]

    def __str__(self):
        return self.nome


class StatusCompra(models.TextChoices):
    RASCUNHO = "rascunho", "Rascunho"
    RECEBIDA = "recebida", "Recebida"
    CANCELADA = "cancelada", "Cancelada"


class Compra(LojaModel):
    """
    Pedido de compra ao fornecedor.

    Enquanto é **rascunho** nada acontece no estoque; ao ser **recebida**, o
    serviço gera as entradas, atualiza o custo médio e — se houver vencimento —
    cria a conta a pagar. Esse é o único caminho de entrada por compra.
    """

    fornecedor = models.ForeignKey(
        Fornecedor, on_delete=models.PROTECT, related_name="compras", verbose_name="fornecedor"
    )
    numero_documento = models.CharField("nota / documento", max_length=60, blank=True)
    data = models.DateField("data da compra")
    status = models.CharField(
        "status", max_length=20, choices=StatusCompra.choices, default=StatusCompra.RASCUNHO
    )

    frete = models.DecimalField("frete", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    desconto = models.DecimalField("desconto", max_digits=12, decimal_places=2,
                                   default=Decimal("0.00"))
    total = models.DecimalField("total", max_digits=12, decimal_places=2, default=Decimal("0.00"))

    vencimento = models.DateField(
        "vencimento", null=True, blank=True,
        help_text="Preenchido gera automaticamente uma conta a pagar ao receber.",
    )
    observacoes = models.TextField("observações", blank=True)

    usuario = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, related_name="compras",
        verbose_name="usuário", null=True, blank=True,
    )
    recebida_em = models.DateTimeField("recebida em", null=True, blank=True)

    class Meta:
        verbose_name = "compra"
        verbose_name_plural = "compras"
        ordering = ["-data", "-id"]
        indexes = [
            models.Index(fields=["loja", "-data"]),
            models.Index(fields=["loja", "status"]),
        ]

    def __str__(self):
        return f"Compra #{self.pk} — {self.fornecedor}"

    def calcular_total(self) -> Decimal:
        """Soma dos itens + frete − desconto."""
        subtotal = sum(
            (item.quantidade * item.custo_unitario for item in self.itens.all()),
            Decimal("0.00"),
        )
        return max(subtotal + self.frete - self.desconto, Decimal("0.00"))

    @property
    def editavel(self) -> bool:
        return self.status == StatusCompra.RASCUNHO


class ItemCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="itens")
    variacao = models.ForeignKey(
        "produtos.Variacao", on_delete=models.PROTECT,
        related_name="itens_compra", verbose_name="variação",
    )
    quantidade = models.PositiveIntegerField("quantidade")
    custo_unitario = models.DecimalField("custo unitário", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "item da compra"
        verbose_name_plural = "itens da compra"
        constraints = [
            models.UniqueConstraint(fields=["compra", "variacao"], name="item_unico_por_compra")
        ]

    def __str__(self):
        return f"{self.quantidade}× {self.variacao}"

    @property
    def total(self) -> Decimal:
        return self.quantidade * self.custo_unitario
