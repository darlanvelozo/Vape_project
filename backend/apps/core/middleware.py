"""Middleware que resolve a loja (tenant) da requisição."""

from .contexto import definir_loja_atual, restaurar_loja


class LojaAtualMiddleware:
    """
    Publica `request.loja` e o ContextVar correspondente.

    A autenticação do DRF acontece dentro da view, depois deste middleware —
    por isso aqui só conseguimos resolver usuários de sessão (Django Admin).
    Para a API quem popula o contexto é `apps.core.views.LojaViewSet.initial`,
    que roda já com `request.user` autenticado pelo JWT. Este middleware
    garante a limpeza do contexto ao fim da requisição nos dois casos.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        loja = getattr(usuario, "loja", None) if usuario and usuario.is_authenticated else None
        request.loja = loja
        token = definir_loja_atual(loja)
        try:
            return self.get_response(request)
        finally:
            restaurar_loja(token)
