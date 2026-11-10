"""
Endpoints públicos do pedido on-line — o cliente não tem login.

Mesma regra da vitrine: a loja é achada pelo slug, e loja inexistente,
inativa ou sem venda on-line respondem o mesmo 404. O pedido é achado pelo
`token` (longo, impossível de chutar), nunca pelo código curto.
"""

from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.lojas.models import Loja

from . import servicos
from .models import PedidoOnline
from .serializers import (
    ConsultaTelefoneSerializer,
    CriarPedidoSerializer,
    PedidoPublicoSerializer,
    PedidoResumoPublicoSerializer,
)

# A consulta por telefone mostra só pedidos recentes.
JANELA_CONSULTA = timedelta(days=90)


def _loja_vendendo(slug) -> Loja:
    loja = Loja.objects.filter(slug=slug, ativa=True).select_related("configuracao").first()
    configuracao = getattr(loja, "configuracao", None)
    if loja is None or configuracao is None or not configuracao.vitrine_publica:
        raise NotFound("Vitrine não encontrada.")
    return loja


def _pedido(loja, token) -> PedidoOnline:
    servicos.expirar_vencidos(loja)
    pedido = (
        PedidoOnline.objects.filter(loja=loja, token=token)
        .select_related("loja", "loja__configuracao", "venda")
        .prefetch_related("itens").first()
    )
    if pedido is None:
        raise NotFound("Pedido não encontrado.")
    return pedido


class _Publica(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []


class CriarPedidoPublicoView(_Publica):
    """POST /api/vitrine/{slug}/pedidos/"""

    throttle_scope = "vitrine_pedido"

    @extend_schema(request=CriarPedidoSerializer, responses=PedidoPublicoSerializer)
    def post(self, request, slug):
        loja = _loja_vendendo(slug)
        entrada = CriarPedidoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pedido = servicos.criar_pedido(loja=loja, **entrada.validated_data)
        return Response(
            PedidoPublicoSerializer(_pedido(loja, pedido.token)).data,
            status=status.HTTP_201_CREATED,
        )


class PedidoPublicoView(_Publica):
    """GET /api/vitrine/{slug}/pedidos/{token}/ — a página do pedido consulta aqui."""

    throttle_scope = "vitrine_status"

    @extend_schema(responses=PedidoPublicoSerializer)
    def get(self, request, slug, token):
        loja = _loja_vendendo(slug)
        return Response(PedidoPublicoSerializer(_pedido(loja, token)).data)


class InformarPagamentoPublicoView(_Publica):
    """POST /api/vitrine/{slug}/pedidos/{token}/pagamento/ — "já paguei" (+ imagem opcional)."""

    throttle_scope = "vitrine_pedido"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(request=None, responses=PedidoPublicoSerializer)
    def post(self, request, slug, token):
        loja = _loja_vendendo(slug)
        pedido = servicos.informar_pagamento(
            pedido=_pedido(loja, token), comprovante=request.FILES.get("comprovante"),
        )
        return Response(PedidoPublicoSerializer(_pedido(loja, pedido.token)).data)


class CancelarPedidoPublicoView(_Publica):
    """POST /api/vitrine/{slug}/pedidos/{token}/cancelar/ — desistência antes de pagar."""

    throttle_scope = "vitrine_pedido"

    @extend_schema(request=None, responses=PedidoPublicoSerializer)
    def post(self, request, slug, token):
        loja = _loja_vendendo(slug)
        pedido = servicos.cliente_cancelar(pedido=_pedido(loja, token))
        return Response(PedidoPublicoSerializer(_pedido(loja, pedido.token)).data)


class MeusPedidosPublicoView(_Publica):
    """
    POST /api/vitrine/{slug}/meus-pedidos/ — o cliente acha os pedidos pelo telefone.

    POST e não GET: telefone é dado pessoal e não deve ir para a URL (fica em
    log de servidor e histórico do navegador). A resposta é enxuta — código,
    status, total — e o limite por IP é baixo para não servir de varredura.
    """

    throttle_scope = "vitrine_consulta"

    @extend_schema(
        request=ConsultaTelefoneSerializer,
        responses=PedidoResumoPublicoSerializer(many=True),
    )
    def post(self, request, slug):
        loja = _loja_vendendo(slug)
        entrada = ConsultaTelefoneSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        telefone = servicos.normalizar_telefone(entrada.validated_data["telefone"])
        servicos.expirar_vencidos(loja)
        pedidos = (
            PedidoOnline.objects.filter(
                loja=loja, telefone=telefone,
                criado_em__gte=timezone.now() - JANELA_CONSULTA,
            )
            .prefetch_related("itens").order_by("-criado_em")[:20]
        )
        return Response(PedidoResumoPublicoSerializer(pedidos, many=True).data)
