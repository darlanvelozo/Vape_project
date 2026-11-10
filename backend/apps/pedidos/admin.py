from django.contrib import admin

from .models import ItemPedidoOnline, PedidoOnline


class ItemInline(admin.TabularInline):
    model = ItemPedidoOnline
    extra = 0
    readonly_fields = ["variacao", "descricao", "quantidade", "preco_unitario"]


@admin.register(PedidoOnline)
class PedidoOnlineAdmin(admin.ModelAdmin):
    list_display = ["codigo", "loja", "codinome", "status", "tipo_entrega", "total", "criado_em"]
    list_filter = ["status", "tipo_entrega", "loja"]
    search_fields = ["codigo", "codinome", "telefone"]
    exclude = ["comprovante"]
    inlines = [ItemInline]
