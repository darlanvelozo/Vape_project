"""PDV: caixa, venda, itens e pagamentos."""

from decimal import Decimal

from django.db import models

from apps.core.models import LojaModel


class StatusCaixa(models.TextChoices):
    ABERTO = "aberto", "Aberto"
    FECHADO = "fechado", "Fechado"


class Caixa(LojaModel):
    """
    Sessão de caixa: da abertura ao fechamento.

    Toda venda finalizada pertence a um caixa aberto — é o que permite
    conferir, no fim do dia, o dinheiro da gaveta contra o que o sistema
    registrou.
    """

    usuario_abertura = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT,
        related_name="caixas_abertos", verbose_name="aberto por",
    )
    aberto_em = models.DateTimeField("aberto em", auto_now_add=True)
    saldo_inicial = models.DecimalField(
        "saldo inicial (troco)", max_digits=12, decimal_places=2, default=Decimal("0.00")
    )

    usuario_fechamento = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT,
        related_name="caixas_fechados", verbose_name="fechado por",
        null=True, blank=True,
    )
    fechado_em = models.DateTimeField("fechado em", null=True, blank=True)
    saldo_informado = models.DecimalField(
        "dinheiro conferido na gaveta", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    saldo_calculado = models.DecimalField(
        "saldo calculado pelo sistema", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    diferenca = models.DecimalField(
        "diferença (sobra/falta)", max_digits=12, decimal_places=2, null=True, blank=True
    )

    status = models.CharField(
        "status", max_length=20, choices=StatusCaixa.choices, default=StatusCaixa.ABERTO
    )
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        verbose_name = "caixa"
        verbose_name_plural = "caixas"
        ordering = ["-aberto_em"]
        constraints = [
            # Uma loja só pode ter um caixa aberto por vez: com dois, não há
            # como saber em qual a venda deveria entrar.
            models.UniqueConstraint(
                fields=["loja"],
                condition=models.Q(status="aberto"),
                name="um_caixa_aberto_por_loja",
            ),
        ]
        indexes = [models.Index(fields=["loja", "status"])]

    def __str__(self):
        return f"Caixa #{self.pk} — {self.get_status_display()}"

    @property
    def aberto(self) -> bool:
        return self.status == StatusCaixa.ABERTO


class TipoMovimentoCaixa(models.TextChoices):
    SUPRIMENTO = "suprimento", "Suprimento (entrada de troco)"
    SANGRIA = "sangria", "Sangria (retirada)"
    VENDA = "venda", "Venda em dinheiro"
    ESTORNO = "estorno", "Estorno de venda"


class MovimentoCaixa(LojaModel):
    """
    Movimento de **dinheiro físico** na gaveta.

    Pix e cartão não geram movimento de caixa: entram no financeiro, não na
    gaveta. Só dinheiro afeta a conferência do fechamento.
    """

    caixa = models.ForeignKey(
        Caixa, on_delete=models.PROTECT, related_name="movimentos", verbose_name="caixa"
    )
    tipo = models.CharField("tipo", max_length=20, choices=TipoMovimentoCaixa.choices)
    valor = models.DecimalField("valor", max_digits=12, decimal_places=2)
    descricao = models.CharField("descrição", max_length=200, blank=True)
    usuario = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT,
        related_name="movimentos_caixa", verbose_name="usuário",
    )
    venda = models.ForeignKey(
        "vendas.Venda", on_delete=models.PROTECT, related_name="movimentos_caixa",
        null=True, blank=True,
    )

    class Meta:
        verbose_name = "movimento de caixa"
        verbose_name_plural = "movimentos de caixa"
        ordering = ["-criado_em", "-id"]
        indexes = [models.Index(fields=["caixa", "-criado_em"])]

    def __str__(self):
        return f"{self.get_tipo_display()} — R$ {self.valor}"

    @property
    def valor_com_sinal(self) -> Decimal:
        """Sangria e estorno tiram dinheiro da gaveta."""
        if self.tipo in (TipoMovimentoCaixa.SANGRIA, TipoMovimentoCaixa.ESTORNO):
            return -self.valor
        return self.valor


class StatusVenda(models.TextChoices):
    ABERTA = "aberta", "Aberta"
    FINALIZADA = "finalizada", "Finalizada"
    CANCELADA = "cancelada", "Cancelada"


class FormaPagamento(models.TextChoices):
    DINHEIRO = "dinheiro", "Dinheiro"
    PIX = "pix", "Pix"
    DEBITO = "debito", "Cartão de débito"
    CREDITO = "credito", "Cartão de crédito"
    FIADO = "fiado", "Fiado (a receber)"


class Venda(LojaModel):
    """
    Venda de balcão.

    `numero` é sequencial **por loja** — o lojista se refere à "venda 42",
    não ao id global do banco.
    """

    numero = models.PositiveIntegerField("número")
    caixa = models.ForeignKey(
        Caixa, on_delete=models.PROTECT, related_name="vendas",
        verbose_name="caixa", null=True, blank=True,
    )
    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, related_name="vendas",
        verbose_name="cliente", null=True, blank=True,
    )
    usuario = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, related_name="vendas",
        verbose_name="vendedor",
    )

    status = models.CharField(
        "status", max_length=20, choices=StatusVenda.choices, default=StatusVenda.ABERTA
    )
    subtotal = models.DecimalField("subtotal", max_digits=12, decimal_places=2,
                                   default=Decimal("0.00"))
    desconto = models.DecimalField("desconto", max_digits=12, decimal_places=2,
                                   default=Decimal("0.00"))
    total = models.DecimalField("total", max_digits=12, decimal_places=2,
                                default=Decimal("0.00"))
    custo_total = models.DecimalField(
        "custo total (snapshot)", max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="Soma do custo dos itens no momento da venda — base da margem.",
    )

    observacoes = models.TextField("observações", blank=True)
    finalizada_em = models.DateTimeField("finalizada em", null=True, blank=True)
    cancelada_em = models.DateTimeField("cancelada em", null=True, blank=True)
    motivo_cancelamento = models.CharField("motivo do cancelamento", max_length=200, blank=True)

    class Meta:
        verbose_name = "venda"
        verbose_name_plural = "vendas"
        ordering = ["-criado_em", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["loja", "numero"], name="numero_venda_unico_por_loja")
        ]
        indexes = [
            models.Index(fields=["loja", "-criado_em"]),
            models.Index(fields=["loja", "status"]),
            models.Index(fields=["loja", "-finalizada_em"]),
        ]

    def __str__(self):
        return f"Venda #{self.numero}"

    @property
    def lucro(self) -> Decimal:
        return self.total - self.custo_total

    @property
    def total_pago(self) -> Decimal:
        return sum((p.valor for p in self.pagamentos.all()), Decimal("0.00"))


class ItemVenda(models.Model):
    """
    Item da venda com **snapshot** de descrição, preço e custo.

    Sem o snapshot, mudar o preço de um produto reescreveria o histórico e a
    margem de vendas passadas.
    """

    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens")
    variacao = models.ForeignKey(
        "produtos.Variacao", on_delete=models.PROTECT,
        related_name="itens_venda", verbose_name="variação",
    )
    descricao = models.CharField("descrição no momento da venda", max_length=240)
    quantidade = models.PositiveIntegerField("quantidade")
    preco_unitario = models.DecimalField("preço unitário", max_digits=12, decimal_places=2)
    desconto = models.DecimalField("desconto do item", max_digits=12, decimal_places=2,
                                   default=Decimal("0.00"))
    custo_unitario = models.DecimalField("custo unitário", max_digits=12, decimal_places=2,
                                         default=Decimal("0.00"))

    class Meta:
        verbose_name = "item da venda"
        verbose_name_plural = "itens da venda"
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantidade}× {self.descricao}"

    @property
    def total(self) -> Decimal:
        return max(self.quantidade * self.preco_unitario - self.desconto, Decimal("0.00"))

    @property
    def custo_total(self) -> Decimal:
        return self.quantidade * self.custo_unitario


class Pagamento(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="pagamentos")
    forma = models.CharField("forma", max_length=20, choices=FormaPagamento.choices)
    valor = models.DecimalField("valor", max_digits=12, decimal_places=2)
    troco = models.DecimalField("troco", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    observacao = models.CharField("observação", max_length=140, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "pagamento"
        verbose_name_plural = "pagamentos"
        ordering = ["id"]

    def __str__(self):
        return f"{self.get_forma_display()} — R$ {self.valor}"
