from django.contrib import admin

from .models import Caixa, ItemVenda, MovimentoCaixa, Pagamento, Venda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 0
    readonly_fields = ["variacao", "descricao", "quantidade", "preco_unitario",
                       "desconto", "custo_unitario"]


class PagamentoInline(admin.TabularInline):
    model = Pagamento
    extra = 0
    readonly_fields = ["forma", "valor", "troco", "observacao"]


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ["numero", "loja", "status", "total", "cliente", "usuario", "criado_em"]
    list_filter = ["loja", "status", "criado_em"]
    search_fields = ["numero", "cliente__nome"]
    date_hierarchy = "criado_em"
    inlines = [ItemVendaInline, PagamentoInline]

    def has_add_permission(self, request):
        # Venda nasce no PDV, nunca no Admin: pelo Admin não há baixa de estoque.
        return False


@admin.register(Caixa)
class CaixaAdmin(admin.ModelAdmin):
    list_display = ["id", "loja", "status", "aberto_em", "fechado_em",
                    "saldo_calculado", "diferenca"]
    list_filter = ["loja", "status"]


@admin.register(MovimentoCaixa)
class MovimentoCaixaAdmin(admin.ModelAdmin):
    list_display = ["criado_em", "loja", "caixa", "tipo", "valor", "usuario"]
    list_filter = ["loja", "tipo"]
