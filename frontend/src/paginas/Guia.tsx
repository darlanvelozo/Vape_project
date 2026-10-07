/**
 * Guia de uso — escrito para o lojista e a equipe do balcão, não para quem
 * desenvolve. A linguagem evita jargão: fala em "o que a loja ganhou" em vez
 * de "resultado do exercício", e explica o porquê de cada regra, porque uma
 * regra sem motivo é decorada errado.
 */

import {
  BarChart3, Boxes, ChevronRight, LayoutDashboard, Lightbulb, Package,
  Receipt, Settings, ShoppingCart, Store, Truck, Users, Wallet,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { CabecalhoPagina, Cartao } from '../componentes/ui'

type Icone = typeof LayoutDashboard

interface Secao {
  id: string
  titulo: string
  icone: Icone
  conteudo: ReactNode
}

/** Passo numerado de um procedimento. */
function Passos({ itens }: { itens: ReactNode[] }) {
  return (
    <ol className="mt-3 space-y-2.5">
      {itens.map((item, indice) => (
        <li key={indice} className="flex gap-3">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full
                           bg-marca-700 text-xs font-bold text-white">
            {indice + 1}
          </span>
          <span className="min-w-0 flex-1 pt-0.5 text-sm text-slate-700">{item}</span>
        </li>
      ))}
    </ol>
  )
}

/** Observação lateral: o porquê por trás de uma regra. */
function Nota({ children, tom = 'dica' }: { children: ReactNode; tom?: 'dica' | 'atencao' }) {
  const estilos = {
    dica: 'border-sky-200 bg-sky-50 text-sky-900',
    atencao: 'border-amber-200 bg-amber-50 text-amber-900',
  }
  return (
    <div className={`mt-3 flex gap-2 rounded-lg border px-3 py-2.5 text-sm ${estilos[tom]}`}>
      <Lightbulb size={16} className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}

function Paragrafo({ children }: { children: ReactNode }) {
  return <p className="mt-3 text-sm leading-relaxed text-slate-700">{children}</p>
}

function Titulo({ children }: { children: ReactNode }) {
  return <h3 className="mt-5 text-sm font-bold uppercase tracking-wide text-slate-500">{children}</h3>
}

function Termo({ children }: { children: ReactNode }) {
  return <strong className="font-semibold text-slate-900">{children}</strong>
}

const SECOES: Secao[] = [
  // ----------------------------------------------------------------
  {
    id: 'comecando',
    titulo: 'Como funciona',
    icone: Lightbulb,
    conteudo: (
      <>
        <Paragrafo>
          O sistema guarda quatro coisas que precisam bater entre si o tempo todo:
          o <Termo>catálogo</Termo> (o que você vende), o <Termo>estoque</Termo> (quanto
          tem de cada item), o <Termo>caixa</Termo> (o dinheiro da gaveta) e
          o <Termo>financeiro</Termo> (o que entrou, saiu e ainda falta receber).
        </Paragrafo>
        <Paragrafo>
          Você quase nunca mexe nesses quatro na mão. Uma venda no PDV já baixa o
          estoque, movimenta o caixa e lança a receita. Uma compra recebida já dá
          entrada no estoque, recalcula o custo e lança a despesa. O sistema existe
          para que essas contas nunca fiquem desencontradas.
        </Paragrafo>

        <Titulo>Os três papéis</Titulo>
        <Paragrafo>
          Cada pessoa da loja entra com o próprio acesso, e o papel define o que ela vê:
        </Paragrafo>
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          <li><Termo>Dono</Termo> — vê tudo, inclusive financeiro, relatórios de margem
            e a equipe. É quem manda.</li>
          <li><Termo>Gerente</Termo> — faz tudo do dia a dia e vê o financeiro, mas não
            pode alterar nem criar um usuário dono.</li>
          <li><Termo>Vendedor</Termo> — vende, abre e fecha caixa, cadastra cliente.
            <Termo> Não vê o financeiro nem a margem dos produtos.</Termo></li>
        </ul>
        <Nota>
          Vale a pena dar acesso de vendedor a quem fica no balcão, em vez de todo mundo
          usar a mesma conta: assim o relatório de equipe mostra quem vendeu o quê, e o
          fechamento de caixa registra quem conferiu o dinheiro.
        </Nota>

        <Titulo>Seu primeiro dia</Titulo>
        <Passos itens={[
          <>Confira o <Link to="/estoque" className="-my-2.5 inline-block py-2.5 font-medium text-marca-700 underline decoration-marca-300 underline-offset-2">Estoque</Link> — ele já veio carregado com o que você tem.</>,
          <>Abra o <Link to="/caixa" className="-my-2.5 inline-block py-2.5 font-medium text-marca-700 underline decoration-marca-300 underline-offset-2">Caixa</Link>, informando o troco que está na gaveta.</>,
          <>Venda no <Link to="/pdv" className="-my-2.5 inline-block py-2.5 font-medium text-marca-700 underline decoration-marca-300 underline-offset-2">PDV</Link> durante o dia.</>,
          <>No fim do expediente, volte ao Caixa, conte o dinheiro e feche.</>,
        ]} />
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'painel',
    titulo: 'Painel',
    icone: LayoutDashboard,
    conteudo: (
      <>
        <Paragrafo>
          É a tela que abre quando você entra. Serve para responder em cinco segundos:
          como foi hoje, como está o mês, tem algo pedindo atenção?
        </Paragrafo>
        <Titulo>O que cada quadro mostra</Titulo>
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          <li><Termo>Vendas hoje</Termo> — quanto faturou e quantas vendas, com o ticket médio.</li>
          <li><Termo>Lucro hoje</Termo> — o que sobrou depois de descontar quanto as peças
            custaram para você.</li>
          <li><Termo>Estoque</Termo> — quantas unidades tem e quanto isso custou.</li>
          <li><Termo>A receber</Termo> — fiado em aberto.</li>
        </ul>
        <Paragrafo>
          Logo abaixo aparecem os avisos: itens no estoque mínimo, itens zerados e contas
          em atraso. Eles são clicáveis e levam direto para a lista do problema.
        </Paragrafo>
        <Nota>
          O quadro do caixa mostra se ele está aberto. Se estiver fechado, o PDV não
          aceita venda — é o primeiro lugar a olhar quando alguém disser que "não
          consegue vender".
        </Nota>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'pdv',
    titulo: 'PDV — Vender',
    icone: ShoppingCart,
    conteudo: (
      <>
        <Paragrafo>
          É a tela do balcão, feita para ser rápida. O cursor já nasce na busca e volta
          para lá depois de cada item.
        </Paragrafo>
        <Titulo>Como fazer uma venda</Titulo>
        <Passos itens={[
          <>Digite o nome, o sabor ou o SKU — ou passe o leitor no código de barras,
            que cai direto no carrinho.</>,
          <>Toque no produto para adicioná-lo. Toque de novo para somar outra unidade.</>,
          <>Se precisar, ajuste a quantidade nos botões <Termo>−</Termo> e <Termo>+</Termo>,
            ou mude o preço daquele item no campo ao lado.</>,
          <>Dê desconto no campo <Termo>Desconto</Termo>, se for o caso.</>,
          <>Toque em <Termo>Finalizar venda</Termo> (ou aperte <Termo>F2</Termo> no
            teclado), escolha a forma de pagamento e confirme.</>,
        ]} />

        <Titulo>Pagamento e troco</Titulo>
        <Paragrafo>
          Ao pagar em dinheiro, informe quanto o cliente entregou e o sistema calcula o
          troco. Nas outras formas, o valor é o total da venda — se você digitar a mais
          no cartão, o sistema recusa, porque ali não existe troco e aquilo seria erro
          de digitação.
        </Paragrafo>
        <Paragrafo>
          Só o <Termo>dinheiro</Termo> entra na gaveta. Pix e cartão vão para o
          financeiro, mas não afetam a conferência do caixa — é por isso que o valor
          fechado no fim do dia costuma ser menor que o total vendido.
        </Paragrafo>

        <Titulo>Cliente e fiado</Titulo>
        <Paragrafo>
          Identificar o cliente é opcional na venda comum, mas <Termo>obrigatório no
          fiado</Termo> — e o sistema só deixa fiar dentro do limite de crédito que você
          cadastrou para aquela pessoa.
        </Paragrafo>
        <Nota tom="atencao">
          Se o cliente cadastrado for menor de 18 anos, a venda é bloqueada.
        </Nota>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'caixa',
    titulo: 'Caixa',
    icone: Wallet,
    conteudo: (
      <>
        <Paragrafo>
          O caixa é uma sessão: abre de manhã, recebe as vendas do dia e fecha à noite.
          Toda venda pertence a um caixa aberto — é isso que permite conferir, no fim do
          expediente, se o dinheiro da gaveta bate com o que foi registrado.
        </Paragrafo>

        <Titulo>Abrir</Titulo>
        <Paragrafo>
          Informe o <Termo>fundo de troco</Termo>: o dinheiro que já está na gaveta antes
          da primeira venda. Se não houver, deixe zero.
        </Paragrafo>

        <Titulo>Durante o dia</Titulo>
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          <li><Termo>Sangria</Termo> — retirada de dinheiro (depósito no banco, pagamento
            de uma conta). Sai da gaveta.</li>
          <li><Termo>Suprimento</Termo> — entrada de dinheiro que não é venda, como
            reforço de troco.</li>
        </ul>
        <Nota>
          Registre sangria e suprimento na hora. Se o dinheiro sair sem registro, a
          diferença vai aparecer no fechamento e você não vai lembrar por quê.
        </Nota>

        <Titulo>Fechar</Titulo>
        <Passos itens={[
          'Conte o dinheiro físico da gaveta.',
          'Informe o valor contado — o sistema mostra o que ele calculou.',
          'Confirme. A diferença, para mais ou para menos, fica registrada no histórico.',
        ]} />
        <Paragrafo>
          A diferença não impede o fechamento: ela é justamente o dado que interessa.
          Falta recorrente no mesmo turno é informação de gestão, não erro do sistema.
        </Paragrafo>
        <Nota tom="atencao">
          Não é possível fechar com venda em aberto. Finalize ou cancele antes.
        </Nota>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'vendas',
    titulo: 'Vendas',
    icone: Receipt,
    conteudo: (
      <>
        <Paragrafo>
          O histórico de tudo que foi vendido, com filtro por período e status. Clique no
          olho para ver os itens, os pagamentos e o lucro daquela venda.
        </Paragrafo>
        <Titulo>Cancelar uma venda</Titulo>
        <Paragrafo>
          Só dono e gerente podem. O cancelamento desfaz tudo de uma vez: devolve os
          itens ao estoque, tira o dinheiro da gaveta (se foi em espécie) e cancela o
          lançamento no financeiro.
        </Paragrafo>
        <Nota tom="atencao">
          Para cancelar uma venda paga em dinheiro é preciso ter um caixa aberto — o
          estorno precisa sair de algum lugar.
        </Nota>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'produtos',
    titulo: 'Produtos',
    icone: Package,
    conteudo: (
      <>
        <Paragrafo>
          Aqui mora o catálogo. A parte mais importante de entender é a diferença entre
          produto e variação.
        </Paragrafo>
        <Titulo>Produto e variação</Titulo>
        <Paragrafo>
          O <Termo>produto</Termo> é o modelo: "Elfbar 30K". A <Termo>variação</Termo> é
          o que de fato se vende: "Elfbar 30K · Miami Mint". É a variação que tem preço,
          código de barras e estoque — porque na prateleira você não tem "dez Elfbar",
          tem "três Miami Mint e sete Acai Banana".
        </Paragrafo>
        <Nota>
          Quando um sabor acaba e outro não, é a variação que zera. Por isso o estoque,
          a vitrine e os relatórios trabalham sempre no nível da variação.
        </Nota>

        <Titulo>Cadastrar</Titulo>
        <Passos itens={[
          <>Toque em <Termo>Novo produto</Termo> e informe nome, tipo, categoria e marca.</>,
          'Preencha a primeira variação com sabor, custo e preço de venda.',
          <>Depois, expanda o produto na lista e use <Termo>Adicionar variação</Termo> para
            os outros sabores.</>,
        ]} />

        <Titulo>Foto do produto</Titulo>
        <Paragrafo>
          Edite o produto e use <Termo>Escolher foto</Termo>. A imagem aparece na vitrine
          pública e na lista de produtos. É uma foto por modelo — todos os sabores daquele
          modelo mostram a mesma.
        </Paragrafo>
        <Nota>
          Pode mandar a foto direto do celular: o sistema reduz e comprime sozinho, então
          não precisa se preocupar com o tamanho do arquivo.
        </Nota>

        <Titulo>Estoque mínimo</Titulo>
        <Paragrafo>
          É o ponto em que o sistema avisa para repor. Deixe em zero nos itens que você
          não pretende repor — assim o alerta continua significando alguma coisa. Se
          tudo estiver sempre em alerta, ninguém olha.
        </Paragrafo>

        <Titulo>Excluir</Titulo>
        <Paragrafo>
          Produto que já foi vendido não é excluído, apenas desativado: apagar quebraria
          o histórico das vendas antigas. Ele some do PDV e da vitrine, mas os relatórios
          do passado continuam corretos.
        </Paragrafo>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'estoque',
    titulo: 'Estoque',
    icone: Boxes,
    conteudo: (
      <>
        <Paragrafo>
          Mostra o saldo de cada variação e o extrato de tudo que entrou e saiu. As
          vendas e as compras mexem no estoque sozinhas — aqui você registra o que
          acontece fora delas.
        </Paragrafo>

        <Titulo>As quatro operações</Titulo>
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          <li><Termo>Entrada</Termo> — chegou mercadoria sem uma compra registrada. Se
            informar o custo, o custo médio é recalculado.</li>
          <li><Termo>Perda</Termo> — quebrou, venceu, sumiu. Sai do estoque sem virar venda.</li>
          <li><Termo>Devolução</Termo> — o cliente devolveu e o item voltou para a prateleira.</li>
          <li><Termo>Inventário</Termo> — você contou a prateleira. Informe
            <Termo> quanto contou</Termo>, não a diferença: o sistema calcula o ajuste.</li>
        </ul>

        <Titulo>Custo médio</Titulo>
        <Paragrafo>
          Quando chega mercadoria nova por um preço diferente, o sistema calcula a média
          ponderada. Comprou 10 a R$ 55 e depois 10 a R$ 65? O custo passa a ser R$ 60, e
          é esse valor que entra no cálculo do lucro das próximas vendas.
        </Paragrafo>
        <Nota>
          O custo fica <Termo>congelado</Termo> em cada venda no momento em que ela
          acontece. Mudar o preço depois não reescreve o lucro do que já foi vendido.
        </Nota>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'clientes',
    titulo: 'Clientes',
    icone: Users,
    conteudo: (
      <>
        <Paragrafo>
          Cadastrar cliente é opcional para vender, mas necessário para duas coisas:
          fiado e histórico de compras.
        </Paragrafo>
        <Titulo>Limite de crédito</Titulo>
        <Paragrafo>
          É quanto aquele cliente pode dever. Em zero, ele não compra fiado. O sistema
          desconta o que já está em aberto: com limite de R$ 200 e R$ 150 em aberto,
          sobram R$ 50.
        </Paragrafo>
        <Titulo>Data de nascimento</Titulo>
        <Paragrafo>
          Serve para bloquear a venda a menor de idade. Cliente sem data cadastrada não
          bloqueia nada — a venda anônima de balcão continua possível.
        </Paragrafo>
        <Paragrafo>
          O ícone de histórico mostra quanto a pessoa já comprou, o ticket médio e o que
          ainda deve.
        </Paragrafo>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'compras',
    titulo: 'Fornecedores e compras',
    icone: Truck,
    conteudo: (
      <>
        <Paragrafo>
          É por aqui que a mercadoria entra da forma certa: com custo, fornecedor e
          reflexo no financeiro.
        </Paragrafo>
        <Titulo>Como registrar uma compra</Titulo>
        <Passos itens={[
          'Cadastre o fornecedor, se ainda não existir.',
          <>Em <Termo>Compras</Termo>, toque em <Termo>Nova compra</Termo>, escolha o
            fornecedor e a data.</>,
          'Busque cada produto, informe a quantidade e o custo unitário pago.',
          <>Salve. A compra fica como <Termo>rascunho</Termo> e ainda não mexe em nada.</>,
          <>Quando a mercadoria chegar, toque no <Termo>visto</Termo> para receber.</>,
        ]} />
        <Paragrafo>
          O recebimento faz três coisas de uma vez: dá entrada no estoque, recalcula o
          custo médio e lança a despesa no financeiro.
        </Paragrafo>
        <Titulo>À vista ou a prazo</Titulo>
        <Paragrafo>
          Se você preencher o <Termo>vencimento</Termo>, a compra vira uma conta a pagar
          em aberto. Se deixar vazio, o sistema entende que foi paga à vista e já lança
          como paga na data da compra.
        </Paragrafo>
        <Nota tom="atencao">
          Cancelar uma compra já recebida estorna tudo: tira a mercadoria do estoque e
          cancela a despesa. Use quando a nota veio errada.
        </Nota>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'financeiro',
    titulo: 'Financeiro',
    icone: Wallet,
    conteudo: (
      <>
        <Paragrafo>
          Tem duas abas. A <Termo>Visão de gestão</Termo> responde "como o negócio está
          indo"; a de <Termo>Lançamentos</Termo> é a lista de contas para pagar e receber.
        </Paragrafo>

        <Titulo>Lucro e caixa não são a mesma coisa</Titulo>
        <Paragrafo>
          Esta é a parte que mais confunde, e vale ler devagar.
        </Paragrafo>
        <Paragrafo>
          O <Termo>lucro</Termo> é o faturamento menos o custo <em>daquilo que você
          vendeu</em>, menos as despesas da loja. O <Termo>caixa</Termo> é simplesmente
          quanto dinheiro entrou e saiu no período.
        </Paragrafo>
        <Paragrafo>
          Quando você compra estoque, o caixa cai — mas não é prejuízo: o dinheiro virou
          mercadoria e volta quando ela for vendida. É por isso que o caixa pode estar
          negativo num mês em que você teve lucro. A tela mostra exatamente quanto está
          parado na prateleira, para explicar a diferença.
        </Paragrafo>
        <Nota>
          Regra prática: olhe o <Termo>lucro</Termo> para saber se o negócio dá dinheiro,
          e o <Termo>caixa</Termo> para saber se você consegue pagar as contas deste mês.
        </Nota>

        <Titulo>A receber e a pagar</Titulo>
        <Paragrafo>
          <Termo>A receber</Termo> é o fiado em aberto. <Termo>A pagar</Termo> são as
          compras a prazo e as contas que você lançou. O que passou do vencimento aparece
          destacado em vermelho.
        </Paragrafo>

        <Titulo>Lançar uma conta</Titulo>
        <Paragrafo>
          Aluguel, energia, salário e qualquer outra despesa entram em
          <Termo> Novo lançamento</Termo>. Quando pagar, use o visto para dar baixa. Se
          errar, o botão de estorno volta atrás.
        </Paragrafo>
        <Nota tom="atencao">
          Lançamento criado por uma venda ou compra não pode ser excluído — cancele a
          venda ou a compra de origem, para os números continuarem batendo.
        </Nota>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'relatorios',
    titulo: 'Relatórios',
    icone: BarChart3,
    conteudo: (
      <>
        <Paragrafo>
          Seis visões, todas com filtro de período. As mais úteis para decidir compra:
        </Paragrafo>
        <ul className="mt-3 space-y-2.5 text-sm text-slate-700">
          <li><Termo>Mais vendidos</Termo> — o que sai. Base para repor.</li>
          <li><Termo>Margem por produto</Termo> — o que dá dinheiro. Nem sempre é o mais
            vendido: um item de giro alto e margem baixa pode render menos que um de
            giro médio e margem boa.</li>
          <li><Termo>Curva ABC</Termo> — separa os itens que respondem por 80% da sua
            receita (classe A) do resto. Os A são os que <Termo>não podem faltar</Termo>.</li>
          <li><Termo>Giro de estoque</Termo> — quantas vezes o estoque girou. Marca como
            "parado" o que tem saldo e não vendeu no período, e como "ruptura" o que
            vendeu e zerou.</li>
          <li><Termo>Formas de pagamento</Termo> — quanto veio de Pix, cartão, dinheiro.</li>
          <li><Termo>Equipe</Termo> — quanto cada vendedor faturou, com ticket médio.</li>
        </ul>
        <Nota>
          Curva ABC e giro juntos respondem a pergunta mais cara da loja: em que gastar
          o dinheiro da próxima compra. Repõe os A que estão em ruptura e evita comprar
          mais do que está parado.
        </Nota>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'vitrine',
    titulo: 'Vitrine pública',
    icone: Store,
    conteudo: (
      <>
        <Paragrafo>
          É uma página sem senha com o que você tem disponível, para mandar aos clientes
          no WhatsApp. Ela se atualiza sozinha: item que esgota some da lista, item que
          chega aparece.
        </Paragrafo>
        <Titulo>O que ela mostra — e o que não mostra</Titulo>
        <Paragrafo>
          Mostra o modelo, o sabor e o preço. <Termo>Não mostra</Termo> o seu custo, a
          margem nem a quantidade exata — em vez do número, aparece "última unidade",
          "poucas unidades" ou "disponível", para não entregar seu estoque à concorrência.
        </Paragrafo>
        <Titulo>Como o cliente faz um pedido</Titulo>
        <Paragrafo>
          Ele monta o carrinho na vitrine e toca em <Termo>Reservar no WhatsApp</Termo>. A
          conversa abre no seu WhatsApp com a lista pronta: itens, quantidades e total.
          A partir daí é você quem combina a reserva.
        </Paragrafo>
        <Nota tom="atencao">
          O pedido da vitrine <Termo>não</Termo> baixa estoque nem registra venda. Ele é um
          recado. A venda só existe quando alguém a registra no PDV — assim o estoque nunca
          cai por uma reserva que não se confirmou.
        </Nota>
        <Paragrafo>
          A quantidade que o cliente pode pedir respeita o que você tem: item marcado como
          "última unidade" não deixa somar mais de uma.
        </Paragrafo>

        <Titulo>Como ativar</Titulo>
        <Passos itens={[
          <>Vá em <Link to="/configuracoes" className="-my-2.5 inline-block py-2.5 font-medium text-marca-700 underline decoration-marca-300 underline-offset-2">Configurações → Vitrine pública</Link>.</>,
          'Ligue a chave e copie o link que aparece.',
          <>Preencha o <Termo>WhatsApp</Termo> — sem ele o cliente monta o pedido mas não
            tem como enviar.</>,
          <>Suba as fotos dos modelos em <Link to="/produtos" className="-my-2.5 inline-block py-2.5 font-medium text-marca-700 underline decoration-marca-300 underline-offset-2">Produtos</Link>: vitrine com foto vende bem mais que lista de nomes.</>,
        ]} />
        <Nota tom="atencao">
          É um catálogo informativo, não uma loja on-line: ninguém compra por ali. O link
          é público — quem tiver o endereço abre, ainda que a página não apareça em
          buscadores.
        </Nota>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'configuracoes',
    titulo: 'Configurações',
    icone: Settings,
    conteudo: (
      <>
        <Titulo>Dados da loja</Titulo>
        <Paragrafo>
          Nome, telefone e endereço. O nome aparece no topo do sistema, no recibo e na
          vitrine.
        </Paragrafo>

        <Titulo>Operação</Titulo>
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          <li><Termo>Exigir cliente na venda</Termo> — obriga identificar quem comprou.</li>
          <li><Termo>Permitir vender sem estoque</Termo> — deixa o saldo ficar negativo.
            Só ligue se trabalhar com encomenda.</li>
          <li><Termo>Permitir fiado</Termo> — habilita a venda a prazo.</li>
          <li><Termo>Prazo do fiado</Termo> — em quantos dias a venda fiada vence. O
            padrão é 30; em zero, vence no mesmo dia e apareceria como atrasada já no
            dia seguinte.</li>
        </ul>

        <Titulo>Equipe</Titulo>
        <Paragrafo>
          Cria e desativa os acessos. Usuário com vendas registradas é desativado, não
          excluído — o histórico precisa continuar mostrando quem vendeu.
        </Paragrafo>

        <Titulo>Minha conta</Titulo>
        <Paragrafo>
          Seu nome, telefone e a troca de senha. O e-mail de acesso não muda por aqui:
          quem altera é um dono, pela aba Equipe.
        </Paragrafo>
      </>
    ),
  },

  // ----------------------------------------------------------------
  {
    id: 'duvidas',
    titulo: 'Dúvidas frequentes',
    icone: Lightbulb,
    conteudo: (
      <>
        {[
          {
            p: 'Não consigo vender, o PDV não deixa.',
            r: 'O caixa está fechado. Vá em Caixa → Abrir caixa.',
          },
          {
            p: 'O total vendido não bate com o dinheiro da gaveta.',
            r: 'É esperado. Só o dinheiro em espécie passa pela gaveta; Pix e cartão vão direto para o financeiro. Confira pela aba de formas de pagamento na tela do Caixa.',
          },
          {
            p: 'Meu lucro está positivo, mas o caixa está negativo.',
            r: 'Você comprou estoque. O dinheiro virou mercadoria e volta quando ela for vendida. A tela do Financeiro mostra exatamente quanto está parado.',
          },
          {
            p: 'Vendi errado, e agora?',
            r: 'Vá em Vendas, abra a venda e cancele. O estoque volta, o dinheiro sai da gaveta e o lançamento é cancelado. Se foi paga em dinheiro, o caixa precisa estar aberto.',
          },
          {
            p: 'Chegou mercadoria nova. Onde registro?',
            r: 'Em Fornecedores e compras, se tem nota e fornecedor — assim o custo e o financeiro ficam certos. Em Estoque → Entrada, para um acerto avulso.',
          },
          {
            p: 'Contei a prateleira e o número não bate.',
            r: 'Use Estoque → Inventário e informe quanto contou. O sistema registra o ajuste e a diferença fica no extrato.',
          },
          {
            p: 'Como sei o que comprar na próxima vez?',
            r: 'Relatórios → Curva ABC mostra os itens que respondem pela maior parte da receita; o Giro mostra o que está parado. Reponha os primeiros e evite os segundos.',
          },
          {
            p: 'Esqueci minha senha.',
            r: 'Peça a um dono para definir uma nova em Configurações → Equipe, editando seu usuário.',
          },
        ].map((item) => (
          <div key={item.p} className="mt-4 border-l-2 border-slate-200 pl-3">
            <p className="text-sm font-semibold text-slate-900">{item.p}</p>
            <p className="mt-1 text-sm leading-relaxed text-slate-600">{item.r}</p>
          </div>
        ))}
      </>
    ),
  },
]

export function Guia() {
  const [ativa, setAtiva] = useState(SECOES[0].id)

  // Abre na seção indicada pela âncora (#pdv, por exemplo).
  useEffect(() => {
    const alvo = window.location.hash.replace('#', '')
    if (alvo && SECOES.some((secao) => secao.id === alvo)) setAtiva(alvo)
  }, [])

  function irPara(id: string) {
    setAtiva(id)
    window.history.replaceState(null, '', `#${id}`)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const secao = SECOES.find((item) => item.id === ativa) ?? SECOES[0]
  const Icone = secao.icone

  return (
    <>
      <CabecalhoPagina
        titulo="Guia de uso"
        descricao="Como operar cada tela do sistema, e por que as regras são o que são."
      />

      <div className="grid gap-4 lg:grid-cols-[250px_1fr]">
        {/* Índice */}
        {/* No celular o índice fica acima do conteúdo, com rolagem própria
            para não empurrar o texto para fora da primeira tela. */}
        <nav className="cartao h-max overflow-hidden lg:sticky lg:top-20">
          <ul className="max-h-64 divide-y divide-slate-100 overflow-y-auto lg:max-h-none">
            {SECOES.map((item) => {
              const IconeItem = item.icone
              const selecionada = item.id === ativa
              return (
                <li key={item.id}>
                  <button
                    onClick={() => irPara(item.id)}
                    className={`flex min-h-[48px] w-full items-center gap-2.5 px-3 text-left
                                text-sm transition ${
                      selecionada
                        ? 'bg-marca-50 font-semibold text-marca-800'
                        : 'text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <IconeItem size={16} className="shrink-0" />
                    <span className="min-w-0 flex-1 truncate">{item.titulo}</span>
                    {selecionada && <ChevronRight size={15} className="shrink-0" />}
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Conteúdo */}
        <Cartao>
          <header className="flex items-center gap-2.5 border-b border-slate-200 pb-3">
            <span className="rounded-lg bg-marca-50 p-2 text-marca-700">
              <Icone size={20} />
            </span>
            <h2 className="text-lg font-bold text-slate-900">{secao.titulo}</h2>
          </header>
          <div className="pt-1">{secao.conteudo}</div>

          <div className="mt-6 flex items-center justify-between gap-3 border-t border-slate-200 pt-4">
            {(() => {
              const indice = SECOES.findIndex((item) => item.id === ativa)
              const anterior = SECOES[indice - 1]
              const proxima = SECOES[indice + 1]
              return (
                <>
                  {anterior ? (
                    <button
                      onClick={() => irPara(anterior.id)}
                      className="min-h-[44px] text-sm font-medium text-marca-700 hover:underline"
                    >
                      ← {anterior.titulo}
                    </button>
                  ) : <span />}
                  {proxima && (
                    <button
                      onClick={() => irPara(proxima.id)}
                      className="min-h-[44px] text-right text-sm font-medium text-marca-700 hover:underline"
                    >
                      {proxima.titulo} →
                    </button>
                  )}
                </>
              )
            })()}
          </div>
        </Cartao>
      </div>
    </>
  )
}
