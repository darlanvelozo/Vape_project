from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nome", "loja", "telefone", "cpf", "limite_credito", "ativo"]
    list_filter = ["loja", "ativo", "cidade"]
    search_fields = ["nome", "telefone", "cpf", "email"]
