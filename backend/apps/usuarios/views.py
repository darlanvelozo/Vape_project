from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.exceptions import ErroDeNegocio
from apps.core.permissions import EhDonoOuGerente, PertenceALoja
from apps.core.views import LojaAPIView, LojaViewSetMixin
from apps.lojas.serializers import ConfiguracaoLojaSerializer, LojaSerializer

from .models import Papel, Usuario
from .serializers import (
    AlterarSenhaSerializer,
    CadastroLojaSerializer,
    TokenSerializer,
    UsuarioAtualSerializer,
    UsuarioSerializer,
)


class LoginView(TokenObtainPairView):
    """POST /api/auth/token — devolve access, refresh e os dados do usuário."""

    serializer_class = TokenSerializer
    permission_classes = [AllowAny]
    throttle_scope = "login"


class CadastroLojaView(CreateAPIView):
    """POST /api/auth/cadastrar — onboarding público de uma nova loja."""

    serializer_class = CadastroLojaSerializer
    permission_classes = [AllowAny]
    throttle_scope = "cadastro"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()

        # Já devolve o par de tokens: o cadastro cai direto no sistema logado.
        token = TokenSerializer.get_token(usuario)
        return Response(
            {
                "access": str(token.access_token),
                "refresh": str(token),
                "usuario": UsuarioAtualSerializer(usuario).data,
            },
            status=status.HTTP_201_CREATED,
        )


class UsuarioAtualView(LojaAPIView):
    """GET /api/auth/eu — quem sou eu, minha loja e meu papel."""

    permission_classes = [PertenceALoja]

    @extend_schema(responses=UsuarioAtualSerializer)
    def get(self, request):
        return Response(UsuarioAtualSerializer(request.user).data)

    @extend_schema(request=UsuarioAtualSerializer, responses=UsuarioAtualSerializer)
    def patch(self, request):
        """Atualiza o próprio nome e telefone."""
        serializer = UsuarioAtualSerializer(
            request.user,
            data={k: v for k, v in request.data.items() if k in ("nome", "telefone")},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AlterarSenhaView(APIView):
    """POST /api/auth/senha — troca a própria senha."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=AlterarSenhaSerializer, responses={204: None})
    def post(self, request):
        serializer = AlterarSenhaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsuarioViewSet(LojaViewSetMixin, viewsets.ModelViewSet):
    """Equipe da loja. Só dono e gerente administram."""

    queryset = Usuario.objects.select_related("loja")
    serializer_class = UsuarioSerializer
    permission_classes = [EhDonoOuGerente]
    search_fields = ["nome", "email"]
    filterset_fields = ["papel", "is_active"]
    ordering_fields = ["nome", "date_joined"]

    def perform_create(self, serializer):
        loja = self.loja
        if loja.atingiu_limite_de_usuarios():
            raise ErroDeNegocio(
                f"O plano atual permite {loja.limite_usuarios} usuários ativos. "
                "Desative um usuário ou fale com o suporte para ampliar o plano.",
                campo="loja",
            )
        # Gerente não cria dono: evita escalada de privilégio pela API.
        eh_gerente = self.request.user.papel == Papel.GERENTE
        if eh_gerente and serializer.validated_data.get("papel") == Papel.DONO:
            raise ErroDeNegocio("Gerente não pode criar usuário com papel de dono.", campo="papel")
        serializer.save(loja=loja)

    def perform_update(self, serializer):
        alvo = serializer.instance
        solicitante = self.request.user
        if solicitante.papel == Papel.GERENTE and alvo.papel == Papel.DONO:
            raise ErroDeNegocio("Gerente não pode alterar o usuário dono.", campo="papel")
        serializer.save()

    def perform_destroy(self, instancia):
        if instancia.pk == self.request.user.pk:
            raise ErroDeNegocio("Você não pode excluir a própria conta.", campo="id")
        if instancia.papel == Papel.DONO and self._quantidade_de_donos_ativos() <= 1:
            raise ErroDeNegocio(
                "A loja precisa de ao menos um dono ativo.", campo="papel"
            )
        # Usuário com vendas registradas não pode sumir (FK PROTECT): desativa.
        instancia.is_active = False
        instancia.save(update_fields=["is_active"])

    def _quantidade_de_donos_ativos(self) -> int:
        return self.get_queryset().filter(papel=Papel.DONO, is_active=True).count()

    @extend_schema(responses=UsuarioSerializer)
    @action(detail=True, methods=["post"])
    def reativar(self, request, pk=None):
        usuario = self.get_object()
        usuario.is_active = True
        usuario.save(update_fields=["is_active"])
        return Response(self.get_serializer(usuario).data)


class MinhaLojaView(LojaAPIView):
    """GET/PATCH /api/loja — dados cadastrais da própria loja."""

    permission_classes = [PertenceALoja]

    @extend_schema(responses=LojaSerializer)
    def get(self, request):
        if request.loja is None:
            raise ErroDeNegocio("Usuário sem loja vinculada.", campo="loja")
        return Response(LojaSerializer(request.loja).data)

    @extend_schema(request=LojaSerializer, responses=LojaSerializer)
    def patch(self, request):
        if not request.user.pode_gerenciar:
            raise ErroDeNegocio("Apenas dono ou gerente podem alterar os dados da loja.")
        if request.loja is None:
            # Sem instância, o serializer criaria uma loja nova em vez de
            # atualizar a existente.
            raise ErroDeNegocio("Usuário sem loja vinculada.", campo="loja")
        serializer = LojaSerializer(request.loja, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ConfiguracaoLojaView(LojaAPIView):
    """GET/PATCH /api/loja/configuracao — preferências operacionais."""

    permission_classes = [PertenceALoja]

    def _configuracao(self, loja):
        from apps.lojas.models import ConfiguracaoLoja

        if loja is None:
            # Nunca criar configuração sem dono: viraria linha órfã.
            raise ErroDeNegocio("Usuário sem loja vinculada.", campo="loja")
        configuracao, _ = ConfiguracaoLoja.objects.get_or_create(loja=loja)
        return configuracao

    @extend_schema(responses=ConfiguracaoLojaSerializer)
    def get(self, request):
        return Response(ConfiguracaoLojaSerializer(self._configuracao(request.loja)).data)

    @extend_schema(request=ConfiguracaoLojaSerializer, responses=ConfiguracaoLojaSerializer)
    @transaction.atomic
    def patch(self, request):
        if not request.user.pode_gerenciar:
            raise ErroDeNegocio("Apenas dono ou gerente podem alterar as configurações.")
        serializer = ConfiguracaoLojaSerializer(
            self._configuracao(request.loja), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
