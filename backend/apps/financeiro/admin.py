from django.contrib import admin

from .models import CategoriaFinanceira, Lancamento


@admin.register(CategoriaFinanceira)
class CategoriaFinanceiraAdmin(admin.ModelAdmin):
    list_display = ["nome", "loja", "tipo", "ativo"]
    list_filter = ["loja", "tipo", "ativo"]


@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ["descricao", "loja", "tipo", "valor", "vencimento", "status"]
    list_filter = ["loja", "tipo", "status", "vencimento"]
    search_fields = ["descricao"]
    date_hierarchy = "vencimento"
