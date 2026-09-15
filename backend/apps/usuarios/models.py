"""Usuário do sistema: login por e-mail, vinculado a uma loja."""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Papel(models.TextChoices):
    DONO = "dono", "Dono"
    GERENTE = "gerente", "Gerente"
    VENDEDOR = "vendedor", "Vendedor"


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _criar(self, email, password, **extra):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        email = self.normalize_email(email).lower()
        usuario = self.model(email=email, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._criar(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("papel", Papel.DONO)
        if not extra.get("is_staff") or not extra.get("is_superuser"):
            raise ValueError("Superusuário precisa de is_staff e is_superuser.")
        # Superusuário é conta de suporte: sem loja, opera só pelo Django Admin.
        extra.setdefault("loja", None)
        return self._criar(email, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("e-mail", unique=True)
    nome = models.CharField("nome", max_length=120)
    loja = models.ForeignKey(
        "lojas.Loja",
        on_delete=models.PROTECT,
        related_name="usuarios",
        verbose_name="loja",
        null=True,
        blank=True,
        help_text="Vazio apenas para contas de suporte (superusuário).",
    )
    papel = models.CharField("papel", max_length=20, choices=Papel.choices, default=Papel.VENDEDOR)
    telefone = models.CharField("telefone", max_length=20, blank=True)

    is_active = models.BooleanField("ativo", default=True)
    is_staff = models.BooleanField("acesso ao admin", default=False)
    date_joined = models.DateTimeField("cadastrado em", default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["nome"]
        indexes = [models.Index(fields=["loja", "is_active"])]

    def __str__(self):
        return f"{self.nome} <{self.email}>"

    @property
    def eh_dono(self) -> bool:
        return self.papel == Papel.DONO

    @property
    def pode_gerenciar(self) -> bool:
        """Dono e gerente administram cadastros e veem relatórios financeiros."""
        return self.papel in (Papel.DONO, Papel.GERENTE)
