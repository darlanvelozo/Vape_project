"""
Loja atual da requisição.

Guardada num ContextVar (e não numa thread-local) porque ContextVar é isolado
por tarefa assíncrona além de por thread — funciona igual sob gunicorn com
threads e sob ASGI. Ver ADR-0001.
"""

from contextvars import ContextVar

_loja_atual: ContextVar = ContextVar("loja_atual", default=None)


def definir_loja_atual(loja):
    """Publica a loja da requisição. Devolve o token para restaurar depois."""
    return _loja_atual.set(loja)


def obter_loja_atual():
    """Loja da requisição em curso, ou None fora de um request autenticado."""
    return _loja_atual.get()


def restaurar_loja(token):
    """Desfaz um `definir_loja_atual`, evitando vazamento entre requisições."""
    _loja_atual.reset(token)
