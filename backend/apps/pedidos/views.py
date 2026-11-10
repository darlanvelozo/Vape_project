"""Pedidos on-line no painel da loja (ADR-0004)."""

from django.db.models import Q
from django.http import FileResponse, Http404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import ErroDeNegocio
from apps.core.permissions import PertenceALoja
from apps.core.views import LojaViewSetMixin

from . import servicos
from .models import STATUS_PAGOS, PedidoOnline, StatusPedido, TipoEntrega
from .serializers import (
    AtualizarEntregaSerializer,
    CancelarPedidoSerializer,
    PedidoPainelSerializer,
)

SITUACOES = {
    # Precisa de alguém conferir o Pix.
    "pendentes": Q(status__in=[StatusPedido.AGUARDANDO_PAGAMENTO,
                               StatusPedido.AGUARDANDO_CONFERENCIA]),
    # Pago, ainda não chegou ao cliente.
    "andamento": Q(status__in=[StatusPedido.PREPARANDO, StatusPedido.PRONTO_RETIRADA,
                               StatusPedido.SAIU_ENTREGA]),
    "concluidos": Q(status=StatusPedido.ENTREGUE),
    "encerrados": Q(status__in=[StatusPedido.CANCELADO, StatusPedido.EXPIRADO]),
}


class PedidoOnlineViewSet(LojaViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Lista e opera os pedidos da vitrine.

    `?situacao=pendentes|andamento|concluidos|encerrados` e `?entregas=1`
    (só entregas pagas ainda não entregues, na ordem de chegada — é a lista
    que vira rota).
    """

    queryset = PedidoOnline.objects.all()
    serializer_class = PedidoPainelSerializer
    permission_classes = [PertenceALoja]

    def get_queryset(self):
        queryset = (
            super().get_queryset()
            .select_related("venda", "aprovado_por")
            .prefetch_related("itens")
        )
        if self.action != "list":
            return queryset
        parametros = self.request.query_params
        situacao = parametros.get("situacao")
        if situacao in SITUACOES:
            queryset = queryset.filter(SITUACOES[situacao])
        if parametros.get("entregas"):
            queryset = queryset.filter(
                tipo_entrega=TipoEntrega.ENTREGA,
                status__in=[StatusPedido.PREPARANDO, StatusPedido.SAIU_ENTREGA],
            ).order_by("pago_em")
        else:
            queryset = queryset.order_by("-criado_em")
        busca = (parametros.get("busca") or "").strip()
        if busca:
            queryset = queryset.filter(
                Q(codigo__iexact=busca.upper()) | Q(codinome__icontains=busca)
                | Q(telefone__contains="".join(c for c in busca if c.isdigit()) or busca)
            )
        return queryset

    def list(self, request, *args, **kwargs):
        servicos.expirar_vencidos(self.loja)
        return super().list(request, *args, **kwargs)

    def _responder(self, pedido):
        pedido = self.get_queryset().get(pk=pedido.pk)
        return Response(PedidoPainelSerializer(pedido).data)

    @extend_schema(responses=dict)
    @action(detail=False, methods=["get"])
    def resumo(self, request):
        """Contadores do menu — o painel consulta a cada 30 s."""
        servicos.expirar_vencidos(self.loja)
        base = PedidoOnline.objects.filter(loja=self.loja)
        hoje = timezone.localdate()
        return Response({
            "aguardando_pagamento": base.filter(status=StatusPedido.AGUARDANDO_PAGAMENTO).count(),
            "aguardando_conferencia": base.filter(
                status=StatusPedido.AGUARDANDO_CONFERENCIA
            ).count(),
            "em_andamento": base.filter(SITUACOES["andamento"]).count(),
            "entregues_hoje": base.filter(
                status=StatusPedido.ENTREGUE, entregue_em__date=hoje
            ).count(),
        })

    @extend_schema(request=None, responses=PedidoPainelSerializer)
    @action(detail=True, methods=["post"])
    def aprovar(self, request, pk=None):
        pedido = servicos.aprovar_pedido(pedido=self.get_object(), usuario=request.user)
        return self._responder(pedido)

    @extend_schema(request=CancelarPedidoSerializer, responses=PedidoPainelSerializer)
    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        pedido = self.get_object()
        # Cancelar pedido pago estorna venda: mesma regra do cancelamento de
        # venda no PDV (só dono e gerente).
        if pedido.status in STATUS_PAGOS and request.user.papel not in ("dono", "gerente"):
            raise ErroDeNegocio(
                "Pedido já pago só pode ser cancelado por dono ou gerente.", campo="status"
            )
        entrada = CancelarPedidoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pedido = servicos.cancelar_pedido(
            pedido=pedido, usuario=request.user, motivo=entrada.validated_data.get("motivo", ""),
        )
        return self._responder(pedido)

    @extend_schema(request=AtualizarEntregaSerializer, responses=PedidoPainelSerializer)
    @action(detail=True, methods=["post"])
    def entrega(self, request, pk=None):
        entrada = AtualizarEntregaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        pedido = servicos.atualizar_entrega(
            pedido=self.get_object(),
            status=dados.get("status"),
            previsao_entrega=dados["previsao_entrega"] if "previsao_entrega" in dados else ...,
            recado_loja=dados.get("recado_loja"),
        )
        return self._responder(pedido)

    @extend_schema(responses={(200, "image/jpeg"): bytes})
    @action(detail=True, methods=["get"])
    def comprovante(self, request, pk=None):
        """A imagem do Pix — fora de /media/, só para a própria loja."""
        pedido = self.get_object()
        if not pedido.comprovante:
            raise Http404("Pedido sem comprovante.")
        resposta = FileResponse(pedido.comprovante.open("rb"), content_type="image/jpeg")
        resposta["Cache-Control"] = "private, no-store"
        return resposta
