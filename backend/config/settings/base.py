"""
Configuração comum a todos os ambientes.

Tudo que varia por ambiente (segredo, banco, hosts, CORS) vem de variável de
ambiente via django-environ. `dev.py` e `prod.py` só ajustam o que difere.
"""

from datetime import timedelta
from pathlib import Path

import environ

# backend/config/settings/base.py -> backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# raiz do repositório (onde fica o .env de desenvolvimento)
RAIZ_REPO = BASE_DIR.parent

env = environ.Env()
for caminho in (RAIZ_REPO / ".env", BASE_DIR / ".env"):
    if caminho.exists():
        env.read_env(str(caminho))
        break

SECRET_KEY = env("DJANGO_SECRET_KEY", default="inseguro-somente-para-desenvolvimento")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ------------------------------------------------------------------
# Aplicações
# ------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

TERCEIROS_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "simple_history",
]

APPS_LOCAIS = [
    "apps.core",
    "apps.lojas",
    "apps.usuarios",
    "apps.produtos",
    "apps.estoque",
    "apps.clientes",
    "apps.fornecedores",
    "apps.vendas",
    "apps.financeiro",
    "apps.relatorios",
]

INSTALLED_APPS = DJANGO_APPS + TERCEIROS_APPS + APPS_LOCAIS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    # Resolve a loja (tenant) do usuário autenticado — ver ADR-0001.
    "apps.core.middleware.LojaAtualMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ------------------------------------------------------------------
# Banco de dados
# ------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://vape:vape@localhost:5433/vape_dev",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------
# Autenticação
# ------------------------------------------------------------------
AUTH_USER_MODEL = "usuarios.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------
# Internacionalização
# ------------------------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = env("TZ", default="America/Sao_Paulo")
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------
# Estáticos e mídia
# ------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static_collected"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# ------------------------------------------------------------------
# DRF
# ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "apps.core.permissions.PertenceALoja",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.PaginacaoPadrao",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "login": env("THROTTLE_LOGIN", default="10/min"),
        "cadastro": env("THROTTLE_CADASTRO", default="5/hour"),
        # Vitrine é pública: teto generoso para o cliente navegar, baixo
        # o bastante para não servir de raspagem de catálogo.
        "vitrine": env("THROTTLE_VITRINE", default="120/hour"),
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.tratador_de_excecao",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MIN", default=60)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DIAS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Vape Project — API",
    "DESCRIPTION": (
        "API de gestão e vendas para loja de vapes: catálogo com variações, "
        "estoque, PDV com caixa, clientes, fornecedores e financeiro. "
        "Multi-loja (SaaS): cada requisição enxerga apenas a loja do usuário "
        "autenticado. Valores monetários trafegam em centavos inteiros."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    # Vários modelos têm campos `status` e `tipo` com conjuntos de escolhas
    # diferentes. Sem nomear cada enum, o gerador inventa nomes como
    # "Status7c7Enum", que vazam para os tipos TypeScript do frontend.
    "ENUM_NAME_OVERRIDES": {
        "StatusVendaEnum": "apps.vendas.models.StatusVenda.choices",
        "StatusCaixaEnum": "apps.vendas.models.StatusCaixa.choices",
        "StatusCompraEnum": "apps.fornecedores.models.StatusCompra.choices",
        "StatusLancamentoEnum": "apps.financeiro.models.StatusLancamento.choices",
        "TipoProdutoEnum": "apps.produtos.models.TipoProduto.choices",
        "TipoMovimentoEstoqueEnum": "apps.estoque.models.TipoMovimento.choices",
        "TipoMovimentoCaixaEnum": "apps.vendas.models.TipoMovimentoCaixa.choices",
        "TipoLancamentoEnum": "apps.financeiro.models.TipoLancamento.choices",
        "FormaPagamentoEnum": "apps.vendas.models.FormaPagamento.choices",
        "PapelEnum": "apps.usuarios.models.Papel.choices",
        "PlanoEnum": "apps.lojas.models.Plano.choices",
    },
}

# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = False

# ------------------------------------------------------------------
# Cache
# ------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6380/0"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "vape",
    }
}

# ------------------------------------------------------------------
# Regras de negócio configuráveis
# ------------------------------------------------------------------
# Idade mínima para compra (ADR-0003). Zero desativa a checagem.
IDADE_MINIMA_COMPRA = env.int("IDADE_MINIMA_COMPRA", default=18)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "padrao": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "padrao"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "handlers": ["console"], "propagate": False},
    },
}
