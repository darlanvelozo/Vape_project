from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.lojas.models import ConfiguracaoLoja, Loja
from apps.lojas.serializers import LojaSerializer

from .models import Papel, Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    """Usuário visto pela própria loja."""

    senha = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = Usuario
        fields = ["id", "nome", "email", "papel", "telefone", "is_active", "senha", "date_joined"]
        read_only_fields = ["id", "date_joined"]

    def validate_email(self, valor):
        valor = valor.lower().strip()
        existente = Usuario.objects.filter(email=valor)
        if self.instance:
            existente = existente.exclude(pk=self.instance.pk)
        if existente.exists():
            raise serializers.ValidationError("Já existe um usuário com este e-mail.")
        return valor

    def validate(self, dados):
        if not self.instance and not dados.get("senha"):
            raise serializers.ValidationError({"senha": "Informe a senha do novo usuário."})
        return dados

    def create(self, dados):
        senha = dados.pop("senha")
        usuario = Usuario(**dados)
        usuario.set_password(senha)
        usuario.save()
        return usuario

    def update(self, instancia, dados):
        senha = dados.pop("senha", None)
        for campo, valor in dados.items():
            setattr(instancia, campo, valor)
        if senha:
            instancia.set_password(senha)
        instancia.save()
        return instancia


class UsuarioAtualSerializer(serializers.ModelSerializer):
    """Payload do /api/auth/eu — usuário + loja + permissões derivadas."""

    loja = LojaSerializer(read_only=True)
    pode_gerenciar = serializers.BooleanField(read_only=True)

    class Meta:
        model = Usuario
        fields = ["id", "nome", "email", "papel", "telefone", "loja", "pode_gerenciar"]


class TokenSerializer(TokenObtainPairSerializer):
    """Login: recusa usuário de loja inativa e devolve os dados do usuário."""

    def validate(self, atributos):
        dados = super().validate(atributos)
        usuario = self.user

        if usuario.loja is None:
            raise serializers.ValidationError(
                "Esta conta é de suporte e não tem acesso ao sistema da loja."
            )
        if not usuario.loja.ativa:
            raise serializers.ValidationError(
                "A loja está inativa. Fale com o suporte para reativá-la."
            )

        dados["usuario"] = UsuarioAtualSerializer(usuario).data
        return dados

    @classmethod
    def get_token(cls, usuario):
        token = super().get_token(usuario)
        # Claims úteis para o frontend evitar uma ida extra ao servidor.
        token["loja_id"] = usuario.loja_id
        token["papel"] = usuario.papel
        return token


class CadastroLojaSerializer(serializers.Serializer):
    """
    Onboarding do SaaS: cria a loja, a configuração padrão e o usuário dono
    numa transação só.
    """

    loja_nome = serializers.CharField(max_length=120)
    nome = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, validators=[validate_password])
    telefone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, valor):
        valor = valor.lower().strip()
        if Usuario.objects.filter(email=valor).exists():
            raise serializers.ValidationError("Já existe uma conta com este e-mail.")
        return valor

    @transaction.atomic
    def create(self, dados):
        loja = Loja.objects.create(nome=dados["loja_nome"])
        ConfiguracaoLoja.objects.create(loja=loja)
        usuario = Usuario.objects.create_user(
            email=dados["email"],
            password=dados["senha"],
            nome=dados["nome"],
            telefone=dados.get("telefone", ""),
            loja=loja,
            papel=Papel.DONO,
        )
        return usuario


class AlterarSenhaSerializer(serializers.Serializer):
    senha_atual = serializers.CharField(write_only=True)
    senha_nova = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_senha_atual(self, valor):
        usuario = self.context["request"].user
        if not usuario.check_password(valor):
            raise serializers.ValidationError("Senha atual incorreta.")
        return valor

    def save(self, **kwargs):
        usuario = self.context["request"].user
        usuario.set_password(self.validated_data["senha_nova"])
        usuario.save(update_fields=["password"])
        return usuario
