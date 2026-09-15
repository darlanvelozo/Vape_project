from django.db.models import Count, Q, Sum
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import PertenceALoja
from apps.core.utils import para_centavos
from apps.core.views import LojaViewSet

from .models import Cliente
from .serializers import ClienteResumoSerializer, ClienteSerializer


class ClienteViewSet(LojaViewSet):
    """
    Clientes. O vendedor pode cadastrar no balcão — é o fluxo natural do PDV,
    então aqui não restringimos escrita a dono/gerente.
    """

    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [PertenceALoja]
    search_fields = ["nome", "telefone", "cpf", "email"]
    filterset_fields = ["ativo", "cidade"]
    ordering_fields = ["nome", "criado_em"]

    def get_serializer_class(self):
        if self.action == "busca":
            return ClienteResumoSerializer
        return ClienteSerializer

    def perform_destroy(self, instancia):
        """Cliente com histórico é desativado, não excluído."""
        if instancia.vendas.exists() or instancia.lancamentos.exists():
            instancia.ativo = False
            instancia.save(update_fields=["ativo"])
            return
        instancia.delete()

    @extend_schema(responses=ClienteResumoSerializer(many=True))
    @action(detail=False, methods=["get"])
    def busca(self, request):
        """GET /api/clientes/busca?q=... — autocomplete do PDV."""
        termo = (request.query_params.get("q") or "").strip()
        base = self.get_queryset().filter(ativo=True)
        if termo:
            base = base.filter(
                Q(nome__icontains=termo) | Q(telefone__icontains=termo) | Q(cpf__icontains=termo)
            )
        return Response(ClienteResumoSerializer(base[:20], many=True).data)

    @extend_schema(responses=dict)
    @action(detail=True, methods=["get"])
    def historico(self, request, pk=None):
        """GET /api/clientes/{id}/historico — compras e saldo devedor."""
        from apps.vendas.models import StatusVenda
        from apps.vendas.serializers import VendaResumoSerializer

        cliente = self.get_object()
        vendas = cliente.vendas.filter(status=StatusVenda.FINALIZADA).order_by("-finalizada_em")

        agregado = vendas.aggregate(total=Sum("total"), quantidade=Count("id"))
        total = agregado["total"] or 0
        quantidade = agregado["quantidade"] or 0

        return Response({
            "cliente": ClienteSerializer(cliente).data,
            "total_compras": quantidade,
            "valor_total_centavos": para_centavos(total),
            "ticket_medio_centavos": para_centavos(total / quantidade) if quantidade else 0,
            "saldo_devedor_centavos": para_centavos(cliente.saldo_devedor),
            "ultimas_vendas": VendaResumoSerializer(vendas[:20], many=True).data,
        })
