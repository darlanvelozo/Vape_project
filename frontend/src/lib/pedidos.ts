/**
 * Pedido on-line da vitrine (ADR-0004): tipos e regras compartilhadas entre a
 * página do cliente e o painel da loja.
 */

import { numeroWhatsApp } from './formato'

export type StatusPedido =
  | 'aguardando_pagamento'
  | 'aguardando_conferencia'
  | 'preparando'
  | 'pronto_retirada'
  | 'saiu_entrega'
  | 'entregue'
  | 'cancelado'
  | 'expirado'

export type TipoEntrega = 'entrega' | 'retirada'

export interface ItemPedido {
  descricao: string
  quantidade: number
  preco_unitario_centavos: number
  total_centavos: number
}

/** O que o cliente vê pelo link do pedido. */
export interface PedidoPublico {
  codigo: string
  token: string
  codinome: string
  telefone: string
  status: StatusPedido
  status_display: string
  tipo_entrega: TipoEntrega
  tipo_entrega_display: string
  itens: ItemPedido[]
  total_centavos: number
  criado_em: string
  expira_em: string
  pix_copia_cola: string | null
  comprovante_enviado: boolean
  pago_em: string | null
  venda_numero: number | null
  previsao_entrega: string | null
  recado_loja: string
  saiu_em: string | null
  entregue_em: string | null
  cancelado_em: string | null
  motivo_cancelamento: string
  loja: { nome: string; slug: string; whatsapp: string; pix_nome: string; texto_retirada?: string }
}

export interface PedidoResumo {
  codigo: string
  token: string
  status: StatusPedido
  status_display: string
  tipo_entrega: TipoEntrega
  total_centavos: number
  quantidade_itens: number
  criado_em: string
  previsao_entrega: string | null
}

/** O que a loja vê no painel. */
export interface PedidoPainel {
  id: number
  codigo: string
  token: string
  telefone: string
  codinome: string
  status: StatusPedido
  status_display: string
  tipo_entrega: TipoEntrega
  tipo_entrega_display: string
  latitude: string | null
  longitude: string | null
  precisao_m: number | null
  endereco: string
  referencia: string
  observacoes: string
  maps_url: string | null
  itens: ItemPedido[]
  total_centavos: number
  criado_em: string
  expira_em: string
  tem_comprovante: boolean
  comprovante_enviado_em: string | null
  venda: number | null
  venda_numero: number | null
  pago_em: string | null
  aprovado_por_nome: string | null
  previsao_entrega: string | null
  recado_loja: string
  saiu_em: string | null
  entregue_em: string | null
  cancelado_em: string | null
  motivo_cancelamento: string
}

export interface ResumoPedidos {
  aguardando_pagamento: number
  aguardando_conferencia: number
  em_andamento: number
  entregues_hoje: number
}

export type CorStatus = 'cinza' | 'verde' | 'vermelho' | 'ambar' | 'azul' | 'roxo'

export const COR_STATUS: Record<StatusPedido, CorStatus> = {
  aguardando_pagamento: 'ambar',
  aguardando_conferencia: 'azul',
  preparando: 'roxo',
  pronto_retirada: 'verde',
  saiu_entrega: 'verde',
  entregue: 'cinza',
  cancelado: 'vermelho',
  expirado: 'cinza',
}

/** Etapas mostradas ao cliente, na ordem, conforme o tipo de recebimento. */
export function etapasDoPedido(tipo: TipoEntrega): { status: StatusPedido; rotulo: string }[] {
  return [
    { status: 'aguardando_pagamento', rotulo: 'Pedido feito' },
    { status: 'aguardando_conferencia', rotulo: 'Pagamento em conferência' },
    { status: 'preparando', rotulo: 'Pago — preparando' },
    tipo === 'entrega'
      ? { status: 'saiu_entrega', rotulo: 'Saiu para entrega' }
      : { status: 'pronto_retirada', rotulo: 'Pronto para retirada' },
    { status: 'entregue', rotulo: tipo === 'entrega' ? 'Entregue' : 'Retirado' },
  ]
}

/** Índice da etapa atual na linha do tempo (−1 para cancelado/expirado). */
export function indiceEtapa(status: StatusPedido, tipo: TipoEntrega): number {
  return etapasDoPedido(tipo).findIndex((etapa) => etapa.status === status)
}

export const PEDIDO_PAGO: StatusPedido[] = ['preparando', 'pronto_retirada', 'saiu_entrega', 'entregue']

/** Ponto da rota: coordenada se houver, senão o endereço escrito. */
function pontoDaRota(pedido: Pick<PedidoPainel, 'latitude' | 'longitude' | 'endereco'>): string | null {
  if (pedido.latitude && pedido.longitude) return `${pedido.latitude},${pedido.longitude}`
  if (pedido.endereco.trim()) return pedido.endereco.trim()
  return null
}

/** O link de rotas do Google Maps aceita até 9 paradas intermediárias. */
export const PARADAS_POR_ROTA = 10

/**
 * Links de rota no Google Maps, em blocos de até 10 entregas.
 *
 * Sem `origin` o Maps parte da localização atual do celular de quem abre —
 * que é exatamente o motoboy saindo da loja.
 */
export function rotasNoMaps(
  pedidos: Pick<PedidoPainel, 'latitude' | 'longitude' | 'endereco'>[],
): string[] {
  const pontos = pedidos.map(pontoDaRota).filter((ponto): ponto is string => Boolean(ponto))
  const rotas: string[] = []
  for (let inicio = 0; inicio < pontos.length; inicio += PARADAS_POR_ROTA) {
    const bloco = pontos.slice(inicio, inicio + PARADAS_POR_ROTA)
    const destino = bloco[bloco.length - 1]
    const paradas = bloco.slice(0, -1)
    const parametros = new URLSearchParams({ api: '1', destination: destino, travelmode: 'driving' })
    if (paradas.length) parametros.set('waypoints', paradas.join('|'))
    rotas.push(`https://www.google.com/maps/dir/?${parametros.toString()}`)
  }
  return rotas
}

/** Endereço público da página do pedido — o "comprovante" que o cliente guarda. */
export function linkDoPedido(slug: string, token: string): string {
  return `${window.location.origin}/vitrine/${slug}/pedido/${token}`
}

/** Mensagem que o atendente manda ao cliente depois de aprovar o Pix. */
export function linkWhatsAppCliente(telefone: string, mensagem: string): string {
  return `https://wa.me/${numeroWhatsApp(telefone)}?text=${encodeURIComponent(mensagem)}`
}

const CHAVE_PEDIDOS = 'vape.vitrine.pedidos'

/** Pedidos feitos neste aparelho, para o cliente reabrir sem digitar nada. */
export function pedidosLocais(slug: string): string[] {
  try {
    const salvo = localStorage.getItem(`${CHAVE_PEDIDOS}.${slug}`)
    return salvo ? (JSON.parse(salvo) as string[]) : []
  } catch {
    return []
  }
}

export function lembrarPedido(slug: string, token: string) {
  try {
    const atuais = pedidosLocais(slug).filter((existente) => existente !== token)
    localStorage.setItem(`${CHAVE_PEDIDOS}.${slug}`, JSON.stringify([token, ...atuais].slice(0, 10)))
  } catch {
    /* sem armazenamento: o cliente ainda acha o pedido pelo telefone */
  }
}
