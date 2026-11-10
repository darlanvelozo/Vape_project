/**
 * Finalização da compra na vitrine (ADR-0004).
 *
 * O cliente informa só o necessário: telefone (para a loja falar com ele e
 * para ele achar o pedido depois), um codinome e como quer receber. Na entrega,
 * a localização vem do GPS do celular — um toque, sem digitar endereço — e o
 * ponto de referência resolve o "qual casa".
 */

import { ArrowLeft, Check, Loader2, LocateFixed, MapPin, Store } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { ErroApi, api } from '../lib/api'
import { formatarMoeda, formatarTelefone } from '../lib/formato'
import type { PedidoPublico, TipoEntrega } from '../lib/pedidos'

export interface ConfigVendaOnline {
  aceita_entrega: boolean
  aceita_retirada: boolean
  texto_retirada: string
  reserva_minutos: number
}

interface ItemCheckout {
  opcaoId: number
  quantidade: number
}

interface Localizacao {
  latitude: number
  longitude: number
  precisao: number
}

const CHAVE_CONTATO = 'vape.vitrine.contato'

function contatoSalvo(): { telefone: string; codinome: string } {
  try {
    const salvo = localStorage.getItem(CHAVE_CONTATO)
    if (salvo) return JSON.parse(salvo)
  } catch {
    /* sem armazenamento */
  }
  return { telefone: '', codinome: '' }
}

const estiloCampo =
  'w-full rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-base text-slate-100 ' +
  'placeholder:text-slate-500 focus:border-marca-400 focus:outline-none focus:ring-2 focus:ring-marca-500/30'

export function Checkout({
  slug, itens, totalCentavos, config, aoVoltar, aoConcluir,
}: {
  slug: string
  itens: ItemCheckout[]
  totalCentavos: number
  config: ConfigVendaOnline
  aoVoltar: () => void
  aoConcluir: (pedido: PedidoPublico) => void
}) {
  const inicial = contatoSalvo()
  const [telefone, setTelefone] = useState(formatarTelefone(inicial.telefone))
  const [codinome, setCodinome] = useState(inicial.codinome)
  const [tipo, setTipo] = useState<TipoEntrega>(config.aceita_entrega ? 'entrega' : 'retirada')
  const [local, setLocal] = useState<Localizacao | null>(null)
  const [buscandoLocal, setBuscandoLocal] = useState(false)
  const [erroLocal, setErroLocal] = useState('')
  const [endereco, setEndereco] = useState('')
  const [referencia, setReferencia] = useState('')
  const [observacoes, setObservacoes] = useState('')
  const [maior, setMaior] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<ErroApi | null>(null)

  useEffect(() => {
    if (!config.aceita_entrega) setTipo('retirada')
    else if (!config.aceita_retirada) setTipo('entrega')
  }, [config.aceita_entrega, config.aceita_retirada])

  function pegarLocalizacao() {
    if (!('geolocation' in navigator)) {
      setErroLocal('Este navegador não compartilha localização. Escreva o endereço abaixo.')
      return
    }
    setBuscandoLocal(true)
    setErroLocal('')
    navigator.geolocation.getCurrentPosition(
      (posicao) => {
        setLocal({
          latitude: posicao.coords.latitude,
          longitude: posicao.coords.longitude,
          precisao: Math.round(posicao.coords.accuracy),
        })
        setBuscandoLocal(false)
      },
      (falha) => {
        setBuscandoLocal(false)
        setErroLocal(
          falha.code === falha.PERMISSION_DENIED
            ? 'Localização bloqueada no navegador. Escreva o endereço abaixo.'
            : 'Não conseguimos sua localização agora. Escreva o endereço abaixo.',
        )
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    )
  }

  const digitos = telefone.replace(/\D/g, '')
  const entregaOk = tipo === 'retirada' || local !== null || endereco.trim().length >= 5
  const podeEnviar = digitos.length >= 10 && codinome.trim().length >= 2 && entregaOk && maior

  async function enviar() {
    setEnviando(true)
    setErro(null)
    try {
      const pedido = await api.post<PedidoPublico>(
        `/vitrine/${slug}/pedidos/`,
        {
          telefone: digitos,
          codinome: codinome.trim(),
          declarou_maioridade: maior,
          tipo_entrega: tipo,
          itens: itens.map((item) => ({ variacao: item.opcaoId, quantidade: item.quantidade })),
          ...(tipo === 'entrega' && {
            latitude: local?.latitude ?? null,
            longitude: local?.longitude ?? null,
            precisao_m: local?.precisao ?? null,
            endereco: endereco.trim(),
            referencia: referencia.trim(),
          }),
          observacoes: observacoes.trim(),
        },
        true,
      )
      try {
        localStorage.setItem(CHAVE_CONTATO, JSON.stringify({ telefone: digitos, codinome: codinome.trim() }))
      } catch {
        /* sem armazenamento */
      }
      aoConcluir(pedido)
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha : new ErroApi(0, 'Sem conexão. Tente de novo.'))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="space-y-4 px-4 py-4">
      <button
        onClick={aoVoltar}
        className="-ml-2 flex min-h-[44px] items-center gap-1 px-2 text-sm text-slate-400 active:text-slate-200"
      >
        <ArrowLeft size={16} /> Voltar ao pedido
      </button>

      <Grupo titulo="Seus dados">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-400">Telefone (WhatsApp)</span>
          <input
            value={telefone}
            onChange={(evento) => setTelefone(formatarTelefone(evento.target.value))}
            inputMode="tel"
            autoComplete="tel-national"
            placeholder="(86) 99999-9999"
            className={estiloCampo}
          />
          {erro?.doCampo('telefone') && <ErroCampo>{erro.doCampo('telefone')}</ErroCampo>}
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-400">Nome ou codinome</span>
          <input
            value={codinome}
            onChange={(evento) => setCodinome(evento.target.value)}
            maxLength={60}
            autoComplete="nickname"
            placeholder="Como a loja deve te chamar"
            className={estiloCampo}
          />
        </label>
        <p className="text-xs text-slate-500">
          Com este telefone você acompanha o pedido depois, em “Meus pedidos”.
        </p>
      </Grupo>

      {config.aceita_entrega && config.aceita_retirada && (
        <Grupo titulo="Como quer receber?">
          <div className="grid grid-cols-2 gap-2">
            <Opcao ativa={tipo === 'entrega'} aoEscolher={() => setTipo('entrega')}>
              <MapPin size={18} /> Entrega
            </Opcao>
            <Opcao ativa={tipo === 'retirada'} aoEscolher={() => setTipo('retirada')}>
              <Store size={18} /> Retirada
            </Opcao>
          </div>
        </Grupo>
      )}

      {tipo === 'entrega' ? (
        <Grupo titulo="Onde entregar">
          {local ? (
            <div className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-3">
              <Check size={18} className="shrink-0 text-emerald-300" />
              <div className="min-w-0 flex-1 text-sm">
                <p className="font-medium text-emerald-200">Localização registrada</p>
                <p className="text-xs text-emerald-300/80">precisão de ~{local.precisao} m</p>
              </div>
              <button
                onClick={pegarLocalizacao}
                className="min-h-[44px] shrink-0 px-2 text-xs text-emerald-200 underline"
              >
                Atualizar
              </button>
            </div>
          ) : (
            <button
              onClick={pegarLocalizacao}
              disabled={buscandoLocal}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-marca-700 px-4 py-3.5
                         text-base font-semibold text-white active:bg-marca-800 disabled:opacity-60"
            >
              {buscandoLocal ? <Loader2 size={18} className="animate-spin" /> : <LocateFixed size={18} />}
              {buscandoLocal ? 'Buscando…' : 'Usar minha localização'}
            </button>
          )}
          {erroLocal && <p className="text-xs text-amber-300">{erroLocal}</p>}
          <input
            value={referencia}
            onChange={(evento) => setReferencia(evento.target.value)}
            maxLength={200}
            placeholder="Ponto de referência (ex.: portão azul, ao lado da padaria)"
            className={estiloCampo}
          />
          <input
            value={endereco}
            onChange={(evento) => setEndereco(evento.target.value)}
            maxLength={200}
            autoComplete="street-address"
            placeholder={local ? 'Endereço (opcional)' : 'Rua, número e bairro'}
            className={estiloCampo}
          />
          {erro?.doCampo('endereco') && <ErroCampo>{erro.doCampo('endereco')}</ErroCampo>}
        </Grupo>
      ) : (
        <Grupo titulo="Retirada">
          <p className="text-sm text-slate-300">
            {config.texto_retirada || 'A loja combina com você o local e o horário da retirada.'}
          </p>
        </Grupo>
      )}

      <Grupo titulo="Observações (opcional)">
        <textarea
          value={observacoes}
          onChange={(evento) => setObservacoes(evento.target.value)}
          maxLength={300}
          rows={2}
          placeholder="Algo que a loja precisa saber"
          className={estiloCampo}
        />
      </Grupo>

      <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-3">
        <input
          type="checkbox"
          checked={maior}
          onChange={(evento) => setMaior(evento.target.checked)}
          className="mt-0.5 h-5 w-5 shrink-0 rounded"
        />
        <span className="text-sm text-slate-200">
          Declaro ter <strong>18 anos ou mais</strong>. A venda é proibida para menores.
        </span>
      </label>

      {erro && !erro.doCampo('telefone') && !erro.doCampo('endereco') && (
        <p role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2.5 text-sm text-rose-200">
          {erro.message}
        </p>
      )}

      <div className="area-segura-inferior space-y-2 pt-1">
        <button
          onClick={enviar}
          disabled={!podeEnviar || enviando}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-4
                     text-base font-semibold text-white transition active:bg-emerald-700 disabled:opacity-40"
        >
          {enviando && <Loader2 size={18} className="animate-spin" />}
          Pagar {formatarMoeda(totalCentavos)} com Pix
        </button>
        <p className="text-center text-xs text-slate-500">
          Os itens ficam reservados por {config.reserva_minutos} minutos enquanto você paga.
        </p>
      </div>
    </div>
  )
}

function Grupo({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">{titulo}</h3>
      {children}
    </section>
  )
}

function Opcao({ ativa, aoEscolher, children }: { ativa: boolean; aoEscolher: () => void; children: ReactNode }) {
  return (
    <button
      onClick={aoEscolher}
      aria-pressed={ativa}
      className={`flex min-h-[52px] items-center justify-center gap-2 rounded-xl border text-sm font-semibold transition ${
        ativa
          ? 'border-marca-400 bg-marca-700/40 text-white'
          : 'border-white/10 bg-white/5 text-slate-300 active:bg-white/10'
      }`}
    >
      {children}
    </button>
  )
}

function ErroCampo({ children }: { children: ReactNode }) {
  return <span className="mt-1 block text-xs text-rose-300">{children}</span>
}
