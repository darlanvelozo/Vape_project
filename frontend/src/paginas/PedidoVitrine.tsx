/**
 * Página do pedido para o cliente — pública pelo token, sem login.
 *
 * É ao mesmo tempo:
 * - a tela de pagamento (QR Code e Pix copia e cola, com a contagem da reserva);
 * - o acompanhamento (preparando → saiu para entrega / pronto → entregue);
 * - o comprovante de compra, depois que a loja confirma o Pix.
 *
 * Consulta o status a cada 15 s enquanto o pedido está em andamento: o
 * cliente vê "Pago" ou "Saiu para entrega" sem precisar recarregar.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle, ArrowLeft, Bike, CheckCircle2, Clock, Copy, Loader2, MessageCircle,
  Package, Printer, Search, Upload, XCircle,
} from 'lucide-react'
import QRCode from 'qrcode'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Carregando } from '../componentes/ui'
import { ErroApi, api, enviarArquivo } from '../lib/api'
import { formatarDataHora, formatarMoeda, formatarTelefone, numeroWhatsApp } from '../lib/formato'
import {
  PEDIDO_PAGO, etapasDoPedido, indiceEtapa, lembrarPedido, linkDoPedido,
} from '../lib/pedidos'
import type { PedidoPublico, PedidoResumo, StatusPedido } from '../lib/pedidos'

const ENCERRADOS: StatusPedido[] = ['entregue', 'cancelado']

function usarSemIndexacao() {
  useEffect(() => {
    const meta = document.createElement('meta')
    meta.name = 'robots'
    meta.content = 'noindex, nofollow'
    document.head.appendChild(meta)
    return () => {
      document.head.removeChild(meta)
    }
  }, [])
}

function Casca({ children, slug }: { children: ReactNode; slug: string }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 print:bg-white print:text-black">
      <div className="mx-auto max-w-lg px-4 pb-12 pt-4">
        <Link
          to={`/vitrine/${slug}`}
          className="-ml-2 mb-2 inline-flex min-h-[44px] items-center gap-1 px-2 text-sm text-slate-400 print:hidden"
        >
          <ArrowLeft size={16} /> Voltar ao catálogo
        </Link>
        {children}
      </div>
    </div>
  )
}

export function PedidoVitrine() {
  const { slug = '', token = '' } = useParams()
  const clienteQuery = useQueryClient()
  usarSemIndexacao()

  const { data: pedido, isLoading, isError } = useQuery({
    queryKey: ['pedido-vitrine', slug, token],
    queryFn: () => api.get<PedidoPublico>(`/vitrine/${slug}/pedidos/${token}/`),
    retry: false,
    refetchInterval: (consulta) =>
      consulta.state.data && ENCERRADOS.includes(consulta.state.data.status) ? false : 15000,
  })

  useEffect(() => {
    if (pedido) {
      lembrarPedido(slug, pedido.token)
      document.title = `Pedido ${pedido.codigo} — ${pedido.loja.nome}`
    }
  }, [pedido, slug])

  const atualizar = (novo: PedidoPublico) =>
    clienteQuery.setQueryData(['pedido-vitrine', slug, token], novo)

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <Carregando texto="Abrindo o pedido…" />
      </div>
    )
  }

  if (isError || !pedido) {
    return (
      <Casca slug={slug}>
        <div className="py-20 text-center">
          <Package size={40} className="mx-auto text-slate-700" />
          <h1 className="mt-3 text-lg font-semibold">Pedido não encontrado</h1>
          <p className="mt-1 text-sm text-slate-500">Confira o link ou procure pelo seu telefone.</p>
          <Link
            to={`/vitrine/${slug}/meus-pedidos`}
            className="mt-5 inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-marca-700 px-4 font-semibold"
          >
            <Search size={16} /> Meus pedidos
          </Link>
        </div>
      </Casca>
    )
  }

  const pago = PEDIDO_PAGO.includes(pedido.status)

  return (
    <Casca slug={slug}>
      <header className="mb-5">
        <p className="text-sm text-slate-400 print:text-black">{pedido.loja.nome}</p>
        <div className="flex items-end justify-between gap-3">
          <h1 className="text-2xl font-bold tracking-tight">
            Pedido <span className="font-mono text-marca-200 print:text-black">{pedido.codigo}</span>
          </h1>
          <SeloStatus status={pedido.status} rotulo={pedido.status_display} />
        </div>
        <p className="mt-1 text-xs text-slate-500">
          Feito em {formatarDataHora(pedido.criado_em)} · {pedido.codinome} · {pedido.telefone}
        </p>
      </header>

      <div className="space-y-4">
        {pedido.status === 'aguardando_pagamento' && <Pagamento pedido={pedido} slug={slug} aoAtualizar={atualizar} />}
        {pedido.status === 'aguardando_conferencia' && <EmConferencia pedido={pedido} />}
        {pedido.status === 'expirado' && <Expirado pedido={pedido} slug={slug} aoAtualizar={atualizar} />}
        {pedido.status === 'cancelado' && (
          <Aviso cor="vermelho" icone={<XCircle size={18} />} titulo="Pedido cancelado">
            {pedido.motivo_cancelamento || 'Este pedido foi cancelado.'}
          </Aviso>
        )}

        {(pago || pedido.status === 'aguardando_conferencia') && <LinhaDoTempo pedido={pedido} />}
        {pago && <Entrega pedido={pedido} />}

        <Itens pedido={pedido} pago={pago} />

        <div className="grid gap-2 print:hidden">
          {pago && (
            <button
              onClick={() => window.print()}
              className="flex min-h-[48px] items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 font-semibold"
            >
              <Printer size={17} /> Salvar comprovante
            </button>
          )}
          <FalarComLoja pedido={pedido} slug={slug} />
          <Link
            to={`/vitrine/${slug}/meus-pedidos`}
            className="flex min-h-[44px] items-center justify-center gap-2 text-sm text-slate-400"
          >
            <Search size={15} /> Ver todos os meus pedidos
          </Link>
        </div>
      </div>
    </Casca>
  )
}

// ------------------------------------------------------------------ Pagamento

function Pagamento({
  pedido, slug, aoAtualizar,
}: {
  pedido: PedidoPublico
  slug: string
  aoAtualizar: (pedido: PedidoPublico) => void
}) {
  const [qr, setQr] = useState('')
  const [copiado, setCopiado] = useState(false)
  const restante = useContagem(pedido.expira_em)

  useEffect(() => {
    if (!pedido.pix_copia_cola) return
    QRCode.toDataURL(pedido.pix_copia_cola, { margin: 1, width: 260, errorCorrectionLevel: 'M' })
      .then(setQr)
      .catch(() => setQr(''))
  }, [pedido.pix_copia_cola])

  const cancelar = useMutation({
    mutationFn: () => api.post<PedidoPublico>(`/vitrine/${slug}/pedidos/${pedido.token}/cancelar/`, {}, true),
    onSuccess: aoAtualizar,
  })

  async function copiar() {
    if (!pedido.pix_copia_cola) return
    try {
      await navigator.clipboard.writeText(pedido.pix_copia_cola)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 3000)
    } catch {
      setCopiado(false)
    }
  }

  if (!pedido.pix_copia_cola) {
    return (
      <Aviso cor="ambar" icone={<AlertCircle size={18} />} titulo="Pix indisponível">
        A loja ainda não terminou de configurar o Pix. Fale com ela pelo WhatsApp informando o
        código {pedido.codigo}.
      </Aviso>
    )
  }

  return (
    <section className="space-y-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
      <div className="flex items-baseline justify-between">
        <h2 className="font-semibold">Pague com Pix</h2>
        <span className="numerico text-2xl font-bold">{formatarMoeda(pedido.total_centavos)}</span>
      </div>

      <div className="flex items-center gap-2 rounded-xl bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
        <Clock size={16} className="shrink-0" />
        {restante > 0 ? (
          <span>
            Itens reservados por mais <strong className="numerico">{formatarRestante(restante)}</strong>
          </span>
        ) : (
          <span>A reserva venceu. Se já pagou, envie o comprovante abaixo.</span>
        )}
      </div>

      {qr && (
        <div className="mx-auto w-fit rounded-xl bg-white p-3">
          <img src={qr} alt="QR Code do Pix" width={220} height={220} className="h-[220px] w-[220px]" />
        </div>
      )}

      <button
        onClick={copiar}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-4
                   text-base font-semibold text-white active:bg-emerald-700"
      >
        {copiado ? <CheckCircle2 size={18} /> : <Copy size={18} />}
        {copiado ? 'Código copiado!' : 'Copiar código Pix'}
      </button>

      <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-300">
        <li>No app do banco, escolha <strong>Pix → Pagar com QR Code</strong> ou <strong>Pix Copia e Cola</strong>.</li>
        <li>
          Confira o valor e o recebedor{pedido.loja.pix_nome ? <> (<strong>{pedido.loja.pix_nome}</strong>)</> : ''}.
        </li>
        <li>Depois de pagar, envie o comprovante aqui embaixo.</li>
      </ol>

      <EnviarComprovante pedido={pedido} slug={slug} aoAtualizar={aoAtualizar} />

      <button
        onClick={() => cancelar.mutate()}
        disabled={cancelar.isPending}
        className="min-h-[44px] w-full text-sm text-slate-500 active:text-rose-400"
      >
        {cancelar.isPending ? 'Cancelando…' : 'Desistir e cancelar o pedido'}
      </button>
    </section>
  )
}

function EnviarComprovante({
  pedido, slug, aoAtualizar,
}: {
  pedido: PedidoPublico
  slug: string
  aoAtualizar: (pedido: PedidoPublico) => void
}) {
  const entrada = useRef<HTMLInputElement>(null)
  const [arquivo, setArquivo] = useState<File | null>(null)

  const enviar = useMutation({
    mutationFn: (comArquivo: boolean) =>
      enviarArquivo<PedidoPublico>(
        `/vitrine/${slug}/pedidos/${pedido.token}/pagamento/`,
        comArquivo && arquivo ? { comprovante: arquivo } : {},
        'POST',
      ),
    onSuccess: aoAtualizar,
  })

  return (
    <div className="space-y-2 border-t border-white/10 pt-4">
      <input
        ref={entrada}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(evento) => setArquivo(evento.target.files?.[0] ?? null)}
      />
      <button
        onClick={() => entrada.current?.click()}
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-white/20
                   px-4 py-3.5 text-sm text-slate-200 active:bg-white/5"
      >
        <Upload size={17} />
        {arquivo ? arquivo.name : 'Escolher print do comprovante'}
      </button>
      <button
        onClick={() => enviar.mutate(true)}
        disabled={enviar.isPending}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-marca-700 px-4 py-3.5
                   font-semibold text-white active:bg-marca-800 disabled:opacity-50"
      >
        {enviar.isPending && <Loader2 size={17} className="animate-spin" />}
        {arquivo ? 'Enviar comprovante' : 'Já paguei'}
      </button>
      {enviar.error && (
        <p className="text-sm text-rose-300">
          {enviar.error instanceof ErroApi ? enviar.error.message : 'Falha ao enviar. Tente de novo.'}
        </p>
      )}
    </div>
  )
}

function EmConferencia({ pedido }: { pedido: PedidoPublico }) {
  return (
    <Aviso cor="azul" icone={<Loader2 size={18} className="animate-spin" />} titulo="Conferindo seu Pix">
      Recebemos seu aviso de pagamento{pedido.comprovante_enviado ? ' e o comprovante' : ''}. A loja
      está conferindo — esta página atualiza sozinha quando for confirmado.
    </Aviso>
  )
}

function Expirado({
  pedido, slug, aoAtualizar,
}: {
  pedido: PedidoPublico
  slug: string
  aoAtualizar: (pedido: PedidoPublico) => void
}) {
  return (
    <section className="space-y-3 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
      <div className="flex gap-2 text-slate-300">
        <Clock size={18} className="mt-0.5 shrink-0" />
        <div>
          <h2 className="font-semibold text-slate-100">A reserva venceu</h2>
          <p className="text-sm">
            Os itens voltaram para o catálogo. Se você <strong>já pagou</strong>, envie o
            comprovante: a loja confere e confirma se ainda houver estoque.
          </p>
        </div>
      </div>
      <EnviarComprovante pedido={pedido} slug={slug} aoAtualizar={aoAtualizar} />
    </section>
  )
}

// ------------------------------------------------------------------ Acompanhamento

function LinhaDoTempo({ pedido }: { pedido: PedidoPublico }) {
  const etapas = etapasDoPedido(pedido.tipo_entrega)
  const atual = indiceEtapa(pedido.status, pedido.tipo_entrega)
  return (
    <ol className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 print:hidden">
      {etapas.map((etapa, indice) => {
        const feita = indice <= atual
        return (
          <li key={etapa.status} className="flex items-center gap-3 py-1.5">
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                feita ? 'bg-emerald-500 text-slate-950' : 'bg-white/10 text-slate-500'
              } ${indice === atual ? 'ring-4 ring-emerald-500/25' : ''}`}
            >
              {feita ? '✓' : indice + 1}
            </span>
            <span className={feita ? 'font-medium text-slate-100' : 'text-slate-500'}>{etapa.rotulo}</span>
          </li>
        )
      })}
    </ol>
  )
}

function Entrega({ pedido }: { pedido: PedidoPublico }) {
  const ehEntrega = pedido.tipo_entrega === 'entrega'
  return (
    <section className="space-y-2 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 print:border-black print:bg-white">
      <div className="flex items-center gap-2 font-semibold text-emerald-200 print:text-black">
        <CheckCircle2 size={18} /> Pagamento confirmado
        {pedido.venda_numero && <span className="text-sm font-normal">· venda nº {pedido.venda_numero}</span>}
      </div>
      {pedido.pago_em && (
        <p className="text-sm text-emerald-100/80 print:text-black">Pago em {formatarDataHora(pedido.pago_em)}</p>
      )}
      {pedido.status !== 'entregue' && pedido.previsao_entrega && (
        <p className="flex items-center gap-2 text-sm text-slate-100 print:text-black">
          <Bike size={16} />
          {ehEntrega ? 'Previsão de entrega' : 'Pronto a partir de'}:{' '}
          <strong>{formatarDataHora(pedido.previsao_entrega)}</strong>
        </p>
      )}
      {pedido.status === 'entregue' && pedido.entregue_em && (
        <p className="text-sm text-slate-100 print:text-black">
          {ehEntrega ? 'Entregue' : 'Retirado'} em {formatarDataHora(pedido.entregue_em)}
        </p>
      )}
      {pedido.recado_loja && (
        <p className="rounded-lg bg-slate-950/40 px-3 py-2 text-sm text-slate-200 print:text-black">
          <span className="text-xs text-slate-400">Recado da loja: </span>
          {pedido.recado_loja}
        </p>
      )}
      {!ehEntrega && (
        <p className="text-sm text-slate-200 print:text-black">
          Para retirar, informe o código <strong className="font-mono">{pedido.codigo}</strong>.
          {pedido.loja.texto_retirada && <> {pedido.loja.texto_retirada}</>}
        </p>
      )}
    </section>
  )
}

function Itens({ pedido, pago }: { pedido: PedidoPublico; pago: boolean }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.04] print:border-black print:bg-white">
      <h2 className="border-b border-white/10 px-4 py-3 text-sm font-semibold">
        {pago ? 'Comprovante de compra' : 'Itens do pedido'}
      </h2>
      <ul className="divide-y divide-white/5 px-4">
        {pedido.itens.map((item, indice) => (
          <li key={indice} className="flex justify-between gap-3 py-2.5 text-sm">
            <span>
              {item.quantidade}× {item.descricao}
            </span>
            <span className="numerico shrink-0">{formatarMoeda(item.total_centavos)}</span>
          </li>
        ))}
      </ul>
      <div className="flex items-baseline justify-between border-t border-white/10 px-4 py-3">
        <span className="text-slate-400 print:text-black">Total · {pedido.tipo_entrega_display}</span>
        <span className="numerico text-xl font-bold">{formatarMoeda(pedido.total_centavos)}</span>
      </div>
      {pago && (
        <p className="border-t border-white/10 px-4 py-2 text-[11px] text-slate-500 print:text-black">
          Documento sem valor fiscal. Pedido {pedido.codigo}
          {pedido.venda_numero ? ` · venda nº ${pedido.venda_numero}` : ''} · {pedido.loja.nome}
        </p>
      )}
    </section>
  )
}

function FalarComLoja({ pedido, slug }: { pedido: PedidoPublico; slug: string }) {
  const numero = numeroWhatsApp(pedido.loja.whatsapp)
  if (!numero) return null
  const mensagem =
    pedido.status === 'aguardando_pagamento' || pedido.status === 'aguardando_conferencia'
      ? `Olá! Fiz o pedido ${pedido.codigo} (${formatarMoeda(pedido.total_centavos)}) pela vitrine.`
      : `Olá! Sobre o pedido ${pedido.codigo}.`
  const texto = `${mensagem}\n${linkDoPedido(slug, pedido.token)}`
  return (
    <a
      href={`https://wa.me/${numero}?text=${encodeURIComponent(texto)}`}
      target="_blank"
      rel="noopener noreferrer"
      className="flex min-h-[48px] items-center justify-center gap-2 rounded-xl border border-emerald-500/30
                 bg-emerald-500/10 font-semibold text-emerald-200"
    >
      <MessageCircle size={17} /> Falar com a loja
    </a>
  )
}

// ------------------------------------------------------------------ Meus pedidos

export function MeusPedidosVitrine() {
  const { slug = '' } = useParams()
  usarSemIndexacao()
  const salvo = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem('vape.vitrine.contato') ?? '{}').telefone ?? ''
    } catch {
      return ''
    }
  }, [])
  const [telefone, setTelefone] = useState(formatarTelefone(salvo))

  const consulta = useMutation({
    mutationFn: (numero: string) =>
      api.post<PedidoResumo[]>(`/vitrine/${slug}/meus-pedidos/`, { telefone: numero }, true),
  })

  useEffect(() => {
    document.title = 'Meus pedidos'
    if (salvo.length >= 10) consulta.mutate(salvo)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const digitos = telefone.replace(/\D/g, '')

  return (
    <Casca slug={slug}>
      <h1 className="mb-1 text-2xl font-bold">Meus pedidos</h1>
      <p className="mb-4 text-sm text-slate-400">Informe o telefone usado na compra.</p>

      <form
        onSubmit={(evento) => {
          evento.preventDefault()
          if (digitos.length >= 10) consulta.mutate(digitos)
        }}
        className="flex gap-2"
      >
        <input
          value={telefone}
          onChange={(evento) => setTelefone(formatarTelefone(evento.target.value))}
          inputMode="tel"
          autoComplete="tel-national"
          placeholder="(86) 99999-9999"
          className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-base
                     placeholder:text-slate-500 focus:border-marca-400 focus:outline-none"
        />
        <button
          type="submit"
          disabled={digitos.length < 10 || consulta.isPending}
          className="flex min-h-[48px] shrink-0 items-center gap-2 rounded-xl bg-marca-700 px-4 font-semibold disabled:opacity-40"
        >
          {consulta.isPending ? <Loader2 size={17} className="animate-spin" /> : <Search size={17} />}
          Buscar
        </button>
      </form>

      {consulta.error && (
        <p className="mt-3 text-sm text-rose-300">
          {consulta.error instanceof ErroApi && consulta.error.status === 429
            ? 'Muitas consultas seguidas. Tente de novo mais tarde.'
            : consulta.error.message}
        </p>
      )}

      {consulta.data && (
        <ul className="mt-5 space-y-2">
          {consulta.data.length === 0 && (
            <li className="py-10 text-center text-sm text-slate-500">Nenhum pedido com este telefone.</li>
          )}
          {consulta.data.map((pedido) => (
            <li key={pedido.token}>
              <Link
                to={`/vitrine/${slug}/pedido/${pedido.token}`}
                className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-4 active:bg-white/10"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-mono font-semibold">{pedido.codigo}</p>
                  <p className="text-xs text-slate-400">
                    {formatarDataHora(pedido.criado_em)} · {pedido.quantidade_itens}{' '}
                    {pedido.quantidade_itens === 1 ? 'item' : 'itens'}
                  </p>
                  {pedido.previsao_entrega && !['entregue', 'cancelado'].includes(pedido.status) && (
                    <p className="text-xs text-emerald-300">Previsão: {formatarDataHora(pedido.previsao_entrega)}</p>
                  )}
                </div>
                <div className="text-right">
                  <SeloStatus status={pedido.status} rotulo={pedido.status_display} />
                  <p className="numerico mt-1 text-sm font-semibold">{formatarMoeda(pedido.total_centavos)}</p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Casca>
  )
}

// ------------------------------------------------------------------ Peças

const CORES_ESCURAS: Record<StatusPedido, string> = {
  aguardando_pagamento: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  aguardando_conferencia: 'bg-sky-500/15 text-sky-300 ring-sky-500/30',
  preparando: 'bg-marca-500/20 text-marca-200 ring-marca-400/30',
  pronto_retirada: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
  saiu_entrega: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
  entregue: 'bg-white/10 text-slate-300 ring-white/20',
  cancelado: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  expirado: 'bg-white/10 text-slate-400 ring-white/20',
}

function SeloStatus({ status, rotulo }: { status: StatusPedido; rotulo: string }) {
  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset
                  print:text-black print:ring-black ${CORES_ESCURAS[status]}`}
    >
      {rotulo}
    </span>
  )
}

function Aviso({
  cor, icone, titulo, children,
}: {
  cor: 'ambar' | 'azul' | 'vermelho'
  icone: ReactNode
  titulo: string
  children: ReactNode
}) {
  const estilos = {
    ambar: 'border-amber-500/30 bg-amber-500/10 text-amber-100',
    azul: 'border-sky-500/30 bg-sky-500/10 text-sky-100',
    vermelho: 'border-rose-500/30 bg-rose-500/10 text-rose-100',
  }
  return (
    <section className={`flex gap-3 rounded-2xl border p-4 ${estilos[cor]}`}>
      <span className="mt-0.5 shrink-0">{icone}</span>
      <div>
        <h2 className="font-semibold">{titulo}</h2>
        <p className="mt-0.5 text-sm opacity-90">{children}</p>
      </div>
    </section>
  )
}

function useContagem(alvo: string): number {
  const calcular = () => Math.max(0, Math.floor((new Date(alvo).getTime() - Date.now()) / 1000))
  const [restante, setRestante] = useState(calcular)
  useEffect(() => {
    setRestante(calcular())
    const intervalo = setInterval(() => setRestante(calcular()), 1000)
    return () => clearInterval(intervalo)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alvo])
  return restante
}

function formatarRestante(segundos: number): string {
  const minutos = Math.floor(segundos / 60)
  const resto = segundos % 60
  return `${minutos}:${String(resto).padStart(2, '0')}`
}
