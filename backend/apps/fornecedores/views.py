from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import EhDonoOuGerente, LeituraParaTodosEscritaParaGestao
from apps.core.views import LojaViewSet

from .models import Compra, Fornecedor
from .serializers import CancelarCompraSerializer, CompraSerializer, FornecedorSerializer
from .servicos import cancelar_compra, receber_compra


class FornecedorViewSet(LojaViewSet):
    queryset = Fornecedor.objects.all()
    serializer_class = FornecedorSerializer
    permission_classes = [LeituraParaTodosEscritaParaGestao]
    search_fields = ["nome", "cnpj", "contato", "telefone", "email"]
    filterset_fields = ["ativo", "cidade"]
    ordering_fields = ["nome", "criado_em"]

    def get_queryset(self):
        return super().get_queryset().annotate(total_compras=Count("compras"))

    def perform_destroy(self, instancia):
        if instancia.compras.exists():
            instancia.ativo = False
            instancia.save(update_fields=["ativo"])
            return
        instancia.delete()


class CompraViewSet(LojaViewSet):
    """
    Compras. Enquanto rascunho podem ser editadas; receber é irreversível
    (o cancelamento estorna, mas não volta ao rascunho).
    """

    queryset = Compra.objects.select_related("fornecedor", "usuario").prefetch_related(
        "itens__variacao__produto"
    )
    serializer_class = CompraSerializer
    permission_classes = [EhDonoOuGerente]
    filterset_fields = ["fornecedor", "status"]
    search_fields = ["numero_documento", "fornecedor__nome", "observacoes"]
    ordering_fields = ["data", "total", "criado_em"]

    def perform_create(self, serializer):
        serializer.save(loja=self.loja, usuario=self.request.user)

    def perform_destroy(self, instancia):
        from apps.core.exceptions import ErroDeNegocio

        if instancia.status != "rascunho":
            raise ErroDeNegocio(
                "Compra recebida não pode ser excluída — use o cancelamento, "
                "que estorna o estoque.",
                campo="status",
            )
        instancia.itens.all().delete()
        instancia.delete()

    @extend_schema(request=None, responses=CompraSerializer)
    @action(detail=True, methods=["post"])
    def receber(self, request, pk=None):
        """POST /api/compras/{id}/receber — dá entrada no estoque."""
        compra = receber_compra(compra=self.get_object(), usuario=request.user)
        return Response(self.get_serializer(compra).data)

    @extend_schema(request=CancelarCompraSerializer, responses=CompraSerializer)
    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """POST /api/compras/{id}/cancelar — cancela e estorna se necessário."""
        serializer = CancelarCompraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        compra = cancelar_compra(
            compra=self.get_object(),
            usuario=request.user,
            motivo=serializer.validated_data.get("motivo", ""),
        )
        return Response(self.get_serializer(compra).data)
