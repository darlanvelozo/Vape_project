"""
Catálogo: categoria, marca, produto e variação.

A **variação** é a unidade real de venda e de estoque — um "Elf Bar 10000"
não tem saldo; "Elf Bar 10000 · Blue Razz · 5 mg" tem. Preço e código de
barras vivem na variação porque sabor e teor mudam o custo na prática.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.imagens import caminho_da_imagem
from apps.core.models import LojaModel


class TipoProduto(models.TextChoices):
    DESCARTAVEL = "descartavel", "Descartável"
    POD = "pod", "Pod / dispositivo"
    LIQUIDO = "liquido", "Líquido"
    RESISTENCIA = "resistencia", "Resistência / coil"
    BATERIA = "bateria", "Bateria"
    ACESSORIO = "acessorio", "Acessório"
    OUTRO = "outro", "Outro"


class Categoria(LojaModel):
    nome = models.CharField("nome", max_length=80)
    descricao = models.CharField("descrição", max_length=200, blank=True)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(fields=["loja", "nome"], name="categoria_unica_por_loja")
        ]

    def __str__(self):
        return self.nome


class Marca(LojaModel):
    nome = models.CharField("nome", max_length=80)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "marca"
        verbose_name_plural = "marcas"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(fields=["loja", "nome"], name="marca_unica_por_loja")
        ]

    def __str__(self):
        return self.nome


class Produto(LojaModel):
    nome = models.CharField("nome", max_length=140)
    descricao = models.TextField("descrição", blank=True)
    imagem = models.ImageField(
        "imagem",
        upload_to=caminho_da_imagem,
        blank=True,
        null=True,
        help_text="Foto do modelo, exibida na vitrine pública.",
    )
    tipo = models.CharField("tipo", max_length=20, choices=TipoProduto.choices,
                            default=TipoProduto.DESCARTAVEL)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="produtos",
        verbose_name="categoria", null=True, blank=True,
    )
    marca = models.ForeignKey(
        Marca, on_delete=models.PROTECT, related_name="produtos",
        verbose_name="marca", null=True, blank=True,
    )
    ativo = models.BooleanField("ativo", default=True)

    history = HistoricalRecords(excluded_fields=["atualizado_em", "imagem"])

    class Meta:
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["loja", "ativo"]),
            models.Index(fields=["loja", "nome"]),
        ]

    def __str__(self):
        return self.nome

    @property
    def saldo_total(self) -> int:
        """Soma do saldo de todas as variações ativas."""
        return sum(v.saldo for v in self.variacoes.all() if v.ativo)


class Variacao(LojaModel):
    """
    Combinação vendável de um produto: sabor + teor de nicotina.

    `saldo` é desnormalizado de propósito: o PDV precisa listar dezenas de
    variações com o saldo na tela, e somar movimentos a cada consulta seria
    caro. A consistência é garantida pelo serviço `estoque.servicos`, que é o
    único lugar que escreve nesse campo, sempre com `select_for_update`.
    """

    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE, related_name="variacoes", verbose_name="produto"
    )
    sabor = models.CharField("sabor", max_length=80, blank=True)
    nicotina_mg = models.DecimalField(
        "nicotina (mg/mL)", max_digits=5, decimal_places=2,
        null=True, blank=True, validators=[MinValueValidator(Decimal("0"))],
    )
    puffs = models.PositiveIntegerField("puffs", null=True, blank=True)
    volume_ml = models.DecimalField(
        "volume (mL)", max_digits=6, decimal_places=2, null=True, blank=True
    )

    sku = models.CharField("SKU", max_length=40, blank=True)
    codigo_barras = models.CharField("código de barras", max_length=40, blank=True)

    preco_custo = models.DecimalField(
        "preço de custo", max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    preco_venda = models.DecimalField(
        "preço de venda", max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))],
    )

    saldo = models.IntegerField("saldo em estoque", default=0)
    estoque_minimo = models.PositiveIntegerField("estoque mínimo", default=0)
    ativo = models.BooleanField("ativo", default=True)

    history = HistoricalRecords(excluded_fields=["atualizado_em"])

    class Meta:
        verbose_name = "variação"
        verbose_name_plural = "variações"
        ordering = ["produto__nome", "sabor"]
        constraints = [
            models.UniqueConstraint(
                fields=["produto", "sabor", "nicotina_mg"],
                name="variacao_unica_por_produto",
            ),
            # SKU e código de barras são únicos por loja (ADR-0001), e só
            # quando preenchidos — a maioria das lojas não usa os dois.
            models.UniqueConstraint(
                fields=["loja", "sku"], condition=~models.Q(sku=""),
                name="sku_unico_por_loja",
            ),
            models.UniqueConstraint(
                fields=["loja", "codigo_barras"], condition=~models.Q(codigo_barras=""),
                name="codigo_barras_unico_por_loja",
            ),
        ]
        indexes = [
            models.Index(fields=["loja", "ativo"]),
            models.Index(fields=["loja", "codigo_barras"]),
            models.Index(fields=["loja", "sku"]),
        ]

    def __str__(self):
        return self.descricao_completa

    @property
    def descricao_completa(self) -> str:
        """Como a variação aparece no PDV e no recibo."""
        partes = [self.produto.nome]
        if self.sabor:
            partes.append(self.sabor)
        if self.nicotina_mg is not None:
            partes.append(f"{self.nicotina_mg.normalize()} mg")
        if self.puffs:
            partes.append(f"{self.puffs} puffs")
        return " · ".join(partes)

    @property
    def abaixo_do_minimo(self) -> bool:
        return self.estoque_minimo > 0 and self.saldo <= self.estoque_minimo

    @property
    def margem(self) -> Decimal:
        """Margem sobre o preço de venda, em pontos percentuais."""
        if not self.preco_venda:
            return Decimal("0.00")
        lucro = self.preco_venda - self.preco_custo
        return (lucro / self.preco_venda * 100).quantize(Decimal("0.01"))
