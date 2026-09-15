"""
Permissões da API.

O modelo de papéis é simples de propósito (ADR-0001): três papéis fixos, sem
Groups do Django. `Usuario.papel` decide o que cada um pode fazer.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class PertenceALoja(BasePermission):
    """
    Padrão do projeto: exige usuário autenticado, ativo e vinculado a uma loja
    ativa. É a primeira linha do isolamento multi-tenant.
    """

    message = "Usuário sem loja vinculada ou loja inativa."

    def has_permission(self, request, view):
        usuario = request.user
        if not (usuario and usuario.is_authenticated and usuario.is_active):
            return False
        loja = getattr(usuario, "loja", None)
        if loja is None:
            # Superusuário de suporte não opera a API de domínio; usa o Admin.
            return False
        return loja.ativa


class EhDono(PertenceALoja):
    """Só o dono da loja."""

    message = "Apenas o dono da loja pode executar esta ação."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.papel == "dono"


class EhDonoOuGerente(PertenceALoja):
    """Dono ou gerente — operações administrativas do dia a dia."""

    message = "Apenas dono ou gerente podem executar esta ação."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.papel in ("dono", "gerente")


class LeituraParaTodosEscritaParaGestao(PertenceALoja):
    """
    Todos da loja leem; só dono e gerente escrevem.

    Usada em cadastros que o vendedor precisa consultar no PDV (produtos,
    categorias, fornecedores) mas não deve alterar no balcão.
    """

    message = "Vendedor pode consultar, mas não alterar este cadastro."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.papel in ("dono", "gerente")
