from django.db.models import Count, Prefetch, Q
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.exceptions import ErroDeNegocio
from apps.core.permissions import LeituraParaTodosEscritaParaGestao
from apps.core.views import LojaViewSet

from .filters import ProdutoFilter, VariacaoFilter
from .models import Categoria, Marca, Produto, Variacao
from .serializers import (
    CategoriaSerializer,
    MarcaSerializer,
    PrecosDoModeloSerializer,
    ProdutoSerializer,
    VariacaoResumoSerializer,
    VariacaoSerializer,
)
from .servicos import aplicar_precos_ao_modelo


class CategoriaViewSet(LojaViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [LeituraParaTodosEscritaParaGestao]
    search_fields = ["nome"]
    filterset_fields = ["ativo"]

    def get_queryset(self):
        return super().get_queryset().annotate(total_produtos=Count("produtos"))


class MarcaViewSet(LojaViewSet):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer
    permission_classes = [LeituraParaTodosEscritaParaGestao]
    search_fields = ["nome"]
    filterset_fields = ["ativo"]

    def get_queryset(self):
        return super().get_queryset().annotate(total_produtos=Count("produtos"))


class ProdutoViewSet(LojaViewSet):
    queryset = Produto.objects.select_related("categoria", "marca")
    serializer_class = ProdutoSerializer
    permission_classes = [LeituraParaTodosEscritaParaGestao]
    # A foto sobe por multipart; o resto do cadastro continua em JSON.
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_class = ProdutoFilter
    search_fields = ["nome", "descricao", "variacoes__sku", "variacoes__codigo_barras",
                     "variacoes__sabor"]
    ordering_fields = ["nome", "criado_em"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(Prefetch("variacoes", queryset=Variacao.objects.order_by("sabor")))
            .distinct()
        )

    def perform_create(self, serializer):
        loja = self.loja
        if loja.atingiu_limite_de_produtos():
            raise ErroDeNegocio(
                f"O plano atual permite {loja.limite_produtos} produtos ativos.",
                campo="loja",
            )
        serializer.save(loja=loja)

    def perform_destroy(self, instancia):
        """
        Produto com histórico de venda não é excluído — é desativado.

        Excluir quebraria o histórico: o item de venda guarda FK para a
        variação (PROTECT).
        """
        tem_movimento = Variacao.objects.filter(
            produto=instancia
        ).filter(Q(itens_venda__isnull=False) | Q(movimentos__isnull=False)).exists()

        if tem_movimento:
            instancia.ativo = False
            instancia.save(update_fields=["ativo"])
            instancia.variacoes.update(ativo=False)
            return
        instancia.variacoes.all().delete()
        instancia.delete()

    @extend_schema(request=None, responses=ProdutoSerializer)
    @action(detail=True, methods=["delete"], url_path="imagem")
    def remover_imagem(self, request, pk=None):
        """
        DELETE /api/produtos/{id}/imagem — tira a foto do produto.

        Precisa de rota própria porque um PATCH multipart não consegue
        enviar `null`: o campo ausente é indistinguível de "não mexer".
        """
        produto = self.get_object()
        if produto.imagem:
            produto.imagem.delete(save=False)
            produto.imagem = None
            produto.save(update_fields=["imagem", "atualizado_em"])
        return Response(self.get_serializer(produto).data)

    @extend_schema(request=VariacaoSerializer, responses=VariacaoSerializer)
    @action(detail=True, methods=["post"], url_path="variacoes")
    def adicionar_variacao(self, request, pk=None):
        """POST /api/produtos/{id}/variacoes — nova variação do produto."""
        produto = self.get_object()
        contexto = {**self.get_serializer_context(), "produto": produto}
        serializer = VariacaoSerializer(data=request.data, context=contexto)
        serializer.is_valid(raise_exception=True)
        serializer.save(produto=produto, loja=self.loja)
        return Response(serializer.data, status=201)

    @extend_schema(request=PrecosDoModeloSerializer, responses=ProdutoSerializer)
    @action(detail=True, methods=["post"], url_path="precos")
    def precos(self, request, pk=None):
        """
        POST /api/produtos/{id}/precos — mesmo custo e/ou venda em todos os sabores.

        Responde o produto atualizado e, em `variacoes_alteradas`, quantos
        sabores mudaram de fato, para a tela confirmar o que aconteceu.
        """
        produto = self.get_object()
        entrada = PrecosDoModeloSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        alteradas = aplicar_precos_ao_modelo(
            produto=produto,
            preco_custo=entrada.validated_data.get("preco_custo_centavos"),
            preco_venda=entrada.validated_data.get("preco_venda_centavos"),
        )
        produto = self.get_queryset().get(pk=produto.pk)
        return Response({**self.get_serializer(produto).data, "variacoes_alteradas": alteradas})


class VariacaoViewSet(LojaViewSet):
    """
    Variações — é o que o PDV consulta e o que tem saldo.

    A busca aceita nome do produto, sabor, SKU e código de barras, porque no
    balcão o vendedor digita qualquer um dos quatro.
    """

    queryset = Variacao.objects.select_related("produto", "produto__categoria", "produto__marca")
    serializer_class = VariacaoSerializer
    permission_classes = [LeituraParaTodosEscritaParaGestao]
    filterset_class = VariacaoFilter
    search_fields = ["produto__nome", "sabor", "sku", "codigo_barras"]
    ordering_fields = ["produto__nome", "sabor", "saldo", "preco_venda"]

    def get_serializer_class(self):
        if self.action in ("list", "busca_pdv"):
            return VariacaoResumoSerializer
        return VariacaoSerializer

    @extend_schema(responses=VariacaoResumoSerializer(many=True))
    @action(detail=False, methods=["get"], url_path="busca-pdv")
    def busca_pdv(self, request):
        """
        GET /api/variacoes/busca-pdv?q=... — busca rápida do balcão.

        Código de barras exato vem primeiro: leitor de código de barras deve
        cair direto no item certo, sem lista intermediária.
        """
        termo = (request.query_params.get("q") or "").strip()
        base = self.get_queryset().filter(ativo=True, produto__ativo=True)

        if not termo:
            return Response(VariacaoResumoSerializer(base[:20], many=True).data)

        exato = base.filter(Q(codigo_barras=termo) | Q(sku__iexact=termo))
        if exato.exists():
            return Response(VariacaoResumoSerializer(exato[:20], many=True).data)

        resultados = base.filter(
            Q(produto__nome__icontains=termo)
            | Q(sabor__icontains=termo)
            | Q(sku__icontains=termo)
            | Q(codigo_barras__icontains=termo)
        )[:30]
        return Response(VariacaoResumoSerializer(resultados, many=True).data)
