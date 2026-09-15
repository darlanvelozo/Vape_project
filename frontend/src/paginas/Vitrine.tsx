/**
 * Vitrine pública — o catálogo que o cliente da loja abre, sem senha.
 *
 * Desenhada para o celular antes de tudo: o caminho normal é o lojista mandar
 * o link no WhatsApp e a pessoa abrir no telefone, na rua, em rede ruim. Daí
 * a página ser leve (não carrega nada do sistema interno), com alvos grandes
 * e leitura em coluna única.
 *
 * O pedido **não** é uma venda: o cliente monta o carrinho e a mensagem sai
 * pronta no WhatsApp da loja, onde a reserva é combinada. Nada é debitado do
 * estoque aqui — o item só sai quando alguém vender no PDV.
 */

import { useQuery } from '@tanstack/react-query'
import {
  AlertCircle, ImageOff, Minus, MessageCircle, Plus, Search, ShoppingBag, Store, X,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'

import { Carregando } from '../componentes/ui'
import { api } from '../lib/api'
import { formatarMoeda } from '../lib/formato'

type Disponibilidade = 'ultima_unidade' | 'poucas_unidades' | 'disponivel'

interface Opcao {
  id: number
  sabor: string
  nicotina_mg: string | null
  puffs: number | null
  disponibilidade: Disponibilidade
  preco_centavos?: number
}

interface ProdutoVitrine {
  id: number
  nome: string
  marca: string
  categoria: string
  descricao: string
  imagem_url: string | null
  opcoes: Opcao[]
}

interface Vitrine {
  loja: { nome: string; cidade: string; uf: string; whatsapp: string }
  mensagem: string
  mostrar_preco: boolean
  produtos: ProdutoVitrine[]
  total_itens: number
  aviso_idade: string
}

interface ItemCarrinho {
  opcaoId: number
  produto: string
  sabor: string
  precoCentavos: number
  quantidade: number
  maximo: number
}

const ROTULO: Record<Disponibilidade, string> = {
  ultima_unidade: 'última unidade',
  poucas_unidades: 'poucas unidades',
  disponivel: 'disponível',
}

const COR: Record<Disponibilidade, string> = {
  ultima_unidade: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  poucas_unidades: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  disponivel: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
}

/**
 * Teto de quantidade por faixa de estoque.
 *
 * A vitrine não revela o saldo exato, mas também não pode aceitar 10 unidades
 * de um item que tem uma só — o cliente combinaria uma reserva impossível.
 */
const MAXIMO_POR_FAIXA: Record<Disponibilidade, number> = {
  ultima_unidade: 1,
  poucas_unidades: 3,
  disponivel: 10,
}

const CHAVE_CARRINHO = 'vape.vitrine.carrinho'

export function Vitrine() {
  const { slug = '' } = useParams()
  const [busca, setBusca] = useState('')
  const [carrinho, setCarrinho] = useState<ItemCarrinho[]>([])
  const [carrinhoAberto, setCarrinhoAberto] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['vitrine', slug],
    queryFn: () => api.get<Vitrine>(`/vitrine/${slug}/`),
    retry: false,
  })

  // Catálogo público não deve ser indexado: o link circula por WhatsApp, não
  // pelo buscador. O Nginx manda o mesmo em X-Robots-Tag.
  useEffect(() => {
    const meta = document.createElement('meta')
    meta.name = 'robots'
    meta.content = 'noindex, nofollow'
    document.head.appendChild(meta)
    return () => {
      document.head.removeChild(meta)
    }
  }, [])

  useEffect(() => {
    if (data) document.title = `${data.loja.nome} — disponível agora`
  }, [data])

  // O carrinho sobrevive a fechar a aba: é comum a pessoa ir olhar outra coisa
  // no meio e voltar. Falha de armazenamento (aba anônima) não pode quebrar a
  // página, então tudo é protegido.
  useEffect(() => {
    try {
      const salvo = localStorage.getItem(`${CHAVE_CARRINHO}.${slug}`)
      if (salvo) setCarrinho(JSON.parse(salvo))
    } catch {
      /* sem carrinho salvo; segue com o vazio */
    }
  }, [slug])

  useEffect(() => {
    try {
      localStorage.setItem(`${CHAVE_CARRINHO}.${slug}`, JSON.stringify(carrinho))
    } catch {
      /* navegador sem armazenamento: o carrinho vale só para esta visita */
    }
  }, [carrinho, slug])

  const alterar = useCallback((item: Omit<ItemCarrinho, 'quantidade'>, delta: number) => {
    setCarrinho((atual) => {
      const existente = atual.find((linha) => linha.opcaoId === item.opcaoId)
      if (!existente) {
        return delta > 0 ? [...atual, { ...item, quantidade: 1 }] : atual
      }
      const nova = Math.min(Math.max(existente.quantidade + delta, 0), item.maximo)
      if (nova === 0) return atual.filter((linha) => linha.opcaoId !== item.opcaoId)
      return atual.map((linha) =>
        linha.opcaoId === item.opcaoId ? { ...linha, quantidade: nova } : linha,
      )
    })
  }, [])

  const totalItens = carrinho.reduce((soma, item) => soma + item.quantidade, 0)
  const totalCentavos = carrinho.reduce(
    (soma, item) => soma + item.precoCentavos * item.quantidade,
    0,
  )

  const produtos = useMemo(() => {
    if (!data) return []
    const termo = busca.trim().toLowerCase()
    if (!termo) return data.produtos
    return data.produtos
      .map((produto) => ({
        ...produto,
        opcoes: produto.opcoes.filter(
          (opcao) =>
            produto.nome.toLowerCase().includes(termo) ||
            produto.marca.toLowerCase().includes(termo) ||
            opcao.sabor.toLowerCase().includes(termo),
        ),
      }))
      .filter((produto) => produto.opcoes.length > 0)
  }, [data, busca])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <Carregando texto="Carregando o catálogo…" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-950 px-6 text-center">
        <Store size={40} className="text-slate-700" />
        <h1 className="text-lg font-semibold text-slate-200">Catálogo indisponível</h1>
        <p className="max-w-sm text-sm text-slate-500">
          Este link não está ativo. Confira o endereço com a loja.
        </p>
      </div>
    )
  }

  const whatsapp = data.loja.whatsapp.replace(/\D/g, '')

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-white/10 bg-gradient-to-b from-marca-950 to-slate-950">
        <div className="mx-auto max-w-3xl px-4 pb-6 pt-8">
          <p className="text-3xl">💨</p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
            {data.loja.nome}
          </h1>
          {(data.loja.cidade || data.mensagem) && (
            <p className="mt-1 text-sm text-marca-200">
              {[
                data.loja.cidade && `${data.loja.cidade}${data.loja.uf ? `/${data.loja.uf}` : ''}`,
                data.mensagem,
              ].filter(Boolean).join(' · ')}
            </p>
          )}
          <p className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            {data.total_itens} {data.total_itens === 1 ? 'item disponível' : 'itens disponíveis'}
          </p>
        </div>
      </header>

      <main className={`mx-auto max-w-3xl px-4 pt-5 ${totalItens > 0 ? 'pb-36' : 'pb-10'}`}>
        {data.total_itens > 4 && (
          <div className="relative mb-5">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              value={busca}
              onChange={(evento) => setBusca(evento.target.value)}
              placeholder="Buscar modelo ou sabor…"
              className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pl-10 pr-3 text-base
                         text-slate-100 placeholder:text-slate-500
                         focus:border-marca-400 focus:outline-none focus:ring-2 focus:ring-marca-500/30"
              autoComplete="off"
            />
          </div>
        )}

        {produtos.length === 0 ? (
          <p className="py-16 text-center text-sm text-slate-500">
            {busca ? `Nada encontrado para “${busca}”.` : 'Nenhum item disponível no momento.'}
          </p>
        ) : (
          <div className="space-y-4">
            {produtos.map((produto) => (
              <article
                key={produto.id}
                className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04]"
              >
                <div className="flex gap-3 border-b border-white/10 p-4">
                  <Foto url={produto.imagem_url} alt={produto.nome} />
                  <div className="min-w-0 flex-1">
                    {produto.marca &&
                      !produto.nome.toLowerCase().startsWith(produto.marca.toLowerCase()) && (
                        <p className="text-xs font-semibold uppercase tracking-wider text-marca-300">
                          {produto.marca}
                        </p>
                      )}
                    <h2 className="text-lg font-semibold leading-tight">{produto.nome}</h2>
                    {produto.descricao && (
                      <p className="mt-0.5 text-xs text-slate-400">{produto.descricao}</p>
                    )}
                  </div>
                </div>

                <ul className="divide-y divide-white/5">
                  {produto.opcoes.map((opcao) => {
                    const noCarrinho =
                      carrinho.find((item) => item.opcaoId === opcao.id)?.quantidade ?? 0
                    const maximo = MAXIMO_POR_FAIXA[opcao.disponibilidade]
                    const dados = {
                      opcaoId: opcao.id,
                      produto: produto.nome,
                      sabor: opcao.sabor || 'Padrão',
                      precoCentavos: opcao.preco_centavos ?? 0,
                      maximo,
                    }

                    return (
                      <li key={opcao.id} className="flex items-center gap-3 px-4 py-3">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium leading-snug">{opcao.sabor || 'Padrão'}</p>
                          <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-400">
                            {opcao.puffs && <span>{opcao.puffs.toLocaleString('pt-BR')} puffs</span>}
                            {opcao.nicotina_mg && <span>{opcao.nicotina_mg} mg</span>}
                            <span
                              className={`inline-flex rounded-full px-2 py-0.5 ring-1 ring-inset ${
                                COR[opcao.disponibilidade]
                              }`}
                            >
                              {ROTULO[opcao.disponibilidade]}
                            </span>
                          </p>
                          {data.mostrar_preco && opcao.preco_centavos !== undefined && (
                            <p className="numerico mt-1 text-base font-bold text-marca-200">
                              {formatarMoeda(opcao.preco_centavos)}
                            </p>
                          )}
                        </div>

                        {noCarrinho === 0 ? (
                          <button
                            onClick={() => alterar(dados, 1)}
                            className="shrink-0 rounded-xl bg-marca-700 px-4 py-2.5 text-sm font-semibold
                                       text-white transition active:bg-marca-800"
                          >
                            Adicionar
                          </button>
                        ) : (
                          <div className="flex shrink-0 items-center gap-1 rounded-xl bg-white/10 p-1">
                            <button
                              onClick={() => alterar(dados, -1)}
                              aria-label={`Menos um ${opcao.sabor}`}
                              className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-200 active:bg-white/10"
                            >
                              <Minus size={16} />
                            </button>
                            <span className="numerico w-6 text-center font-bold">{noCarrinho}</span>
                            <button
                              onClick={() => alterar(dados, 1)}
                              disabled={noCarrinho >= maximo}
                              aria-label={`Mais um ${opcao.sabor}`}
                              className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-200
                                         transition active:bg-white/10 disabled:opacity-30"
                            >
                              <Plus size={16} />
                            </button>
                          </div>
                        )}
                      </li>
                    )
                  })}
                </ul>
              </article>
            ))}
          </div>
        )}

        <div className="mt-8 flex items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-xs text-amber-200">
          <AlertCircle size={15} className="mt-0.5 shrink-0" />
          <p>
            {data.aviso_idade} Catálogo informativo, sujeito a alteração de disponibilidade
            sem aviso. O pedido feito aqui é uma <strong>solicitação de reserva</strong> —
            só é confirmado na conversa com a loja.
          </p>
        </div>
      </main>

      {/* Barra do pedido: só aparece com itens, para não roubar tela à toa. */}
      {totalItens > 0 && (
        <div className="area-segura-inferior fixed inset-x-0 bottom-0 border-t border-white/10
                        bg-slate-950/95 px-3 pt-3 backdrop-blur">
          <div className="mx-auto flex max-w-3xl items-center gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-xs text-slate-400">
                {totalItens} {totalItens === 1 ? 'item' : 'itens'} no pedido
              </p>
              <p className="numerico truncate text-xl font-bold">{formatarMoeda(totalCentavos)}</p>
            </div>
            <button
              onClick={() => setCarrinhoAberto(true)}
              className="flex shrink-0 items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3.5
                         text-base font-semibold text-white transition active:bg-emerald-700"
            >
              <ShoppingBag size={18} />
              Ver pedido
            </button>
          </div>
        </div>
      )}

      {carrinhoAberto && (
        <Pedido
          itens={carrinho}
          total={totalCentavos}
          loja={data.loja.nome}
          whatsapp={whatsapp}
          mostrarPreco={data.mostrar_preco}
          aoFechar={() => setCarrinhoAberto(false)}
          aoAlterar={alterar}
          aoLimpar={() => {
            setCarrinho([])
            setCarrinhoAberto(false)
          }}
        />
      )}
    </div>
  )
}

/** Foto do modelo, com espaço reservado quando não há imagem cadastrada. */
function Foto({ url, alt }: { url: string | null; alt: string }) {
  if (!url) {
    return (
      <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl bg-white/5 text-slate-600">
        <ImageOff size={22} />
      </div>
    )
  }
  return (
    <img
      src={url}
      alt={alt}
      loading="lazy"
      // Dimensão fixa evita o salto de layout enquanto a imagem carrega.
      className="h-20 w-20 shrink-0 rounded-xl object-cover"
    />
  )
}

/**
 * Resumo do pedido e envio para o WhatsApp.
 *
 * A mensagem é montada em texto simples porque é o que o WhatsApp aceita em
 * um link `wa.me` — e é também o que o lojista consegue ler e responder sem
 * precisar abrir o sistema.
 */
function Pedido({
  itens, total, loja, whatsapp, mostrarPreco, aoFechar, aoAlterar, aoLimpar,
}: {
  itens: ItemCarrinho[]
  total: number
  loja: string
  whatsapp: string
  mostrarPreco: boolean
  aoFechar: () => void
  aoAlterar: (item: Omit<ItemCarrinho, 'quantidade'>, delta: number) => void
  aoLimpar: () => void
}) {
  const mensagem = useMemo(() => {
    const linhas = itens.map((item) => {
      const valor = mostrarPreco
        ? ` — ${formatarMoeda(item.precoCentavos * item.quantidade)}`
        : ''
      return `• ${item.quantidade}x ${item.produto} — ${item.sabor}${valor}`
    })
    const rodape = mostrarPreco ? `\n\nTotal: ${formatarMoeda(total)}` : ''
    return (
      `Olá, ${loja}! Gostaria de reservar:\n\n` +
      `${linhas.join('\n')}${rodape}\n\n` +
      'Enviado pelo catálogo on-line.'
    )
  }, [itens, total, loja, mostrarPreco])

  const link = `https://wa.me/55${whatsapp}?text=${encodeURIComponent(mensagem)}`

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end bg-slate-950/70 backdrop-blur-sm sm:items-center sm:justify-center">
      <div
        className="absolute inset-0"
        onClick={aoFechar}
        aria-hidden
      />
      <div className="relative max-h-[88vh] w-full overflow-y-auto rounded-t-2xl border border-white/10
                      bg-slate-900 sm:max-w-lg sm:rounded-2xl">
        <header className="sticky top-0 flex items-center justify-between gap-3 border-b border-white/10
                           bg-slate-900 px-4 py-3">
          <h2 className="text-lg font-semibold text-slate-100">Seu pedido</h2>
          <button
            onClick={aoFechar}
            aria-label="Fechar pedido"
            className="flex h-10 w-10 items-center justify-center rounded-lg text-slate-400 active:bg-white/10"
          >
            <X size={20} />
          </button>
        </header>

        <ul className="divide-y divide-white/5">
          {itens.map((item) => (
            <li key={item.opcaoId} className="flex items-center gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-100">{item.produto}</p>
                <p className="text-xs text-slate-400">{item.sabor}</p>
                {mostrarPreco && (
                  <p className="numerico mt-0.5 text-sm font-semibold text-marca-200">
                    {formatarMoeda(item.precoCentavos * item.quantidade)}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1 rounded-xl bg-white/10 p-1">
                <button
                  onClick={() => aoAlterar(item, -1)}
                  aria-label="Diminuir"
                  className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-200 active:bg-white/10"
                >
                  <Minus size={16} />
                </button>
                <span className="numerico w-6 text-center font-bold">{item.quantidade}</span>
                <button
                  onClick={() => aoAlterar(item, 1)}
                  disabled={item.quantidade >= item.maximo}
                  aria-label="Aumentar"
                  className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-200
                             transition active:bg-white/10 disabled:opacity-30"
                >
                  <Plus size={16} />
                </button>
              </div>
            </li>
          ))}
        </ul>

        <div className="area-segura-inferior space-y-3 border-t border-white/10 px-4 pt-4">
          {mostrarPreco && (
            <div className="flex items-baseline justify-between">
              <span className="text-slate-300">Total</span>
              <span className="numerico text-2xl font-bold text-slate-100">
                {formatarMoeda(total)}
              </span>
            </div>
          )}

          {whatsapp ? (
            <a
              href={link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-4
                         text-base font-semibold text-white transition active:bg-emerald-700"
            >
              <MessageCircle size={19} />
              Reservar no WhatsApp
            </a>
          ) : (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
              A loja ainda não cadastrou um WhatsApp de contato. Anote seu pedido e fale
              com a loja pelos canais de sempre.
            </div>
          )}

          <p className="text-center text-xs text-slate-500">
            A reserva é confirmada na conversa. Nada é cobrado por esta página.
          </p>

          <button
            onClick={aoLimpar}
            className="min-h-[44px] w-full text-sm text-slate-400 transition active:text-rose-400"
          >
            Limpar pedido
          </button>
        </div>
      </div>
    </div>
  )
}
