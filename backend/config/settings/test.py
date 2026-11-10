"""
Ambiente de testes.

Isola o cache (senão o throttle de login/cadastro atravessa testes e o Redis
de desenvolvimento) e acelera o hash de senha, que domina o tempo da suíte.
"""

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "testes",
    }
}

# Throttle desligado por padrão: os testes que o exercitam religam via
# `settings` do pytest-django.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {  # noqa: F405
    "login": None,
    "cadastro": None,
    "vitrine": None,
    "vitrine_pedido": None,
    "vitrine_status": None,
    "vitrine_consulta": None,
}}

# Comprovantes de teste não sujam a pasta real.
import tempfile  # noqa: E402

PRIVADO_ROOT = tempfile.mkdtemp(prefix="vape-privado-")

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
}
