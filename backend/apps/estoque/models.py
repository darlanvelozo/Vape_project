"""Movimentação de estoque — livro-razão do saldo de cada variação."""

from decimal import Decimal

from django.db import models

from apps.core.models import LojaModel


class TipoMovimento(models.TextChoices):
    ENTRADA = "entrada", "Entrada (compra)"
    SAIDA = "saida", "Saída (venda)"
    AJUSTE = "ajuste", "Ajuste de inventário"
    PERDA = "perda", "Perda / quebra"
    DEVOLUCAO = "devolucao", "Devolução (cliente)"
    ESTORNO = "estorno", "Estorno de venda cancelada"


# Movimentos que somam saldo. Os demais subtraem.
MOVIMENTOS_DE_ENTRADA = {
    TipoMovimento.ENTRADA,
    TipoMovimento.DEVOLUCAO,
    TipoMovimento.ESTORNO,
}


class MovimentoEstoque(LojaModel):
    """
    Cada linha é um evento imutável de estoque.

    `quantidade` é sempre positiva; o sinal vem do `tipo`. `saldo_apos` grava
    o saldo resultante para que o extrato seja auditável sem recalcular a
    série inteira — se o saldo da variação divergir da última linha, houve
    escrita fora do serviço.

    Ajuste de inventário é o único tipo que pode reduzir ou aumentar: o
    serviço converte a contagem informada em quantidade e sinal.
    """

    variacao = models.ForeignKey(
        "produtos.Variacao", on_delete=models.PROTECT,
        related_name="movimentos", verbose_name="variação",
    )
    tipo = models.CharField("tipo", max_length=20, choices=TipoMovimento.choices)
    quantidade = models.PositiveIntegerField("quantidade")
    saldo_apos = models.IntegerField("saldo após o movimento")

    custo_unitario = models.DecimalField(
        "custo unitário", max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    motivo = models.CharField("motivo", max_length=200, blank=True)
    documento = models.CharField("documento", max_length=60, blank=True)

    usuario = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT,
        related_name="movimentos_estoque", verbose_name="usuário",
        null=True, blank=True,
    )
    venda = models.ForeignKey(
        "vendas.Venda", on_delete=models.PROTECT, related_name="movimentos_estoque",
        verbose_name="venda", null=True, blank=True,
    )
    compra = models.ForeignKey(
        "fornecedores.Compra", on_delete=models.PROTECT, related_name="movimentos_estoque",
        verbose_name="compra", null=True, blank=True,
    )

    class Meta:
        verbose_name = "movimento de estoque"
        verbose_name_plural = "movimentos de estoque"
        ordering = ["-criado_em", "-id"]
        indexes = [
            models.Index(fields=["loja", "-criado_em"]),
            models.Index(fields=["variacao", "-criado_em"]),
            models.Index(fields=["loja", "tipo"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.quantidade}× {self.variacao_id}"

    @property
    def eh_entrada(self) -> bool:
        return self.tipo in MOVIMENTOS_DE_ENTRADA

    @property
    def quantidade_com_sinal(self) -> int:
        return self.quantidade if self.eh_entrada else -self.quantidade
