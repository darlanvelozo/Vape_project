"""ViewSets base que aplicam o isolamento por loja."""

from rest_framework import viewsets

from .contexto import definir_loja_atual


class LojaViewSetMixin:
    """
    Recorta toda consulta pela loja do usuário autenticado.

    **Este é o único ponto onde o isolamento multi-tenant é aplicado**
    (ADR-0001). Toda ViewSet de domínio precisa herdar daqui; nenhuma deve
    sobrescrever `get_queryset` sem chamar `super()`.
    """

    # Definido pela subclasse: o queryset base, sem recorte.
    queryset = None

    def initial(self, request, *args, **kwargs):
        """
        Publica a loja no contexto **depois** da autenticação JWT.

        O middleware roda antes do DRF autenticar, então para a API é aqui que
        `obter_loja_atual()` passa a devolver a loja certa.
        """
        super().initial(request, *args, **kwargs)
        loja = getattr(request.user, "loja", None)
        request.loja = loja
        definir_loja_atual(loja)

    @property
    def loja(self):
        return getattr(self.request, "loja", None)

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
