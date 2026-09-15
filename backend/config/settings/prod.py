"""
Ambiente de produção.

Nginx termina o TLS e faz proxy para o gunicorn em 127.0.0.1 — por isso o
Django precisa confiar no cabeçalho X-Forwarded-Proto para saber que a
requisição original era HTTPS.
"""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# Sem default: em produção a ausência da variável deve quebrar o boot, não
# silenciosamente subir com chave de desenvolvimento.
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# O frontend é servido pelo mesmo Nginx (mesma origem), então CORS fica
# fechado por padrão; só é preenchido se o frontend for para outro host.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
