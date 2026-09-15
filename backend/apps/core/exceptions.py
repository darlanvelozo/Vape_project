"""Erros de domínio e tradução para respostas HTTP."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ErroDeNegocio(Exception):
    """
    Regra de negócio violada — vira HTTP 400 com mensagem em português.

    Serviços de domínio (estoque, caixa, venda) levantam esta exceção; as
    views não precisam traduzir nada.
    """

    def __init__(self, mensagem: str, campo: str = "detalhe"):
        self.mensagem = mensagem
        self.campo = campo
        super().__init__(mensagem)


class EstoqueInsuficiente(ErroDeNegocio):
    pass


class CaixaFechado(ErroDeNegocio):
    pass


def tratador_de_excecao(exc, context):
    """Handler do DRF que entende os erros de domínio do projeto."""
    if isinstance(exc, ErroDeNegocio):
        return Response({exc.campo: [exc.mensagem]}, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, DjangoValidationError):
        detalhe = getattr(exc, "message_dict", None) or {"detalhe": list(exc.messages)}
        return Response(detalhe, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, ProtectedError):
        return Response(
            {"detalhe": [
                "Não é possível excluir: o registro está em uso por outros "
                "cadastros ou movimentações. Desative-o em vez de excluir."
            ]},
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, IntegrityError):
        # Rede de segurança para corridas que passam pelas validações do
        # serializer e só estouram na constraint do banco.
        return Response(
            {"detalhe": [
                "Não foi possível salvar: o registro conflita com outro já "
                "existente (código, SKU ou combinação duplicada)."
            ]},
            status=status.HTTP_409_CONFLICT,
        )

    return exception_handler(exc, context)
