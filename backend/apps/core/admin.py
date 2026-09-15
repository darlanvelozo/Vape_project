"""Ajustes globais do Django Admin.

O Admin é ferramenta de suporte (superusuário), não a interface do lojista —
a operação do dia a dia acontece no frontend React.
"""

from django.contrib import admin

admin.site.site_header = "Vape Project — Administração"
admin.site.site_title = "Vape Project"
admin.site.index_title = "Suporte e manutenção"
