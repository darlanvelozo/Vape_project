"""
Vitrine pública: a página sem senha que o cliente da loja abre.

É o único endpoint do sistema que responde sem autenticação e devolve dados
de uma loja. Por isso a regra aqui é de exposição mínima:

- só sai o que está **disponível** (variação ativa, produto ativo, saldo > 0);
- **nunca** sai custo, margem ou saldo exato — custo é segredo de compra e
  saldo exato entrega a operação ao concorrente. A tela mostra faixas
  ("última unidade", "poucas unidades", "disponível");
- a loja precisa ligar a vitrine explicitamente (`vitrine_publica`);
- há limite de requisições por IP, porque endpoint aberto é alvo de raspagem.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.utils import para_centavos
from apps.produtos.models import Variacao

from .models import Loja


def _disponibilidade(saldo: int) -> str:
    """Faixa de estoque em vez do número exato."""
    if saldo <= 1:
        return "ultima_unidade"
    if saldo <= 3:
        return "poucas_unidades"
    return "disponivel"


class VitrinePublicaView(APIView):
    """GET /api/vitrine/{slug}/ — catálogo disponível de uma loja, sem senha."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "vitrine"

    @extend_schema(
        responses=dict,
        description="Catálogo público de uma loja. Não exige autenticação.",
    )
    def get(self, request, slug):
        loja = Loja.objects.filter(slug=slug, ativa=True).select_related(
            "configuracao"
        ).first()
        configuracao = getattr(loja, "configuracao", None)

        # Loja inexistente, inativa e vitrine desligada devolvem o mesmo 404:
        # assim a URL não serve para descobrir quais lojas existem.
        if loja is None or configuracao is None or not configuracao.vitrine_publica:
            raise NotFound("Vitrine não encontrada.")

        variacoes = (
            Variacao.objects.filter(
                loja=loja, ativo=True, produto__ativo=True, saldo__gt=0
            )
            .select_related("produto", "produto__marca", "produto__categoria")
            .order_by("produto__nome", "sabor")
        )

        # Agrupa por produto para a tela montar um card por modelo.
        produtos: dict[int, dict] = {}
        for variacao in variacoes:
            produto = produtos.setdefault(
                variacao.produto_id,
                {
                    "nome": variacao.produto.nome,
                    "marca": variacao.produto.marca.nome if variacao.produto.marca else "",
                    "categoria": (
                        variacao.produto.categoria.nome
                        if variacao.produto.categoria else ""
                    ),
                    "descricao": variacao.produto.descricao,
                    "opcoes": [],
                },
            )
            opcao = {
                "sabor": variacao.sabor,
                "nicotina_mg": (
                    str(variacao.nicotina_mg.normalize())
                    if variacao.nicotina_mg is not None else None
                ),
                "puffs": variacao.puffs,
                "disponibilidade": _disponibilidade(variacao.saldo),
            }
            if configuracao.vitrine_mostrar_preco:
                opcao["preco_centavos"] = para_centavos(variacao.preco_venda)
            produto["opcoes"].append(opcao)

        return Response({
            "loja": {
                "nome": loja.nome,
                "cidade": loja.cidade,
                "uf": loja.uf,
                "whatsapp": configuracao.vitrine_whatsapp,
            },
            "mensagem": configuracao.vitrine_mensagem,
            "mostrar_preco": configuracao.vitrine_mostrar_preco,
            "produtos": list(produtos.values()),
            "total_itens": sum(len(p["opcoes"]) for p in produtos.values()),
            "aviso_idade": "Venda proibida para menores de 18 anos.",
        })
