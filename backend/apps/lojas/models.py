"""A loja é o tenant do SaaS (ADR-0001)."""

from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimestampedModel


class Plano(models.TextChoices):
    GRATUITO = "gratuito", "Gratuito"
    PRO = "pro", "Pro"


class Loja(TimestampedModel):
    """
    Uma loja de vapes assinante do sistema.

    Não herda de LojaModel: a loja *é* o tenant, não pertence a um.
    """

    nome = models.CharField("nome", max_length=120, validators=[MinLengthValidator(2)])
    slug = models.SlugField("identificador", max_length=140, unique=True)
    cnpj = models.CharField("CNPJ", max_length=14, blank=True)
    telefone = models.CharField("telefone", max_length=20, blank=True)
    email = models.EmailField("e-mail de contato", blank=True)

    endereco = models.CharField("endereço", max_length=200, blank=True)
    cidade = models.CharField("cidade", max_length=80, blank=True)
    uf = models.CharField("UF", max_length=2, blank=True)
    cep = models.CharField("CEP", max_length=9, blank=True)

    plano = models.CharField("plano", max_length=20, choices=Plano.choices, default=Plano.GRATUITO)
    ativa = models.BooleanField(
        "ativa",
        default=True,
        help_text="Loja inativa não consegue autenticar nem usar a API.",
    )

    # Limites do plano. Zero = ilimitado.
    limite_usuarios = models.PositiveIntegerField("limite de usuários", default=3)
    limite_produtos = models.PositiveIntegerField("limite de produtos", default=0)

    class Meta:
        verbose_name = "loja"
        verbose_name_plural = "lojas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._gerar_slug_unico(self.nome)
        super().save(*args, **kwargs)

    @staticmethod
    def _gerar_slug_unico(nome: str) -> str:
        base = slugify(nome)[:120] or "loja"
        slug = base
        contador = 2
        while Loja.objects.filter(slug=slug).exists():
            slug = f"{base}-{contador}"
            contador += 1
        return slug

    def atingiu_limite_de_usuarios(self) -> bool:
        if not self.limite_usuarios:
            return False
        return self.usuarios.filter(is_active=True).count() >= self.limite_usuarios

    def atingiu_limite_de_produtos(self) -> bool:
        if not self.limite_produtos:
            return False
        return self.produtos.filter(ativo=True).count() >= self.limite_produtos


class ConfiguracaoLoja(TimestampedModel):
    """Preferências operacionais da loja, uma linha por loja."""

    loja = models.OneToOneField(
        Loja, on_delete=models.CASCADE, related_name="configuracao", verbose_name="loja"
    )
    exigir_cliente_na_venda = models.BooleanField("exigir cliente na venda", default=False)
    permitir_venda_sem_estoque = models.BooleanField(
        "permitir venda sem estoque",
        default=False,
        help_text="Se marcado, o PDV aceita vender variação com saldo insuficiente.",
    )
    permitir_fiado = models.BooleanField("permitir fiado", default=True)
    prazo_fiado_dias = models.PositiveIntegerField(
        "prazo do fiado (dias)",
        default=30,
        help_text=(
            "Prazo padrão de vencimento da venda fiada. Zero faz vencer no "
            "mesmo dia — o que marcaria toda venda fiada como atrasada já no "
            "dia seguinte."
        ),
    )
    alerta_estoque_minimo = models.BooleanField("alertar estoque mínimo", default=True)
    mensagem_recibo = models.CharField(
        "mensagem do recibo",
        max_length=200,
        blank=True,
        default="Obrigado pela preferência!",
    )

    class Meta:
        verbose_name = "configuração da loja"
        verbose_name_plural = "configurações das lojas"

    def __str__(self):
        return f"Configuração de {self.loja}"
