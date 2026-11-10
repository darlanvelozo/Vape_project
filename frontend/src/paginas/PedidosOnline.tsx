/**
 * Pedidos on-line — onde a loja confere o Pix, organiza a entrega e avisa o
 * cliente (ADR-0004).
 *
 * O fluxo do atendente é curto de propósito:
 * 1. "A conferir": abre o comprovante, confere no app do banco, toca em
 *    "Pix recebido". A venda nasce aí (estoque e financeiro, como no PDV).
 * 2. "Em andamento": marca saiu para entrega / pronto para retirada, informa
 *    previsão e recado — o cliente vê tudo na página do pedido.
 * 3. "Rota": as entregas pagas na ordem, com um botão que abre o Google Maps
 *    já com todas as paradas.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import {
  Bike, CheckCircle2, Clock, ExternalLink, FileImage, MapPin, MessageCircle, Navigation,
  RefreshCw, Store, XCircle,
} from 'lucide-react'
import { useState } from 'react'

import { Alerta, Botao, CabecalhoPagina, Campo, Carregando, Modal, Selo, Vazio } from '../componentes/ui'
import { ErroApi, api, armazenamento, querystring } from '../lib/api'
import { useAutenticacao } from '../lib/auth'
import { formatarDataHora, formatarMoeda, formatarTelefone } from '../lib/formato'
import {
  COR_STATUS, PEDIDO_PAGO, linkDoPedido, linkWhatsAppCliente, rotasNoMaps,
} from '../lib/pedidos'
import type { PedidoPainel, ResumoPedidos, StatusPedido } from '../lib/pedidos'
import type { Pagina } from '../lib/tipos'

type Aba = 'pendentes' | 'andamento' | 'rota' | 'concluidos' | 'encerrados'

const ABAS: { chave: Aba; rotulo: string }[] = [
  { chave: 'pendentes', rotulo: 'A conferir' },
  { chave: 'andamento', rotulo: 'Em andamento' },
  { chave: 'rota', rotulo: 'Rota de entrega' },
  { chave: 'concluidos', rotulo: 'Entregues' },
  { chave: 'encerrados', rotulo: 'Cancelados' },
]

const BASE = import.meta.env.VITE_API_URL ?? '/api'

export function PedidosOnline() {
  const { usuario } = useAutenticacao()
  const [aba, setAba] = useState<Aba>('pendentes')
  const [aprovando, setAprovando] = useState<PedidoPainel | null>(null)
  const [cancelando, setCancelando] = useState<PedidoPainel | null>(null)
  const [comprovante, setComprovante] = useState<PedidoPainel | null>(null)
  const slug = usuario?.loja.slug ?? ''

  const resumo = useQuery({
    queryKey: ['pedidos-online', 'resumo'],
    queryFn: () => api.get<ResumoPedidos>('/pedidos-online/resumo/'),
    refetchInterval: 30000,
  })

  const lista = useQuery({
    queryKey: ['pedidos-online', aba],
    queryFn: () =>
      api.get<Pagina<PedidoPainel>>(
        `/pedidos-online/${querystring(
          aba === 'rota' ? { entregas: 1, tamanho_pagina: 100 } : { situacao: aba },
        )}`,
      ),
    refetchInterval: 30000,
  })

  const pedidos = lista.data?.results ?? []
  const pendentes = (resumo.data?.aguardando_pagamento ?? 0) + (resumo.data?.aguardando_conferencia ?? 0)

  return (
    <div>
      <CabecalhoPagina
        titulo="Pedidos on-line"
        descricao="Compras feitas pela vitrine com Pix. Confira o pagamento, prepare e acompanhe a entrega."
        acoes={
          <Botao
            variante="secundario"
            icone={<RefreshCw size={15} className={lista.isFetching ? 'animate-spin' : ''} />}
            onClick={() => {
              lista.refetch()
              resumo.refetch()
            }}
          >
            Atualizar
          </Botao>
        }
      />

      <div className="mb-4 flex gap-1 overflow-x-auto border-b border-slate-200">
        {ABAS.map(({ chave, rotulo }) => {
          const contador =
            chave === 'pendentes' ? pendentes : chave === 'andamento' ? resumo.data?.em_andamento ?? 0 : 0
          return (
            <button
              key={chave}
              onClick={() => setAba(chave)}
              className={clsx(
                '-mb-px flex min-h-[44px] shrink-0 items-center gap-1.5 border-b-2 px-3 text-sm font-medium',
                aba === chave
                  ? 'border-marca-700 text-marca-800'
                  : 'border-transparent text-slate-500 hover:text-slate-700',
              )}
            >
              {rotulo}
              {contador > 0 && (
                <span
                  className={clsx(
                    'rounded-full px-1.5 text-xs',
                    chave === 'pendentes' ? 'bg-amber-500 text-white' : 'bg-slate-200 text-slate-700',
                  )}
                >
                  {contador}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {aba === 'rota' && pedidos.length > 0 && <BotoesDeRota pedidos={pedidos} />}

      {lista.isLoading ? (
        <Carregando />
      ) : pedidos.length === 0 ? (
        <Vazio
          titulo={aba === 'pendentes' ? 'Nenhum pedido esperando conferência' : 'Nada por aqui'}
          descricao={
            aba === 'pendentes'
              ? 'Quando um cliente finalizar uma compra na vitrine, ela aparece aqui.'
              : aba === 'rota'
                ? 'Entregas pagas e ainda não entregues aparecem aqui, na ordem de pagamento.'
                : undefined
          }
        />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {pedidos.map((pedido, indice) => (
            <CartaoPedido
              key={pedido.id}
              pedido={pedido}
              slug={slug}
              ordem={aba === 'rota' ? indice + 1 : undefined}
              podeGerenciar={usuario?.pode_gerenciar ?? false}
              aoAprovar={() => setAprovando(pedido)}
              aoCancelar={() => setCancelando(pedido)}
              aoVerComprovante={() => setComprovante(pedido)}
            />
          ))}
        </div>
      )}

      {aprovando && <ModalAprovar pedido={aprovando} aoFechar={() => setAprovando(null)} />}
      {cancelando && <ModalCancelar pedido={cancelando} aoFechar={() => setCancelando(null)} />}
      {comprovante && <ModalComprovante pedido={comprovante} aoFechar={() => setComprovante(null)} />}
    </div>
  )
}

function usarAtualizacao() {
  const clienteQuery = useQueryClient()
  return () => clienteQuery.invalidateQueries({ queryKey: ['pedidos-online'] })
}

// ------------------------------------------------------------------ Cartão

function CartaoPedido({
  pedido, slug, ordem, podeGerenciar, aoAprovar, aoCancelar, aoVerComprovante,
}: {
  pedido: PedidoPainel
  slug: string
  ordem?: number
  podeGerenciar: boolean
  aoAprovar: () => void
  aoCancelar: () => void
  aoVerComprovante: () => void
}) {
  const pago = PEDIDO_PAGO.includes(pedido.status)
  const aConferir = ['aguardando_pagamento', 'aguardando_conferencia', 'expirado'].includes(pedido.status)
  const podeCancelar =
    !['cancelado', 'entregue'].includes(pedido.status) && (!pago || podeGerenciar)

  return (
    <article className="cartao overflow-hidden">
      <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div className="min-w-0">
          <p className="flex items-center gap-2 font-semibold text-slate-900">
            {ordem && (
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-marca-700 text-xs text-white">
                {ordem}
              </span>
            )}
            <span className="font-mono">{pedido.codigo}</span>
            <span className="truncate font-normal text-slate-600">· {pedido.codinome}</span>
          </p>
          <p className="text-xs text-slate-500">
            {formatarDataHora(pedido.criado_em)} · {formatarTelefone(pedido.telefone)}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <Selo cor={COR_STATUS[pedido.status]}>{pedido.status_display}</Selo>
          <p className="numerico mt-1 font-bold text-slate-900">{formatarMoeda(pedido.total_centavos)}</p>
        </div>
      </header>

      <div className="space-y-3 px-4 py-3 text-sm">
        <ul className="space-y-0.5 text-slate-700">
          {pedido.itens.map((item, indice) => (
            <li key={indice}>
              {item.quantidade}× {item.descricao}
            </li>
          ))}
        </ul>

        {pedido.tipo_entrega === 'entrega' ? (
          <div className="flex items-start gap-2 rounded-lg bg-slate-50 px-3 py-2">
            <MapPin size={16} className="mt-0.5 shrink-0 text-marca-700" />
            <div className="min-w-0 flex-1">
              <p className="font-medium text-slate-800">Entrega</p>
              {pedido.referencia && <p className="text-slate-600">Ref.: {pedido.referencia}</p>}
              {pedido.endereco && <p className="text-slate-600">{pedido.endereco}</p>}
              {pedido.latitude && (
                <p className="text-xs text-slate-400">
                  GPS do cliente{pedido.precisao_m ? ` (±${pedido.precisao_m} m)` : ''}
                </p>
              )}
            </div>
            {pedido.maps_url && (
              <a
                href={pedido.maps_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex min-h-[44px] shrink-0 items-center gap-1 rounded-lg px-2 text-xs font-medium text-marca-700"
              >
                Mapa <ExternalLink size={13} />
              </a>
            )}
          </div>
        ) : (
          <p className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-slate-700">
            <Store size={16} className="text-marca-700" /> Retirada na loja
          </p>
        )}

        {pedido.observacoes && (
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-900">“{pedido.observacoes}”</p>
        )}

        {aConferir && (
          <div className="space-y-2">
            {pedido.status === 'aguardando_pagamento' && (
              <p className="flex items-center gap-1.5 text-xs text-slate-500">
                <Clock size={13} /> Reserva até {formatarDataHora(pedido.expira_em)} · cliente ainda não
                avisou que pagou
              </p>
            )}
            {pedido.status === 'expirado' && (
              <p className="text-xs text-slate-500">
                Reserva vencida. Aprove só se o Pix tiver caído — o estoque é conferido na aprovação.
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {pedido.tem_comprovante && (
                <Botao variante="secundario" icone={<FileImage size={15} />} onClick={aoVerComprovante}>
                  Ver comprovante
                </Botao>
              )}
              <Botao variante="sucesso" icone={<CheckCircle2 size={15} />} onClick={aoAprovar}>
                Pix recebido
              </Botao>
            </div>
          </div>
        )}

        {pago && <ControleDeEntrega pedido={pedido} slug={slug} />}

        {pedido.status === 'cancelado' && pedido.motivo_cancelamento && (
          <p className="text-xs text-slate-500">Motivo: {pedido.motivo_cancelamento}</p>
        )}
      </div>

      {(podeCancelar || pago) && (
        <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 px-4 py-2">
          <span className="text-xs text-slate-400">
            {pedido.venda_numero ? `Venda nº ${pedido.venda_numero}` : ''}
            {pedido.aprovado_por_nome ? ` · aprovado por ${pedido.aprovado_por_nome}` : ''}
          </span>
          {podeCancelar && (
            <button
              onClick={aoCancelar}
              className="min-h-[44px] px-2 text-xs font-medium text-rose-600 hover:text-rose-700"
            >
              Cancelar pedido
            </button>
          )}
        </footer>
      )}
    </article>
  )
}

// ------------------------------------------------------------------ Entrega

function paraCampoLocal(iso: string | null): string {
  if (!iso) return ''
  const data = new Date(iso)
  const ajuste = data.getTimezoneOffset() * 60000
  return new Date(data.getTime() - ajuste).toISOString().slice(0, 16)
}

function ControleDeEntrega({ pedido, slug }: { pedido: PedidoPainel; slug: string }) {
  const atualizar = usarAtualizacao()
  const [previsao, setPrevisao] = useState(paraCampoLocal(pedido.previsao_entrega))
  const [recado, setRecado] = useState(pedido.recado_loja)

  const salvar = useMutation({
    mutationFn: (dados: { status?: StatusPedido; previsao_entrega?: string | null; recado_loja?: string }) =>
      api.post<PedidoPainel>(`/pedidos-online/${pedido.id}/entrega/`, dados),
    onSuccess: atualizar,
  })

  const ehEntrega = pedido.tipo_entrega === 'entrega'
  const passos: { status: StatusPedido; rotulo: string; icone: JSX.Element }[] = [
    { status: 'preparando', rotulo: 'Preparando', icone: <Clock size={15} /> },
    ehEntrega
      ? { status: 'saiu_entrega', rotulo: 'Saiu p/ entrega', icone: <Bike size={15} /> }
      : { status: 'pronto_retirada', rotulo: 'Pronto p/ retirar', icone: <Store size={15} /> },
    { status: 'entregue', rotulo: ehEntrega ? 'Entregue' : 'Retirado', icone: <CheckCircle2 size={15} /> },
  ]

  function emMinutos(minutos: number) {
    const alvo = new Date(Date.now() + minutos * 60000)
    setPrevisao(paraCampoLocal(alvo.toISOString()))
  }

  const mudou =
    previsao !== paraCampoLocal(pedido.previsao_entrega) || recado.trim() !== pedido.recado_loja

  const mensagem = (() => {
    const link = linkDoPedido(slug, pedido.token)
    const previsto = pedido.previsao_entrega ? ` Previsão: ${formatarDataHora(pedido.previsao_entrega)}.` : ''
    switch (pedido.status) {
      case 'saiu_entrega':
        return `Olá, ${pedido.codinome}! Seu pedido ${pedido.codigo} saiu para entrega.${previsto}\nAcompanhe: ${link}`
      case 'pronto_retirada':
        return `Olá, ${pedido.codinome}! Seu pedido ${pedido.codigo} está pronto para retirada. Informe o código ${pedido.codigo}.\n${link}`
      case 'entregue':
        return `Obrigado, ${pedido.codinome}! Pedido ${pedido.codigo} entregue. Seu comprovante: ${link}`
      default:
        return `Olá, ${pedido.codinome}! Pagamento do pedido ${pedido.codigo} confirmado ✅ Já estamos preparando.${previsto}\nComprovante e acompanhamento: ${link}`
    }
  })()

  return (
    <div className="space-y-3 rounded-lg border border-slate-200 p-3">
      <div className="grid grid-cols-3 gap-1.5">
        {passos.map((passo) => (
          <button
            key={passo.status}
            onClick={() => salvar.mutate({ status: passo.status })}
            disabled={salvar.isPending}
            className={clsx(
              'flex min-h-[44px] flex-col items-center justify-center gap-0.5 rounded-lg border px-1 text-xs font-medium',
              pedido.status === passo.status
                ? 'border-marca-700 bg-marca-700 text-white'
                : 'border-slate-200 text-slate-600 hover:bg-slate-50',
            )}
          >
            {passo.icone}
            {passo.rotulo}
          </button>
        ))}
      </div>

      {pedido.status !== 'entregue' && (
        <div className="space-y-2">
          <div>
            <label className="rotulo" htmlFor={`previsao-${pedido.id}`}>
              {ehEntrega ? 'Previsão de entrega' : 'Pronto a partir de'}
            </label>
            <input
              id={`previsao-${pedido.id}`}
              type="datetime-local"
              value={previsao}
              onChange={(evento) => setPrevisao(evento.target.value)}
              className="campo"
            />
            <div className="mt-1.5 flex gap-1.5">
              {[30, 60, 120].map((minutos) => (
                <button
                  key={minutos}
                  type="button"
                  onClick={() => emMinutos(minutos)}
                  className="min-h-[36px] flex-1 rounded-md border border-slate-200 text-xs text-slate-600 hover:bg-slate-50"
                >
                  +{minutos < 60 ? `${minutos} min` : `${minutos / 60} h`}
                </button>
              ))}
            </div>
          </div>
          <Campo
            rotulo="Recado para o cliente"
            value={recado}
            maxLength={200}
            onChange={(evento) => setRecado(evento.target.value)}
            placeholder="Ex.: motoboy João, moto vermelha"
          />
          {mudou && (
            <Botao
              tamanho="pequeno"
              carregando={salvar.isPending}
              onClick={() =>
                salvar.mutate({
                  previsao_entrega: previsao ? new Date(previsao).toISOString() : null,
                  recado_loja: recado,
                })
              }
            >
              Salvar previsão e recado
            </Botao>
          )}
        </div>
      )}

      {salvar.error && (
        <Alerta>{salvar.error instanceof ErroApi ? salvar.error.message : 'Falha ao salvar.'}</Alerta>
      )}

      <a
        href={linkWhatsAppCliente(pedido.telefone, mensagem)}
        target="_blank"
        rel="noopener noreferrer"
        className="flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 text-sm font-semibold text-white hover:bg-emerald-700"
      >
        <MessageCircle size={16} /> Avisar cliente no WhatsApp
      </a>
    </div>
  )
}

function BotoesDeRota({ pedidos }: { pedidos: PedidoPainel[] }) {
  const rotas = rotasNoMaps(pedidos)
  const semLocal = pedidos.filter((pedido) => !pedido.latitude && !pedido.endereco.trim()).length
  if (!rotas.length) return null
  return (
    <div className="mb-4 space-y-2 rounded-xl border border-marca-200 bg-marca-50 p-3">
      <div className="flex flex-wrap gap-2">
        {rotas.map((rota, indice) => (
          <a key={rota} href={rota} target="_blank" rel="noopener noreferrer" className="grow sm:grow-0">
            <Botao className="w-full" icone={<Navigation size={15} />}>
              {rotas.length > 1 ? `Abrir rota ${indice + 1} no Maps` : 'Abrir rota no Maps'}
            </Botao>
          </a>
        ))}
      </div>
      <p className="text-xs text-marca-900">
        {pedidos.length} entrega(s) na ordem de pagamento. A rota parte de onde o celular estiver.
        {semLocal > 0 && ` ${semLocal} pedido(s) sem localização ficaram fora — combine pelo WhatsApp.`}
      </p>
    </div>
  )
}

// ------------------------------------------------------------------ Modais

function ModalAprovar({ pedido, aoFechar }: { pedido: PedidoPainel; aoFechar: () => void }) {
  const atualizar = usarAtualizacao()
  const aprovar = useMutation({
    mutationFn: () => api.post<PedidoPainel>(`/pedidos-online/${pedido.id}/aprovar/`, {}),
    onSuccess: () => {
      atualizar()
      aoFechar()
    },
  })
  return (
    <Modal aberto aoFechar={aoFechar} titulo={`Confirmar Pix do pedido ${pedido.codigo}`}>
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          Confira no app do banco se caiu um Pix de{' '}
          <strong className="numerico text-slate-900">{formatarMoeda(pedido.total_centavos)}</strong>. O
          código <strong className="font-mono">{pedido.codigo}</strong> aparece na descrição do Pix na
          maioria dos bancos.
        </p>
        <p className="text-sm text-slate-600">
          Ao confirmar, o pedido vira a venda paga em Pix: o estoque baixa e a receita entra no
          financeiro.
        </p>
        {aprovar.error && (
          <Alerta>{aprovar.error instanceof ErroApi ? aprovar.error.message : 'Falha ao aprovar.'}</Alerta>
        )}
        <div className="acoes-modal flex gap-2">
          <Botao variante="secundario" onClick={aoFechar} className="flex-1">
            Voltar
          </Botao>
          <Botao
            variante="sucesso"
            carregando={aprovar.isPending}
            onClick={() => aprovar.mutate()}
            className="flex-1"
            icone={<CheckCircle2 size={16} />}
          >
            Pix conferido
          </Botao>
        </div>
      </div>
    </Modal>
  )
}

function ModalCancelar({ pedido, aoFechar }: { pedido: PedidoPainel; aoFechar: () => void }) {
  const atualizar = usarAtualizacao()
  const [motivo, setMotivo] = useState('')
  const pago = PEDIDO_PAGO.includes(pedido.status)
  const cancelar = useMutation({
    mutationFn: () => api.post<PedidoPainel>(`/pedidos-online/${pedido.id}/cancelar/`, { motivo }),
    onSuccess: () => {
      atualizar()
      aoFechar()
    },
  })
  return (
    <Modal aberto aoFechar={aoFechar} titulo={`Cancelar pedido ${pedido.codigo}`}>
      <div className="space-y-4">
        {pago ? (
          <Alerta tipo="aviso">
            Este pedido já foi pago: a venda nº {pedido.venda_numero} será estornada (estoque volta e a
            receita sai do financeiro). A devolução do Pix ao cliente é feita por você, no banco.
          </Alerta>
        ) : (
          <p className="text-sm text-slate-600">Os itens reservados voltam para a vitrine.</p>
        )}
        <Campo
          rotulo="Motivo (o cliente vê)"
          value={motivo}
          maxLength={200}
          onChange={(evento) => setMotivo(evento.target.value)}
          placeholder="Ex.: Pix não identificado"
        />
        {cancelar.error && (
          <Alerta>{cancelar.error instanceof ErroApi ? cancelar.error.message : 'Falha ao cancelar.'}</Alerta>
        )}
        <div className="acoes-modal flex gap-2">
          <Botao variante="secundario" onClick={aoFechar} className="flex-1">
            Voltar
          </Botao>
          <Botao
            variante="perigo"
            carregando={cancelar.isPending}
            onClick={() => cancelar.mutate()}
            className="flex-1"
            icone={<XCircle size={16} />}
          >
            Cancelar pedido
          </Botao>
        </div>
      </div>
    </Modal>
  )
}

/**
 * O comprovante não está em /media/ (público): vem da API autenticada e é
 * mostrado a partir de um blob local.
 */
function ModalComprovante({ pedido, aoFechar }: { pedido: PedidoPainel; aoFechar: () => void }) {
  const { data: url, isLoading, isError } = useQuery({
    queryKey: ['comprovante', pedido.id],
    queryFn: async () => {
      const resposta = await fetch(`${BASE}/pedidos-online/${pedido.id}/comprovante/`, {
        headers: { Authorization: `Bearer ${armazenamento.access() ?? ''}` },
      })
      if (!resposta.ok) throw new Error('falha')
      return URL.createObjectURL(await resposta.blob())
    },
    staleTime: Infinity,
  })
  return (
    <Modal aberto aoFechar={aoFechar} titulo={`Comprovante — ${pedido.codigo}`}>
      {isLoading && <Carregando />}
      {isError && <Alerta>Não foi possível abrir o comprovante. Recarregue a página.</Alerta>}
      {url && (
        <div className="space-y-2">
          <img src={url} alt="Comprovante do Pix" className="mx-auto max-h-[60vh] rounded-lg border" />
          <p className="text-center text-xs text-slate-500">
            Enviado em {formatarDataHora(pedido.comprovante_enviado_em)} · valor esperado{' '}
            {formatarMoeda(pedido.total_centavos)}
          </p>
        </div>
      )}
    </Modal>
  )
}
