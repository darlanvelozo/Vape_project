from django.contrib import admin

from .models import MovimentoEstoque


@admin.register(MovimentoEstoque)
class MovimentoEstoqueAdmin(admin.ModelAdmin):
    list_display = ["criado_em", "loja", "variacao", "tipo", "quantidade", "saldo_apos", "usuario"]
    list_filter = ["loja", "tipo", "criado_em"]
    search_fields = ["variacao__produto__nome", "motivo", "documento"]
    date_hierarchy = "criado_em"
    # Movimento é imutável: o Admin só lê.
    readonly_fields = [campo.name for campo in MovimentoEstoque._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
