"""Modelos abstratos reutilizados por todo o domínio."""

from django.db import models

from .contexto import obter_loja_atual


class TimestampedModel(models.Model):
    """Carimbo de criação e atualização."""

    criado_em = models.DateTimeField("criado em", auto_now_add=True, db_index=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        abstract = True


class LojaQuerySet(models.QuerySet):
    """QuerySet com atalho para o recorte por tenant."""

    def da_loja(self, loja):
        return self.filter(loja=loja)

    def da_loja_atual(self):
        """Recorte pela loja publicada no contexto da requisição."""
        loja = obter_loja_atual()
        if loja is None:
            return self.none()
        return self.filter(loja=loja)


class LojaModel(TimestampedModel):
    """
    Base de todo modelo pertencente a uma loja.

    PROTECT porque apagar uma loja com movimento é erro de operação: o
    caminho correto é desativá-la (`Loja.ativa = False`).
    """

    loja = models.ForeignKey(
        "lojas.Loja",
        on_delete=models.PROTECT,
        related_name="%(class)ss",
        verbose_name="loja",
        db_index=True,
    )

    objects = LojaQuerySet.as_manager()

    class Meta:
        abstract = True
