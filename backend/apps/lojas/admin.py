from django.contrib import admin

from .models import ConfiguracaoLoja, Loja


class ConfiguracaoInline(admin.StackedInline):
    model = ConfiguracaoLoja
    can_delete = False


@admin.register(Loja)
class LojaAdmin(admin.ModelAdmin):
    list_display = ["nome", "slug", "plano", "ativa", "criado_em"]
    list_filter = ["plano", "ativa"]
    search_fields = ["nome", "slug", "cnpj", "email"]
    readonly_fields = ["slug", "criado_em", "atualizado_em"]
    inlines = [ConfiguracaoInline]


@admin.register(ConfiguracaoLoja)
class ConfiguracaoLojaAdmin(admin.ModelAdmin):
    list_display = ["loja", "permitir_fiado", "permitir_venda_sem_estoque",
                    "vitrine_publica"]
    list_filter = ["vitrine_publica", "permitir_fiado"]
