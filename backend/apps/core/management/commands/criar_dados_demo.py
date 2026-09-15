"""
Popula uma loja de demonstração com dados realistas.

Serve para a URL pública de demonstração e para desenvolvimento: sem catálogo
e sem histórico, o dashboard e os relatórios ficam vazios e não dá para
avaliar o sistema.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.core.exceptions import ErroDeNegocio
from apps.estoque.models import TipoMovimento
from apps.estoque.servicos import registrar_movimento
from apps.financeiro.models import CategoriaFinanceira, Lancamento, StatusLancamento, TipoLancamento
from apps.fornecedores.models import Fornecedor
from apps.lojas.models import ConfiguracaoLoja, Loja
from apps.produtos.models import Categoria, Marca, Produto, TipoProduto, Variacao
from apps.usuarios.models import Papel, Usuario
from apps.vendas.models import FormaPagamento, StatusVenda
from apps.vendas.servicos import abrir_caixa, criar_venda, fechar_caixa, finalizar_venda

CATALOGO = [
    # (marca, produto, tipo, categoria, custo, venda, [sabores], puffs)
    ("Elf Bar", "Elf Bar BC10000", TipoProduto.DESCARTAVEL, "Descartáveis",
     "38.00", "75.00", ["Blue Razz Ice", "Watermelon Bubblegum", "Strawberry Mango"], 10000),
    ("Elf Bar", "Elf Bar Ice King 30000", TipoProduto.DESCARTAVEL, "Descartáveis",
     "62.00", "120.00", ["Cherry Cola", "Miami Mint"], 30000),
    ("Ignite", "Ignite V150", TipoProduto.DESCARTAVEL, "Descartáveis",
     "55.00", "110.00", ["Grape Ice", "Peach Mango"], 15000),
    ("Oxbar", "Oxbar Magic Maze Pro", TipoProduto.DESCARTAVEL, "Descartáveis",
     "70.00", "135.00", ["Blueberry Storm", "Lemon Mint"], 30000),
    ("Lost Mary", "Lost Mary MO20000", TipoProduto.DESCARTAVEL, "Descartáveis",
     "58.00", "115.00", ["Triple Berry", "Kiwi Passion"], 20000),
    ("Nasty Juice", "Nasty Juice Salt 30ml", TipoProduto.LIQUIDO, "Líquidos",
     "22.00", "50.00", ["Cush Man", "Slow Blow"], None),
    ("Vaporesso", "Vaporesso XROS 4", TipoProduto.POD, "Pods recarregáveis",
     "95.00", "180.00", ["Preto", "Prata"], None),
    ("Vaporesso", "Resistência XROS 0.8Ω", TipoProduto.RESISTENCIA, "Resistências",
     "12.00", "28.00", ["Unitária"], None),
    ("Genérico", "Carregador USB-C", TipoProduto.ACESSORIO, "Acessórios",
     "8.00", "25.00", ["Padrão"], None),
]

NOMES_CLIENTES = [
    "Ana Beatriz Souza", "Carlos Eduardo Lima", "Daniela Martins", "Eduardo Ramos",
    "Fernanda Alves", "Gabriel Torres", "Helena Costa", "Igor Nascimento",
    "Juliana Prado", "Lucas Ferreira", "Mariana Rocha", "Nicolas Batista",
]


class Command(BaseCommand):
    help = "Cria (ou recria) a loja de demonstração com catálogo, estoque e histórico de vendas."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo@vapeproject.app",
                            help="E-mail do usuário dono da demonstração.")
        parser.add_argument("--senha", default="Demo@2026",
                            help="Senha do usuário de demonstração.")
        parser.add_argument("--loja", default="Vape Store Demo", help="Nome da loja.")
        parser.add_argument("--dias", type=int, default=45,
                            help="Quantos dias de histórico de vendas gerar.")
        parser.add_argument("--recriar", action="store_true",
                            help="Apaga a loja de demonstração existente antes de criar.")

    @transaction.atomic
    def handle(self, *args, **opcoes):
        random.seed(42)  # histórico reproduzível entre execuções
        nome_loja = opcoes["loja"]

        if opcoes["recriar"]:
            self._apagar(nome_loja)

        if Loja.objects.filter(nome=nome_loja).exists():
            self.stdout.write(self.style.WARNING(
                f"A loja “{nome_loja}” já existe. Use --recriar para refazê-la."
            ))
            return

        loja = Loja.objects.create(nome=nome_loja, telefone="(11) 98888-0000",
                                   cidade="São Paulo", uf="SP", limite_usuarios=10)
        ConfiguracaoLoja.objects.create(loja=loja, permitir_fiado=True)

        dono = Usuario.objects.create_user(
            email=opcoes["email"], password=opcoes["senha"], nome="Dono da Demo",
            loja=loja, papel=Papel.DONO,
        )
        vendedor = Usuario.objects.create_user(
            email=f"vendedor.{loja.slug}@vapeproject.app", password=opcoes["senha"],
            nome="Vendedor da Demo", loja=loja, papel=Papel.VENDEDOR,
        )

        variacoes = self._criar_catalogo(loja)
        self._criar_fornecedores_e_entradas(loja, dono, variacoes)
        clientes = self._criar_clientes(loja)
        self._criar_historico(loja, dono, vendedor, variacoes, clientes, opcoes["dias"])
        self._criar_financeiro(loja)

        self.stdout.write(self.style.SUCCESS(
            f"\nLoja de demonstração pronta.\n"
            f"  Loja .......: {loja.nome} (slug {loja.slug})\n"
            f"  Login ......: {opcoes['email']}\n"
            f"  Senha ......: {opcoes['senha']}\n"
            f"  Produtos ...: {Produto.objects.filter(loja=loja).count()}\n"
            f"  Variações ..: {len(variacoes)}\n"
            f"  Clientes ...: {len(clientes)}\n"
            f"  Vendas .....: {loja.vendas.filter(status=StatusVenda.FINALIZADA).count()}\n"
        ))

    # ------------------------------------------------------------------

    def _apagar(self, nome_loja):
        """Remove a loja e tudo que pende dela, na ordem que as FKs permitem."""
        loja = Loja.objects.filter(nome=nome_loja).first()
        if not loja:
            return

        from apps.estoque.models import MovimentoEstoque
        from apps.fornecedores.models import Compra, ItemCompra
        from apps.vendas.models import Caixa, ItemVenda, MovimentoCaixa, Pagamento, Venda

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
        self.stdout.write("Loja de demonstração anterior removida.")

    def _criar_catalogo(self, loja):
        categorias, marcas, variacoes = {}, {}, []

        for (marca_nome, produto_nome, tipo, categoria_nome,
             custo, venda, sabores, puffs) in CATALOGO:
            categoria = categorias.get(categoria_nome) or Categoria.objects.create(
                loja=loja, nome=categoria_nome
            )
            categorias[categoria_nome] = categoria

            marca = marcas.get(marca_nome) or Marca.objects.create(loja=loja, nome=marca_nome)
            marcas[marca_nome] = marca

            produto = Produto.objects.create(
                loja=loja, nome=produto_nome, tipo=tipo, categoria=categoria, marca=marca
            )
            for indice, sabor in enumerate(sabores, start=1):
                variacoes.append(Variacao.objects.create(
                    loja=loja, produto=produto, sabor=sabor, puffs=puffs,
                    nicotina_mg=Decimal("5.00") if tipo in (
                        TipoProduto.DESCARTAVEL, TipoProduto.LIQUIDO) else None,
                    sku=f"{marca_nome[:3].upper()}-{produto.id}-{indice}",
                    codigo_barras=f"789{produto.id:04d}{indice:03d}",
                    preco_custo=Decimal(custo), preco_venda=Decimal(venda),
                    estoque_minimo=5,
                ))
        return variacoes

    def _criar_fornecedores_e_entradas(self, loja, usuario, variacoes):
        for nome, cidade in [("Distribuidora Vapor SP", "São Paulo"),
                             ("Import Vape Brasil", "Curitiba")]:
            Fornecedor.objects.create(loja=loja, nome=nome, cidade=cidade,
                                      telefone="(11) 3333-4444")

        for variacao in variacoes:
            registrar_movimento(
                variacao=variacao, tipo=TipoMovimento.ENTRADA,
                quantidade=random.randint(25, 60), usuario=usuario,
                custo_unitario=variacao.preco_custo, motivo="Carga inicial de estoque",
                documento="NF 1000",
            )

    def _criar_clientes(self, loja):
        hoje = timezone.localdate()
        clientes = []
        for indice, nome in enumerate(NOMES_CLIENTES):
            clientes.append(Cliente.objects.create(
                loja=loja, nome=nome,
                telefone=f"(11) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
                data_nascimento=hoje - timedelta(days=365 * random.randint(19, 45)),
                limite_credito=Decimal("300.00") if indice % 3 == 0 else Decimal("0.00"),
                cidade="São Paulo",
            ))
        return clientes

    def _criar_historico(self, loja, dono, vendedor, variacoes, clientes, dias):
        """
        Gera vendas retroativas.

        As datas são reescritas depois de finalizar, porque os serviços sempre
        carimbam `timezone.now()` — e um histórico todo no mesmo dia deixaria
        os gráficos sem sentido.
        """
        from apps.vendas.models import Venda

        agora = timezone.now()
        vendas_criadas = []

        caixa = abrir_caixa(loja=loja, usuario=dono, saldo_inicial=Decimal("200.00"))

        # O range chega a 0 para que a demonstração tenha vendas de hoje —
        # um painel abrindo em “Vendas hoje: R$ 0,00” parece sistema morto.
        for dia_atras in range(dias, -1, -1):
            data = agora - timedelta(days=dia_atras)

            # Reposição semanal: sem ela o estoque inicial acaba na metade do
            # período e as vendas seguintes falham, deixando a demonstração
            # com prateleira vazia e gráfico truncado — o oposto do que uma
            # loja em operação parece.
            if dia_atras % 7 == 0:
                self._repor_estoque(variacoes, dono)

            # Fim de semana vende mais — dá forma ao gráfico.
            quantidade_vendas = (
                random.randint(4, 9) if data.weekday() >= 5 else random.randint(2, 6)
            )

            for _ in range(quantidade_vendas):
                itens = [
                    {"variacao": variacao, "quantidade": random.randint(1, 3)}
                    for variacao in random.sample(variacoes, random.randint(1, 3))
                ]
                cliente = random.choice(clientes) if random.random() < 0.4 else None
                vendedor_da_vez = vendedor if random.random() < 0.6 else dono

                venda = None
                try:
                    venda = criar_venda(
                        loja=loja, usuario=vendedor_da_vez, cliente=cliente, itens=itens
                    )
                    # Cliente com limite às vezes leva fiado: sem isso o
                    # painel mostraria “a receber R$ 0,00” e o módulo de
                    # crediário ficaria invisível na demonstração.
                    pode_fiar = (
                        cliente is not None
                        and cliente.limite_credito > 0
                        and dia_atras < 20
                        and random.random() < 0.25
                    )
                    forma = (
                        FormaPagamento.FIADO
                        if pode_fiar
                        else random.choices(
                            [FormaPagamento.DINHEIRO, FormaPagamento.PIX,
                             FormaPagamento.DEBITO, FormaPagamento.CREDITO],
                            weights=[25, 40, 20, 15],
                        )[0]
                    )
                    finalizar_venda(
                        venda=venda, usuario=vendedor_da_vez,
                        pagamentos=[{"forma": forma, "valor": venda.total}],
                    )
                    vendas_criadas.append((venda.id, data))
                except ErroDeNegocio:
                    # O estoque daquela variação acabou. A venda já criada
                    # precisa sumir, senão fica aberta e trava o fechamento
                    # do caixa no fim deste método.
                    if venda is not None and venda.pk:
                        venda.itens.all().delete()
                        venda.delete()
                    continue

        # Reescreve as datas para espalhar o histórico no calendário.
        #
        # Os lançamentos financeiros entram junto: eles são criados com a data
        # de hoje pelo serviço de venda, e sem este ajuste todo o faturamento
        # de dois meses apareceria empilhado num único dia do fluxo de caixa.
        from apps.financeiro.models import Lancamento

        for venda_id, data in vendas_criadas:
            Venda.objects.filter(id=venda_id).update(criado_em=data, finalizada_em=data)
            dia = data.date()
            # Recebidos vencem e são baixados no dia da venda; o fiado mantém
            # o prazo da loja contado a partir da data real da venda.
            Lancamento.objects.filter(venda_id=venda_id, pago_em__isnull=False).update(
                vencimento=dia, pago_em=dia, criado_em=data
            )
            Lancamento.objects.filter(venda_id=venda_id, pago_em__isnull=True).update(
                vencimento=dia + timedelta(days=30), criado_em=data
            )

        fechar_caixa(caixa=caixa, usuario=dono, saldo_informado=Decimal("0.00"),
                     observacoes="Fechamento do histórico de demonstração.")
        # Deixa um caixa aberto para a demonstração já permitir vender.
        abrir_caixa(loja=loja, usuario=dono, saldo_inicial=Decimal("200.00"))

    def _repor_estoque(self, variacoes, usuario):
        """Repõe o que está abaixo do mínimo, como faria a compra semanal."""
        for variacao in variacoes:
            variacao.refresh_from_db()
            if variacao.saldo > 12:
                continue
            registrar_movimento(
                variacao=variacao,
                tipo=TipoMovimento.ENTRADA,
                quantidade=random.randint(20, 45),
                usuario=usuario,
                custo_unitario=variacao.preco_custo,
                motivo="Reposição semanal",
                documento="NF série D",
            )

    def _criar_financeiro(self, loja):
        hoje = timezone.localdate()
        despesas, _ = CategoriaFinanceira.objects.get_or_create(
            loja=loja, nome="Despesas fixas", defaults={"tipo": TipoLancamento.DESPESA}
        )
        for descricao, valor, dias in [
            ("Aluguel da loja", "2500.00", 5),
            ("Energia elétrica", "480.00", 12),
            ("Internet", "150.00", 8),
            ("Salário — vendedor", "1800.00", 20),
        ]:
            Lancamento.objects.create(
                loja=loja, tipo=TipoLancamento.DESPESA, categoria=despesas,
                descricao=descricao, valor=Decimal(valor),
                vencimento=hoje + timedelta(days=dias), status=StatusLancamento.PENDENTE,
            )
        # Uma conta vencida, para o painel mostrar o alerta de atraso.
        Lancamento.objects.create(
            loja=loja, tipo=TipoLancamento.DESPESA, categoria=despesas,
            descricao="Manutenção do ar-condicionado", valor=Decimal("320.00"),
            vencimento=hoje - timedelta(days=4), status=StatusLancamento.PENDENTE,
        )
