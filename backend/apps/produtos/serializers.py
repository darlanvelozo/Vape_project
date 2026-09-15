from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.core.serializers import CentavosField

from .models import Categoria, Marca, Produto, Variacao


class CategoriaSerializer(serializers.ModelSerializer):
    total_produtos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Categoria
        fields = ["id", "nome", "descricao", "ativo", "total_produtos"]


class MarcaSerializer(serializers.ModelSerializer):
    total_produtos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Marca
        fields = ["id", "nome", "ativo", "total_produtos"]


class VariacaoSerializer(serializers.ModelSerializer):
    # `sabor` e `nicotina_mg` participam da constraint de unicidade, e o DRF
    # torna obrigatório todo campo de unique_together. Aqui eles são
    # declarados à mão porque acessório e bateria não têm sabor nem nicotina —
    # exigi-los seria atrito puro no cadastro. A unicidade é validada em
    # `validate()`.
    sabor = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    nicotina_mg = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, default=None
    )
    preco_custo_centavos = CentavosField(source="preco_custo", min_value=0, required=False,
                                         default=Decimal("0.00"))
    preco_venda_centavos = CentavosField(source="preco_venda", min_value=0)
    descricao_completa = serializers.CharField(read_only=True)
    abaixo_do_minimo = serializers.BooleanField(read_only=True)
    margem = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)

    class Meta:
        model = Variacao
        fields = [
            "id", "produto", "sabor", "nicotina_mg", "puffs", "volume_ml",
            "sku", "codigo_barras",
            "preco_custo_centavos", "preco_venda_centavos",
            "saldo", "estoque_minimo", "ativo",
            "descricao_completa", "abaixo_do_minimo", "margem",
        ]
        # Saldo só muda por movimentação de estoque — nunca por edição direta.
        read_only_fields = ["id", "saldo", "produto"]

    def validate(self, dados):
        """
        Unicidade de (produto, sabor, nicotina) validada à mão.

        O validador automático do DRF foi descartado porque `produto` é
        read-only aqui — sem esta checagem, uma duplicata só estouraria no
        banco, virando erro 500 em vez de uma mensagem ao usuário.

        Preço de venda abaixo do custo não é bloqueado: promoção e queima de
        estoque são decisões legítimas do lojista.
        """
        produto = getattr(self.instance, "produto", None) or self.context.get("produto")
        if produto is None:
            return dados

        sabor = dados.get("sabor", getattr(self.instance, "sabor", ""))
        nicotina = dados.get("nicotina_mg", getattr(self.instance, "nicotina_mg", None))

        irmas = Variacao.objects.filter(produto=produto, sabor=sabor, nicotina_mg=nicotina)
        if self.instance:
            irmas = irmas.exclude(pk=self.instance.pk)
        if irmas.exists():
            raise serializers.ValidationError(
                "Já existe uma variação deste produto com esse sabor e teor de nicotina."
            )
        return dados


class VariacaoResumoSerializer(serializers.ModelSerializer):
    """Versão enxuta para o PDV e para listagens de estoque."""

    descricao_completa = serializers.CharField(read_only=True)
    preco_venda_centavos = CentavosField(source="preco_venda", read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)

    class Meta:
        model = Variacao
        fields = [
            "id", "produto", "produto_nome", "descricao_completa", "sabor",
            "nicotina_mg", "sku", "codigo_barras", "preco_venda_centavos",
            "saldo", "estoque_minimo", "ativo",
        ]


class ProdutoSerializer(serializers.ModelSerializer):
    variacoes = VariacaoSerializer(many=True, required=False)
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True)
    marca_nome = serializers.CharField(source="marca.nome", read_only=True)
    saldo_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = Produto
        fields = [
            "id", "nome", "descricao", "tipo", "categoria", "categoria_nome",
            "marca", "marca_nome", "ativo", "variacoes", "saldo_total", "criado_em",
        ]
        read_only_fields = ["id", "criado_em"]

    def validate_categoria(self, categoria):
        return self._validar_pertence_a_loja(categoria, "categoria")

    def validate_marca(self, marca):
        return self._validar_pertence_a_loja(marca, "marca")

    def _validar_pertence_a_loja(self, objeto, rotulo):
        """
        Barra referência a cadastro de outra loja.

        Sem isto, uma loja poderia apontar seu produto para a categoria de
        outra informando um id qualquer — vazamento de tenant por escrita.
        """
        if objeto is None:
            return objeto
        loja = getattr(self.context.get("request"), "loja", None)
        if loja and objeto.loja_id != loja.id:
            raise serializers.ValidationError(f"A {rotulo} informada não é desta loja.")
        return objeto

    def validate_variacoes(self, variacoes):
        """Duas variações iguais no mesmo envio também são duplicata."""
        chaves = [(v.get("sabor", ""), v.get("nicotina_mg")) for v in variacoes]
        if len(chaves) != len(set(chaves)):
            raise serializers.ValidationError(
                "Há variações repetidas (mesmo sabor e teor de nicotina) neste produto."
            )
        return variacoes

    @transaction.atomic
    def create(self, dados):
        variacoes = dados.pop("variacoes", [])
        produto = Produto.objects.create(**dados)
        for variacao in variacoes:
            Variacao.objects.create(produto=produto, loja=produto.loja, **variacao)
        if not variacoes:
            # Produto sem variação informada ganha uma variação padrão, senão
            # não é vendável — o PDV só enxerga variações.
            Variacao.objects.create(produto=produto, loja=produto.loja, sabor="Padrão")
        return produto

    @transaction.atomic
    def update(self, instancia, dados):
        # As variações têm endpoint próprio (/api/variacoes); aqui só o produto.
        dados.pop("variacoes", None)
        for campo, valor in dados.items():
            setattr(instancia, campo, valor)
        instancia.save()
        return instancia
