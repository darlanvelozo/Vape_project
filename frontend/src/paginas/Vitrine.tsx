/**
 * Vitrine pública — a página que o cliente da loja abre, sem senha.
 *
 * Desenhada para o celular antes de tudo: o caminho normal é o lojista mandar
 * o link no WhatsApp e a pessoa abrir no telefone, na rua, em rede ruim. Daí
 * a página ser leve (não carrega gráfico nem nada do sistema interno), com
 * alvos grandes e leitura de cima para baixo em coluna única.
 */

import { useQuery } from '@tanstack/react-query'
import { AlertCircle, MessageCircle, Search, Store } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'

import { Carregando } from '../componentes/ui'
import { api } from '../lib/api'
import { formatarMoeda } from '../lib/formato'

type Disponibilidade = 'ultima_unidade' | 'poucas_unidades' | 'disponivel'

interface Opcao {
  sabor: string
  nicotina_mg: string | null
  puffs: number | null
  disponibilidade: Disponibilidade
  preco_centavos?: number
}

interface ProdutoVitrine {
  nome: string
  marca: string
  categoria: string
  descricao: string
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

const ROTULO_DISPONIBILIDADE: Record<Disponibilidade, string> = {
  ultima_unidade: 'última unidade',
  poucas_unidades: 'poucas unidades',
  disponivel: 'disponível',
}

const COR_DISPONIBILIDADE: Record<Disponibilidade, string> = {
  ultima_unidade: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  poucas_unidades: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  disponivel: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
}

export function Vitrine() {
  const { slug = '' } = useParams()
  const [busca, setBusca] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['vitrine', slug],
    queryFn: () => api.get<Vitrine>(`/vitrine/${slug}/`),
    retry: false,
  })

  // Catálogo público não deve ser indexado: o link circula por WhatsApp, não
  // pelo Google. O Nginx manda o mesmo em X-Robots-Tag.
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
      {/* Cabeçalho */}
      <header className="border-b border-white/10 bg-gradient-to-b from-marca-950 to-slate-950">
        <div className="mx-auto max-w-3xl px-4 pb-6 pt-8">
          <p className="text-3xl">💨</p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
            {data.loja.nome}
          </h1>
          {(data.loja.cidade || data.mensagem) && (
            <p className="mt-1 text-sm text-marca-200">
              {[data.loja.cidade && `${data.loja.cidade}${data.loja.uf ? `/${data.loja.uf}` : ''}`,
                data.mensagem].filter(Boolean).join(' · ')}
            </p>
          )}

          <p className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            {data.total_itens} {data.total_itens === 1 ? 'item disponível' : 'itens disponíveis'}
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-32 pt-5">
        {/* Busca — só aparece quando há catálogo o bastante para justificar */}
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
                key={produto.nome}
                className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04]"
              >
                <div className="border-b border-white/10 px-4 py-3">
                  {/* Marca omitida quando o nome do modelo já a contém —
                      "DUKE / Duke" não informa nada. */}
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

                <ul className="divide-y divide-white/5">
                  {produto.opcoes.map((opcao) => (
                    <li
                      key={opcao.sabor}
                      className="flex items-center justify-between gap-3 px-4 py-3"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="font-medium leading-snug">{opcao.sabor || 'Padrão'}</p>
                        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-400">
                          {opcao.puffs && <span>{opcao.puffs.toLocaleString('pt-BR')} puffs</span>}
                          {opcao.nicotina_mg && <span>{opcao.nicotina_mg} mg</span>}
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 ring-1 ring-inset ${
                              COR_DISPONIBILIDADE[opcao.disponibilidade]
                            }`}
                          >
                            {ROTULO_DISPONIBILIDADE[opcao.disponibilidade]}
                          </span>
                        </p>
                      </div>

                      {data.mostrar_preco && opcao.preco_centavos !== undefined && (
                        <p className="numerico shrink-0 text-right text-lg font-bold text-marca-200">
                          {formatarMoeda(opcao.preco_centavos)}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        )}

        <div className="mt-8 flex items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-xs text-amber-200">
          <AlertCircle size={15} className="mt-0.5 shrink-0" />
          <p>
            {data.aviso_idade} Catálogo informativo, sujeito a alteração de
            disponibilidade sem aviso. Não é uma loja on-line: não há compra por esta página.
          </p>
        </div>
      </main>

      {/* Contato fixo no rodapé: no celular é o alvo principal da página. */}
      {whatsapp && (
        <div className="area-segura-inferior fixed inset-x-0 bottom-0 border-t border-white/10
                        bg-slate-950/95 px-3 pt-3 backdrop-blur">
          <a
            href={`https://wa.me/55${whatsapp}`}
            target="_blank"
            rel="noopener noreferrer"
            className="mx-auto flex max-w-3xl items-center justify-center gap-2 rounded-xl
                       bg-emerald-600 px-4 py-3.5 text-base font-semibold text-white
                       transition active:bg-emerald-700"
          >
            <MessageCircle size={19} />
            Falar com a loja
          </a>
        </div>
      )}
    </div>
  )
}
