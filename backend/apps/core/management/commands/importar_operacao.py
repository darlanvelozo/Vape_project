"""
Importa a operação inicial de uma loja a partir de um arquivo JSON.

Serve para colocar no sistema o que a loja já tinha antes de começar a usá-lo:
catálogo, compras e vendas passadas. Tudo passa pelos serviços de domínio
(`estoque.servicos`, `vendas.servicos`, `fornecedores.servicos`), então o
resultado é indistinguível de uma operação digitada no dia a dia — saldo,
custo médio, caixa e financeiro ficam consistentes.

Os eventos são processados em **ordem cronológica**, misturando compras e
vendas. Processar todas as compras antes das vendas inflaria o estoque e
estragaria o custo médio.

O arquivo de dados fica fora do repositório (`dados/` está no .gitignore),
porque contém informação comercial da loja.

Uso:
    manage.py importar_operacao dados/minha-loja.json
    manage.py importar_operacao dados/minha-loja.json --recriar
    manage.py importar_operacao dados/minha-loja.json --conferir
"""

import json
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.core.exceptions import ErroDeNegocio
from apps.estoque.models import MovimentoEstoque
from apps.financeiro.models import CategoriaFinanceira, Lancamento
from apps.fornecedores.models import Compra, Fornecedor, ItemCompra, StatusCompra
from apps.fornecedores.servicos import receber_compra
from apps.lojas.models import ConfiguracaoLoja, Loja
from apps.produtos.models import Categoria, Marca, Produto, Variacao
from apps.usuarios.models import Papel, Usuario
from apps.vendas.models import (
    Caixa,
    ItemVenda,
    MovimentoCaixa,
    Pagamento,
    StatusVenda,
    Venda,
)
from apps.vendas.servicos import abrir_caixa, criar_venda, fechar_caixa, finalizar_venda

# Horários em que as vendas do dia são distribuídas, para o histórico não
# ficar todo carimbado na mesma hora.
HORARIOS = [time(10, 30), time(12, 15), time(14, 40), time(16, 20),
            time(17, 50), time(19, 10), time(20, 30)]


class Command(BaseCommand):
    help = "Importa a operação inicial de uma loja (catálogo, compras e vendas) de um JSON."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="Caminho do JSON com os dados da loja.")
        parser.add_argument(
            "--recriar", action="store_true",
            help="Apaga a loja de mesmo nome antes de importar. DESTRUTIVO.",
        )
        parser.add_argument(
            "--conferir", action="store_true",
            help="Valida o arquivo e mostra os totais, sem gravar nada.",
        )

    def handle(self, *args, **opcoes):
        caminho = Path(opcoes["arquivo"])
        if not caminho.exists():
            raise CommandError(f"Arquivo não encontrado: {caminho}")

        dados = json.loads(caminho.read_text(encoding="utf-8"))
        self._validar(dados)

        if opcoes["conferir"]:
            self._mostrar_conferencia(dados)
            return

        with transaction.atomic():
            self._importar(dados, recriar=opcoes["recriar"])

    # ------------------------------------------------------------------
    # Validação
    # ------------------------------------------------------------------

    def _validar(self, dados):
        """Erro de digitação no arquivo tem que aparecer antes de gravar."""
        for chave in ("loja", "usuario", "produtos"):
            if chave not in dados:
                raise CommandError(f"O arquivo não tem a seção obrigatória “{chave}”.")

        catalogo = self._indice_do_catalogo(dados["produtos"])

        for secao in ("compras", "vendas"):
            for evento in dados.get(secao, []):
                if "data" not in evento:
                    raise CommandError(f"Há um item em “{secao}” sem data.")
                for item in evento.get("itens", []):
                    chave = (item["produto"], item.get("sabor", ""))
                    if chave not in catalogo:
                        raise CommandError(
                            f"{secao}: “{item['produto']} / {item.get('sabor', '')}” "
                            "não está na seção produtos."
                        )

        conferencia = dados.get("conferencia")
        if not conferencia:
            return

        totais = self._totais(dados)
        for campo, esperado in conferencia.items():
            obtido = totais.get(campo)
            if obtido is None:
                continue
            if Decimal(str(esperado)) != obtido:
                raise CommandError(
                    f"Conferência falhou em “{campo}”: o arquivo diz {esperado}, "
                    f"mas a soma dos lançamentos dá {obtido}."
                )

    def _totais(self, dados) -> dict:
        total_compras = sum(
            (Decimal(str(item["custo_unitario"])) * item["quantidade"]
             for compra in dados.get("compras", []) for item in compra["itens"]),
            Decimal("0.00"),
        )
        total_vendas = sum(
            (Decimal(str(item["preco_unitario"])) * item["quantidade"]
             for venda in dados.get("vendas", []) for item in venda["itens"]),
            Decimal("0.00"),
        )
        comprado = sum(
            item["quantidade"]
            for compra in dados.get("compras", []) for item in compra["itens"]
        )
        vendido = sum(
            item["quantidade"]
            for venda in dados.get("vendas", []) for item in venda["itens"]
        )
        return {
            "total_compras": total_compras,
            "total_vendas": total_vendas,
            "unidades_compradas": Decimal(comprado),
            "unidades_vendidas": Decimal(vendido),
            "unidades_em_estoque": Decimal(comprado - vendido),
        }

    def _mostrar_conferencia(self, dados):
        totais = self._totais(dados)
        self.stdout.write(self.style.WARNING("Conferência (nada foi gravado):\n"))
        self.stdout.write(f"  Unidades compradas ..: {int(totais['unidades_compradas'])}")
        self.stdout.write(f"  Unidades vendidas ...: {int(totais['unidades_vendidas'])}")
        self.stdout.write(f"  Em estoque ..........: {int(totais['unidades_em_estoque'])}")
        self.stdout.write(f"  Total das compras ...: R$ {totais['total_compras']}")
        self.stdout.write(f"  Total das vendas ....: R$ {totais['total_vendas']}")
        self.stdout.write(
            f"  Resultado ...........: R$ {totais['total_vendas'] - totais['total_compras']}"
        )

    @staticmethod
    def _indice_do_catalogo(produtos):
        return {
            (produto["nome"], variacao.get("sabor", "")): variacao
            for produto in produtos
            for variacao in produto["variacoes"]
        }

    # ------------------------------------------------------------------
    # Importação
    # ------------------------------------------------------------------

    def _importar(self, dados, *, recriar):
        nome_loja = dados["loja"]["nome"]

        if recriar:
            self._apagar(nome_loja)
        elif Loja.objects.filter(nome=nome_loja).exists():
            raise CommandError(
                f"A loja “{nome_loja}” já existe. Use --recriar para refazê-la."
            )

        loja = Loja.objects.create(**dados["loja"])
        ConfiguracaoLoja.objects.create(loja=loja, **dados.get("configuracao", {}))

        usuario = Usuario.objects.create_user(
            email=dados["usuario"]["email"],
            password=dados["usuario"]["senha"],
            nome=dados["usuario"]["nome"],
            telefone=dados["usuario"].get("telefone", ""),
            loja=loja,
            papel=Papel.DONO,
        )

        # Equipe adicional. Fica no arquivo para que um `--recriar` não apague
        # os acessos dos sócios e vendedores junto com o histórico.
        for membro in dados.get("equipe", []):
            Usuario.objects.create_user(
                email=membro["email"],
                password=membro["senha"],
                nome=membro["nome"],
                telefone=membro.get("telefone", ""),
                loja=loja,
                papel=membro.get("papel", Papel.VENDEDOR),
            )

        variacoes = self._criar_catalogo(loja, dados["produtos"])
        fornecedores = {
            self._nome_do_fornecedor(entrada): Fornecedor.objects.create(
                loja=loja,
                **({"nome": entrada} if isinstance(entrada, str) else entrada),
            )
            for entrada in dados.get("fornecedores", [])
        }
        clientes = {
            cliente["nome"]: Cliente.objects.create(loja=loja, **cliente)
            for cliente in dados.get("clientes", [])
        }

        self._processar_linha_do_tempo(
            loja=loja, usuario=usuario, dados=dados,
            variacoes=variacoes, fornecedores=fornecedores, clientes=clientes,
        )

        self._relatorio(loja, dados)

    @staticmethod
    def _variacao(variacoes, item):
        """
        Busca a variação **do banco**, sempre.

        O custo médio muda a cada compra recebida; reaproveitar a instância
        criada no catálogo faria a venda gravar um custo desatualizado no
        snapshot do item — e a margem sairia errada para sempre.
        """
        return Variacao.objects.get(pk=variacoes[(item["produto"], item.get("sabor", ""))])

    @staticmethod
    def _nome_do_fornecedor(entrada):
        """A seção aceita tanto "Nome" quanto {"nome": ..., "telefone": ...}."""
        return entrada if isinstance(entrada, str) else entrada["nome"]

    def _criar_catalogo(self, loja, produtos):
        categorias, marcas = {}, {}
        variacoes = {}

        for dados_produto in produtos:
            nome_categoria = dados_produto.get("categoria")
            categoria = None
            if nome_categoria:
                categoria = categorias.get(nome_categoria) or Categoria.objects.create(
                    loja=loja, nome=nome_categoria
                )
                categorias[nome_categoria] = categoria

            nome_marca = dados_produto.get("marca")
            marca = None
            if nome_marca:
                marca = marcas.get(nome_marca) or Marca.objects.create(loja=loja, nome=nome_marca)
                marcas[nome_marca] = marca

            produto = Produto.objects.create(
                loja=loja,
                nome=dados_produto["nome"],
                descricao=dados_produto.get("descricao", ""),
                tipo=dados_produto.get("tipo", "descartavel"),
                categoria=categoria,
                marca=marca,
            )

            for dados_variacao in dados_produto["variacoes"]:
                variacao = Variacao.objects.create(
                    loja=loja,
                    produto=produto,
                    sabor=dados_variacao.get("sabor", ""),
                    nicotina_mg=dados_variacao.get("nicotina_mg"),
                    puffs=dados_variacao.get("puffs"),
                    sku=dados_variacao.get("sku", ""),
                    codigo_barras=dados_variacao.get("codigo_barras", ""),
                    # O custo definitivo vem do custo médio das entradas; este
                    # é só o ponto de partida antes da primeira compra.
                    preco_custo=Decimal(str(dados_variacao.get("preco_custo", "0.00"))),
                    preco_venda=Decimal(str(dados_variacao["preco_venda"])),
                    estoque_minimo=dados_variacao.get("estoque_minimo", 0),
                )
                variacoes[(produto.nome, variacao.sabor)] = variacao.pk

        return variacoes

    def _processar_linha_do_tempo(self, *, loja, usuario, dados, variacoes,
                                  fornecedores, clientes):
        """
        Aplica compras e vendas em ordem cronológica.

        A ordem importa duas vezes: o custo médio depende de qual entrada veio
        antes, e o saldo não pode ficar negativo por processar uma venda antes
        da compra que a abasteceu.
        """
        eventos = []
        for compra in dados.get("compras", []):
            eventos.append((compra["data"], "compra", compra))
        for venda in dados.get("vendas", []):
            eventos.append((venda["data"], "venda", venda))
        eventos.sort(key=lambda evento: (evento[0], evento[1] != "compra"))

        vendas_por_dia = defaultdict(list)
        for data, tipo, evento in eventos:
            if tipo == "venda":
                vendas_por_dia[data].append(evento)

        dias_processados = set()

        for data, tipo, evento in eventos:
            if tipo == "compra":
                self._importar_compra(
                    loja=loja, usuario=usuario, compra=evento,
                    variacoes=variacoes, fornecedores=fornecedores,
                )
            elif data not in dias_processados:
                # Um caixa por dia de venda, aberto e fechado como na operação
                # real — é isso que dá ao lojista o histórico de conferência.
                dias_processados.add(data)
                self._importar_dia_de_vendas(
                    loja=loja, usuario=usuario, data=data,
                    vendas=vendas_por_dia[data], variacoes=variacoes, clientes=clientes,
                )

    def _importar_compra(self, *, loja, usuario, compra, variacoes, fornecedores):
        nome_fornecedor = compra.get("fornecedor")
        fornecedor = fornecedores.get(nome_fornecedor)
        if fornecedor is None:
            raise CommandError(f"Fornecedor “{nome_fornecedor}” não está na seção fornecedores.")

        data = datetime.strptime(compra["data"], "%Y-%m-%d").date()
        registro = Compra.objects.create(
            loja=loja,
            fornecedor=fornecedor,
            numero_documento=compra.get("documento", ""),
            data=data,
            status=StatusCompra.RASCUNHO,
            frete=Decimal(str(compra.get("frete", "0.00"))),
            desconto=Decimal(str(compra.get("desconto", "0.00"))),
            vencimento=compra.get("vencimento"),
            observacoes=compra.get("observacoes", ""),
            usuario=usuario,
        )
        for item in compra["itens"]:
            ItemCompra.objects.create(
                compra=registro,
                variacao=self._variacao(variacoes, item),
                quantidade=item["quantidade"],
                custo_unitario=Decimal(str(item["custo_unitario"])),
            )

        receber_compra(compra=registro, usuario=usuario)
        self._carimbar_compra(registro, self._momento(data, 0))

    def _importar_dia_de_vendas(self, *, loja, usuario, data, vendas, variacoes, clientes):
        dia = datetime.strptime(data, "%Y-%m-%d").date()
        caixa = abrir_caixa(loja=loja, usuario=usuario, saldo_inicial=Decimal("0.00"))

        for indice, dados_venda in enumerate(vendas):
            momento = self._momento(dia, indice)
            itens = [
                {
                    "variacao": self._variacao(variacoes, item),
                    "quantidade": item["quantidade"],
                    "preco_unitario": Decimal(str(item["preco_unitario"])),
                }
                for item in dados_venda["itens"]
            ]
            cliente = clientes.get(dados_venda.get("cliente"))

            try:
                venda = criar_venda(
                    loja=loja, usuario=usuario, cliente=cliente, itens=itens,
                    desconto=Decimal(str(dados_venda.get("desconto", "0.00"))),
                    observacoes=dados_venda.get("observacoes", ""),
                )
                total = venda.total
                finalizar_venda(
                    venda=venda, usuario=usuario,
                    pagamentos=[{
                        "forma": dados_venda.get("forma_pagamento", "dinheiro"),
                        "valor": total,
                    }],
                )
            except ErroDeNegocio as erro:
                raise CommandError(f"Venda de {data} recusada: {erro}") from erro

            self._carimbar_venda(venda, momento)

        fechamento = self._momento(dia, len(vendas) + 1)
        saldo = sum(
            (movimento.valor_com_sinal for movimento in caixa.movimentos.all()),
            Decimal("0.00"),
        )
        fechar_caixa(
            caixa=caixa, usuario=usuario, saldo_informado=saldo,
            observacoes="Fechamento importado do histórico da loja.",
        )
        Caixa.objects.filter(pk=caixa.pk).update(
            aberto_em=self._momento(dia, 0) - timedelta(minutes=30),
            fechado_em=fechamento,
            criado_em=self._momento(dia, 0) - timedelta(minutes=30),
        )

    # ------------------------------------------------------------------
    # Carimbo de datas
    # ------------------------------------------------------------------

    @staticmethod
    def _momento(dia, indice):
        """Data e hora plausíveis para o n-ésimo evento do dia."""
        horario = HORARIOS[indice % len(HORARIOS)]
        return timezone.make_aware(datetime.combine(dia, horario))

    def _carimbar_compra(self, compra, momento):
        Compra.objects.filter(pk=compra.pk).update(criado_em=momento, recebida_em=momento)
        MovimentoEstoque.objects.filter(compra=compra).update(criado_em=momento)
        Lancamento.objects.filter(compra=compra).update(criado_em=momento)

    def _carimbar_venda(self, venda, momento):
        """
        Reescreve para o passado tudo que a venda criou.

        Os serviços carimbam `timezone.now()` — sem isto, um histórico de duas
        semanas apareceria inteiro no dia da importação.
        """
        dia = momento.date()
        Venda.objects.filter(pk=venda.pk).update(
            criado_em=momento, finalizada_em=momento, atualizado_em=momento
        )
        MovimentoEstoque.objects.filter(venda=venda).update(criado_em=momento)
        MovimentoCaixa.objects.filter(venda=venda).update(criado_em=momento)
        Pagamento.objects.filter(venda=venda).update(criado_em=momento)
        # Recebido à vista vence e é baixado no dia; fiado mantém o prazo.
        Lancamento.objects.filter(venda=venda, pago_em__isnull=False).update(
            vencimento=dia, pago_em=dia, criado_em=momento
        )
        Lancamento.objects.filter(venda=venda, pago_em__isnull=True).update(criado_em=momento)

    # ------------------------------------------------------------------
    # Apagar e relatar
    # ------------------------------------------------------------------

    def _apagar(self, nome_loja):
        loja = Loja.objects.filter(nome=nome_loja).first()
        if not loja:
            return

        Lancamento.objects.filter(loja=loja).delete()
        MovimentoEstoque.objects.filter(loja=loja).delete()
        MovimentoCaixa.objects.filter(loja=loja).delete()
        Pagamento.objects.filter(venda__loja=loja).delete()
        ItemVenda.objects.filter(venda__loja=loja).delete()
        Venda.objects.filter(loja=loja).delete()
        Caixa.objects.filter(loja=loja).delete()
        ItemCompra.objects.filter(compra__loja=loja).delete()
        Compra.objects.filter(loja=loja).delete()
        Variacao.objects.filter(loja=loja).delete()
        Produto.objects.filter(loja=loja).delete()
        Categoria.objects.filter(loja=loja).delete()
        Marca.objects.filter(loja=loja).delete()
        Cliente.objects.filter(loja=loja).delete()
        Fornecedor.objects.filter(loja=loja).delete()
        CategoriaFinanceira.objects.filter(loja=loja).delete()
        Usuario.objects.filter(loja=loja).delete()
        ConfiguracaoLoja.objects.filter(loja=loja).delete()
        loja.delete()
        self.stdout.write(f"Loja “{nome_loja}” anterior removida.")

    def _relatorio(self, loja, dados):
        from django.db.models import Sum

        vendas = Venda.objects.filter(loja=loja, status=StatusVenda.FINALIZADA)
        faturamento = vendas.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        custo = vendas.aggregate(total=Sum("custo_total"))["total"] or Decimal("0.00")
        estoque = Variacao.objects.filter(loja=loja).aggregate(total=Sum("saldo"))["total"] or 0
        compras = Compra.objects.filter(loja=loja).aggregate(
            total=Sum("total")
        )["total"] or Decimal("0.00")

        valor_estoque = sum(
            (variacao.saldo * variacao.preco_custo
             for variacao in Variacao.objects.filter(loja=loja)),
            Decimal("0.00"),
        )

        acessos = ", ".join(
            f"{u.email} ({u.get_papel_display().lower()})"
            for u in Usuario.objects.filter(loja=loja).order_by("papel", "nome")
        )
        total_produtos = Produto.objects.filter(loja=loja).count()
        total_variacoes = Variacao.objects.filter(loja=loja).count()

        self.stdout.write(self.style.SUCCESS(f"""
Operação importada: {loja.nome}

  Acessos ................: {acessos}
  Produtos / variações ...: {total_produtos} / {total_variacoes}
  Compras registradas ....: {Compra.objects.filter(loja=loja).count()} — R$ {compras}
  Vendas registradas .....: {vendas.count()} — R$ {faturamento}
  Lucro realizado ........: R$ {faturamento - custo}
  Estoque atual ..........: {estoque} un. — R$ {valor_estoque.quantize(Decimal("0.01"))} a custo
"""))
