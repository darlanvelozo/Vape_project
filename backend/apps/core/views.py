"""Bases de view que aplicam o isolamento por loja."""

from rest_framework import views, viewsets

from .contexto import definir_loja_atual


class ResolverLojaMixin:
    """
    Publica a loja do usuário autenticado em `request.loja`.

    **Toda view de domínio precisa deste mixin.** O `LojaAtualMiddleware` roda
    antes de o DRF autenticar o JWT — naquele momento `request.user` ainda é
    anônimo, então `request.loja` vem `None`. Uma view que confie apenas no
    middleware enxerga loja nenhuma: no melhor caso devolve vazio, no pior
    grava um registro órfão sem dono.
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        loja = getattr(request.user, "loja", None)
        request.loja = loja
        definir_loja_atual(loja)

    @property
    def loja(self):
        return getattr(self.request, "loja", None)


class LojaAPIView(ResolverLojaMixin, views.APIView):
    """APIView de domínio: use esta base, nunca `APIView` direto."""


class LojaViewSetMixin(ResolverLojaMixin):
    """
    Recorta toda consulta pela loja do usuário autenticado.

    **Este é o único ponto onde o isolamento multi-tenant é aplicado**
    (ADR-0001). Toda ViewSet de domínio precisa herdar daqui; nenhuma deve
    sobrescrever `get_queryset` sem chamar `super()`.
    """

    # Definido pela subclasse: o queryset base, sem recorte.
    queryset = None

    def get_queryset(self):
        queryset = super().get_queryset()
        loja = self.loja
        if loja is None:
            return queryset.none()
        return queryset.filter(loja=loja)

    def perform_create(self, serializer):
        serializer.save(loja=self.loja)


class LojaViewSet(LojaViewSetMixin, viewsets.ModelViewSet):
    """ModelViewSet com isolamento por loja."""


class LojaReadOnlyViewSet(LojaViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """ReadOnlyModelViewSet com isolamento por loja."""
