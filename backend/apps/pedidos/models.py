"""
Pedido feito pelo cliente na vitrine pública (ADR-0004).

O pedido **não é venda**. Ele segura as unidades por um prazo enquanto o
cliente paga o Pix; a venda só nasce quando o atendente confere o pagamento
e aprova — é aí que o estoque baixa e o financeiro recebe o lançamento.
"""

import secrets

from django.conf import settings
from django.db import models

from apps.core.models import LojaModel, TimestampedModel

# Sem 0/O, 1/I/L: o código é ditado por telefone e digitado no celular.
ALFABETO_CODIGO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def gerar_codigo() -> str:
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(6))


def gerar_token() -> str:
    return secrets.token_urlsafe(18)


def caminho_comprovante(instancia, nome_original: str) -> str:
    return f"comprovantes/{instancia.loja.slug}/{secrets.token_hex(16)}.jpg"


def _armazenamento_privado():
    """Fora de MEDIA_ROOT: `/media/` é servido sem login pelo nginx."""
    from django.core.files.storage import FileSystemStorage

    return FileSystemStorage(location=settings.PRIVADO_ROOT)


class StatusPedido(models.TextChoices):
    AGUARDANDO_PAGAMENTO = "aguardando_pagamento", "Aguardando pagamento"
    AGUARDANDO_CONFERENCIA = "aguardando_conferencia", "Pagamento em conferência"
    PREPARANDO = "preparando", "Pago — preparando"
    PRONTO_RETIRADA = "pronto_retirada", "Pronto para retirada"
    SAIU_ENTREGA = "saiu_entrega", "Saiu para entrega"
    ENTREGUE = "entregue", "Entregue"
    CANCELADO = "cancelado", "Cancelado"
    EXPIRADO = "expirado", "Expirado"


# Status que ainda seguram estoque (antes da aprovação).
STATUS_RESERVANDO = (
    StatusPedido.AGUARDANDO_PAGAMENTO,
    StatusPedido.AGUARDANDO_CONFERENCIA,
)
# Status de pedido já pago, em que a loja movimenta a entrega.
STATUS_PAGOS = (
    StatusPedido.PREPARANDO,
    StatusPedido.PRONTO_RETIRADA,
    StatusPedido.SAIU_ENTREGA,
    StatusPedido.ENTREGUE,
)


class TipoEntrega(models.TextChoices):
    ENTREGA = "entrega", "Entrega"
    RETIRADA = "retirada", "Retirada na loja"


class PedidoOnline(LojaModel):
    codigo = models.CharField("código", max_length=10)
    token = models.CharField("token de acesso", max_length=40, unique=True, default=gerar_token)

    telefone = models.CharField("telefone", max_length=20, db_index=True)
    codinome = models.CharField("codinome", max_length=60)
    declarou_maioridade = models.BooleanField("declarou ter 18 anos ou mais", default=False)

    tipo_entrega = models.CharField(
        "recebimento", max_length=10, choices=TipoEntrega.choices, default=TipoEntrega.RETIRADA
    )
    latitude = models.DecimalField(
        "latitude", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        "longitude", max_digits=9, decimal_places=6, null=True, blank=True
    )
    precisao_m = models.PositiveIntegerField("precisão do GPS (m)", null=True, blank=True)
    endereco = models.CharField("endereço", max_length=200, blank=True)
    referencia = models.CharField("ponto de referência", max_length=200, blank=True)
    observacoes = models.CharField("observações do cliente", max_length=300, blank=True)

    status = models.CharField(
        "status", max_length=30, choices=StatusPedido.choices,
        default=StatusPedido.AGUARDANDO_PAGAMENTO, db_index=True,
    )
    total = models.DecimalField("total", max_digits=12, decimal_places=2)
    expira_em = models.DateTimeField("reserva expira em")

    comprovante = models.ImageField(
        "comprovante do Pix", upload_to=caminho_comprovante,
        storage=_armazenamento_privado, blank=True,
    )
    comprovante_enviado_em = models.DateTimeField(null=True, blank=True)

    venda = models.OneToOneField(
        "vendas.Venda", on_delete=models.PROTECT, null=True, blank=True,
        related_name="pedido_online", verbose_name="venda",
    )
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="+", verbose_name="aprovado por",
    )
    pago_em = models.DateTimeField("pagamento aprovado em", null=True, blank=True)

    previsao_entrega = models.DateTimeField("previsão de entrega", null=True, blank=True)
    recado_loja = models.CharField(
        "recado para o cliente", max_length=200, blank=True,
        help_text="Aparece na página do pedido. Ex.: 'Motoboy João, moto vermelha'.",
    )
    saiu_em = models.DateTimeField(null=True, blank=True)
    entregue_em = models.DateTimeField(null=True, blank=True)
    cancelado_em = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "pedido on-line"
        verbose_name_plural = "pedidos on-line"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(fields=["loja", "codigo"], name="pedido_codigo_unico_por_loja"),
        ]
        indexes = [models.Index(fields=["loja", "telefone"])]

    def __str__(self):
        return f"Pedido {self.codigo} — {self.codinome}"

    @property
    def pago(self) -> bool:
        return self.status in STATUS_PAGOS


class ItemPedidoOnline(TimestampedModel):
    pedido = models.ForeignKey(PedidoOnline, on_delete=models.CASCADE, related_name="itens")
    variacao = models.ForeignKey(
        "produtos.Variacao", on_delete=models.PROTECT, related_name="itens_pedido_online"
    )
    descricao = models.CharField("descrição", max_length=200)
    quantidade = models.PositiveIntegerField("quantidade")
    preco_unitario = models.DecimalField("preço unitário", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "item do pedido on-line"
        verbose_name_plural = "itens do pedido on-line"

    @property
    def total(self):
        return self.preco_unitario * self.quantidade
