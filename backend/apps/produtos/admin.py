from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Categoria, Marca, Produto, Variacao


class VariacaoInline(admin.TabularInline):
    model = Variacao
    extra = 0
    readonly_fields = ["saldo"]
    fields = ["sabor", "nicotina_mg", "puffs", "sku", "codigo_barras",
              "preco_custo", "preco_venda", "saldo", "estoque_minimo", "ativo"]


@admin.register(Produto)
class ProdutoAdmin(SimpleHistoryAdmin):
    list_display = ["nome", "loja", "tipo", "categoria", "marca", "ativo"]
    list_filter = ["loja", "tipo", "ativo", "categoria"]
    search_fields = ["nome"]
    inlines = [VariacaoInline]


@admin.register(Variacao)
class VariacaoAdmin(SimpleHistoryAdmin):
    list_display = ["__str__", "loja", "sku", "preco_venda", "saldo", "ativo"]
    list_filter = ["loja", "ativo"]
    search_fields = ["produto__nome", "sabor", "sku", "codigo_barras"]
    readonly_fields = ["saldo"]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nome", "loja", "ativo"]
    list_filter = ["loja", "ativo"]


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ["nome", "loja", "ativo"]
    list_filter = ["loja", "ativo"]
