"""
Rotas da API.

Convenção: tudo sob `/api/`, **sempre com barra final** — é o que o
router do DRF gera, e um POST sem a barra viraria redirect 301 perdendo o
corpo da requisição. O Django Admin fica em `/admin/` e é ferramenta
de suporte — o lojista usa o frontend.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.clientes.views import ClienteViewSet
from apps.estoque.views import MovimentoEstoqueViewSet, PosicaoEstoqueViewSet
from apps.financeiro.views import CategoriaFinanceiraViewSet, LancamentoViewSet
from apps.fornecedores.views import CompraViewSet, FornecedorViewSet
from apps.lojas.views import VitrinePublicaView
from apps.pedidos.publico import (
    CancelarPedidoPublicoView,
    CriarPedidoPublicoView,
    InformarPagamentoPublicoView,
    MeusPedidosPublicoView,
    PedidoPublicoView,
)
from apps.pedidos.views import PedidoOnlineViewSet
from apps.produtos.views import CategoriaViewSet, MarcaViewSet, ProdutoViewSet, VariacaoViewSet
from apps.relatorios.views import (
    CurvaABCView,
    DashboardView,
    GiroDeEstoqueView,
    MaisVendidosView,
    MargemPorProdutoView,
    ResultadoView,
    VendasPorFormaPagamentoView,
    VendasPorPeriodoView,
    VendasPorVendedorView,
)
from apps.usuarios.views import (
    AlterarSenhaView,
    CadastroLojaView,
    ConfiguracaoLojaView,
    LoginView,
    MinhaLojaView,
    UsuarioAtualView,
    UsuarioViewSet,
)
from apps.vendas.views import CaixaViewSet, VendaViewSet

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("categorias", CategoriaViewSet, basename="categoria")
router.register("marcas", MarcaViewSet, basename="marca")
router.register("produtos", ProdutoViewSet, basename="produto")
router.register("variacoes", VariacaoViewSet, basename="variacao")
router.register("estoque/movimentos", MovimentoEstoqueViewSet, basename="movimento-estoque")
router.register("estoque/posicao", PosicaoEstoqueViewSet, basename="posicao-estoque")
router.register("clientes", ClienteViewSet, basename="cliente")
router.register("fornecedores", FornecedorViewSet, basename="fornecedor")
router.register("compras", CompraViewSet, basename="compra")
router.register("caixas", CaixaViewSet, basename="caixa")
router.register("vendas", VendaViewSet, basename="venda")
router.register("pedidos-online", PedidoOnlineViewSet, basename="pedido-online")
router.register(
    "financeiro/categorias", CategoriaFinanceiraViewSet, basename="categoria-financeira"
)
router.register("financeiro/lancamentos", LancamentoViewSet, basename="lancamento")

urlpatterns_autenticacao = [
    path("token/", LoginView.as_view(), name="login"),
    path("token/atualizar/", TokenRefreshView.as_view(), name="token-atualizar"),
    path("token/verificar/", TokenVerifyView.as_view(), name="token-verificar"),
    path("cadastrar/", CadastroLojaView.as_view(), name="cadastrar-loja"),
    path("eu/", UsuarioAtualView.as_view(), name="usuario-atual"),
    path("senha/", AlterarSenhaView.as_view(), name="alterar-senha"),
]

urlpatterns_relatorios = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("resultado/", ResultadoView.as_view(), name="resultado"),
    path("vendas-por-periodo/", VendasPorPeriodoView.as_view(), name="vendas-por-periodo"),
    path("mais-vendidos/", MaisVendidosView.as_view(), name="mais-vendidos"),
    path("curva-abc/", CurvaABCView.as_view(), name="curva-abc"),
    path("margem/", MargemPorProdutoView.as_view(), name="margem"),
    path("giro/", GiroDeEstoqueView.as_view(), name="giro"),
    path("formas-pagamento/", VendasPorFormaPagamentoView.as_view(), name="formas-pagamento"),
    path("vendedores/", VendasPorVendedorView.as_view(), name="vendedores"),
]

urlpatterns = [
    path("admin/", admin.site.urls),

    # Vitrine pública — único endpoint de domínio sem autenticação.
    path("api/vitrine/<slug:slug>/", VitrinePublicaView.as_view(), name="vitrine"),
    # Pedido on-line (ADR-0004): também sem autenticação, pelo token do pedido.
    path("api/vitrine/<slug:slug>/pedidos/", CriarPedidoPublicoView.as_view(),
         name="vitrine-criar-pedido"),
    path("api/vitrine/<slug:slug>/pedidos/<str:token>/", PedidoPublicoView.as_view(),
         name="vitrine-pedido"),
    path("api/vitrine/<slug:slug>/pedidos/<str:token>/pagamento/",
         InformarPagamentoPublicoView.as_view(), name="vitrine-pedido-pagamento"),
    path("api/vitrine/<slug:slug>/pedidos/<str:token>/cancelar/",
         CancelarPedidoPublicoView.as_view(), name="vitrine-pedido-cancelar"),
    path("api/vitrine/<slug:slug>/meus-pedidos/", MeusPedidosPublicoView.as_view(),
         name="vitrine-meus-pedidos"),

    path("api/auth/", include((urlpatterns_autenticacao, "auth"))),
    path("api/relatorios/", include((urlpatterns_relatorios, "relatorios"))),
    path("api/loja/", MinhaLojaView.as_view(), name="minha-loja"),
    path("api/loja/configuracao/", ConfiguracaoLojaView.as_view(), name="configuracao-loja"),
    path("api/", include(router.urls)),

    # Documentação da API
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
