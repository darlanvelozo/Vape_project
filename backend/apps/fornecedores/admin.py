from django.contrib import admin

from .models import Compra, Fornecedor, ItemCompra


class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 0


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ["nome", "loja", "cnpj", "telefone", "ativo"]
    list_filter = ["loja", "ativo"]
    search_fields = ["nome", "cnpj"]


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ["id", "loja", "fornecedor", "data", "status", "total"]
    list_filter = ["loja", "status", "data"]
    search_fields = ["numero_documento", "fornecedor__nome"]
    inlines = [ItemCompraInline]
    date_hierarchy = "data"
