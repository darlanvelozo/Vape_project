/** Componentes básicos de interface, compartilhados por todas as telas. */

import * as Dialog from '@radix-ui/react-dialog'
import clsx from 'clsx'
import { AlertCircle, Loader2, X } from 'lucide-react'
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'

// ------------------------------------------------------------------ Botão

type VarianteBotao = 'primario' | 'secundario' | 'perigo' | 'fantasma' | 'sucesso'

interface BotaoProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: VarianteBotao
  carregando?: boolean
  tamanho?: 'pequeno' | 'medio' | 'grande'
  icone?: ReactNode
}

const ESTILOS_BOTAO: Record<VarianteBotao, string> = {
  primario: 'bg-marca-700 text-white hover:bg-marca-800 focus-visible:ring-marca-500',
  secundario:
    'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 focus-visible:ring-slate-400',
  perigo: 'bg-rose-600 text-white hover:bg-rose-700 focus-visible:ring-rose-500',
  sucesso: 'bg-emerald-600 text-white hover:bg-emerald-700 focus-visible:ring-emerald-500',
  fantasma: 'bg-transparent text-slate-600 hover:bg-slate-100 focus-visible:ring-slate-400',
}

// As alturas mínimas valem no celular (ver a regra `pointer: coarse` em
// index.css); no desktop o padding define o tamanho.
const TAMANHOS_BOTAO = {
  pequeno: 'px-3 py-1.5 text-xs gap-1.5',
  medio: 'px-3.5 py-2.5 text-sm gap-2',
  grande: 'px-5 py-3 text-base gap-2',
}

export function Botao({
  variante = 'primario',
  tamanho = 'medio',
  carregando = false,
  icone,
  children,
  className,
  disabled,
  ...resto
}: BotaoProps) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center rounded-lg font-medium shadow-sm transition',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1',
        'disabled:cursor-not-allowed disabled:opacity-60',
        ESTILOS_BOTAO[variante],
        TAMANHOS_BOTAO[tamanho],
        className,
      )}
      disabled={disabled || carregando}
      {...resto}
    >
      {carregando ? <Loader2 size={16} className="animate-spin" /> : icone}
      {children}
    </button>
  )
}

// ------------------------------------------------------------------ Campos

interface CampoProps extends InputHTMLAttributes<HTMLInputElement> {
  rotulo?: string
  erro?: string
  dica?: string
}

export function Campo({ rotulo, erro, dica, className, id, ...resto }: CampoProps) {
  const identificador = id ?? resto.name
  return (
    <div className={className}>
      {rotulo && (
        <label className="rotulo" htmlFor={identificador}>
          {rotulo}
        </label>
      )}
      <input
        id={identificador}
        className={clsx(
          'campo',
          erro && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/30',
        )}
        aria-invalid={Boolean(erro)}
        {...resto}
      />
      {erro && <p className="mt-1 text-xs text-rose-600">{erro}</p>}
      {!erro && dica && <p className="mt-1 text-xs text-slate-500">{dica}</p>}
    </div>
  )
}

interface SelecaoProps extends SelectHTMLAttributes<HTMLSelectElement> {
  rotulo?: string
  erro?: string
}

export function Selecao({ rotulo, erro, className, children, id, ...resto }: SelecaoProps) {
  const identificador = id ?? resto.name
  return (
    <div className={className}>
      {rotulo && (
        <label className="rotulo" htmlFor={identificador}>
          {rotulo}
        </label>
      )}
      <select id={identificador} className={clsx('campo', erro && 'border-rose-400')} {...resto}>
        {children}
      </select>
      {erro && <p className="mt-1 text-xs text-rose-600">{erro}</p>}
    </div>
  )
}

export function AreaTexto({
  rotulo,
  className,
  ...resto
}: { rotulo?: string } & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <div className={className}>
      {rotulo && <label className="rotulo">{rotulo}</label>}
      <textarea className="campo min-h-[80px] resize-y" {...resto} />
    </div>
  )
}

// ------------------------------------------------------------------ Feedback

export function Alerta({
  tipo = 'erro',
  children,
}: {
  tipo?: 'erro' | 'aviso' | 'sucesso' | 'informacao'
  children: ReactNode
}) {
  const estilos = {
    erro: 'bg-rose-50 text-rose-800 border-rose-200',
    aviso: 'bg-amber-50 text-amber-800 border-amber-200',
    sucesso: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    informacao: 'bg-sky-50 text-sky-800 border-sky-200',
  }
  return (
    <div
      role={tipo === 'erro' ? 'alert' : 'status'}
      className={clsx('flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm', estilos[tipo])}
    >
      <AlertCircle size={16} className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}

export function Selo({
  cor = 'cinza',
  children,
}: {
  cor?: 'cinza' | 'verde' | 'vermelho' | 'ambar' | 'azul' | 'roxo'
  children: ReactNode
}) {
  const cores = {
    cinza: 'bg-slate-100 text-slate-700 ring-slate-200',
    verde: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    vermelho: 'bg-rose-50 text-rose-700 ring-rose-200',
    ambar: 'bg-amber-50 text-amber-800 ring-amber-200',
    azul: 'bg-sky-50 text-sky-700 ring-sky-200',
    roxo: 'bg-marca-50 text-marca-700 ring-marca-200',
  }
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        cores[cor],
      )}
    >
      {children}
    </span>
  )
}

export function Carregando({ texto = 'Carregando…' }: { texto?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <Loader2 size={18} className="animate-spin" />
      {texto}
    </div>
  )
}

export function Vazio({
  titulo,
  descricao,
  acao,
}: {
  titulo: string
  descricao?: string
  acao?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-4 py-14 text-center">
      <p className="font-medium text-slate-700">{titulo}</p>
      {descricao && <p className="max-w-md text-sm text-slate-500">{descricao}</p>}
      {acao && <div className="mt-3">{acao}</div>}
    </div>
  )
}

// ------------------------------------------------------------------ Modal

export function Modal({
  aberto,
  aoFechar,
  titulo,
  descricao,
  children,
  largura = 'max-w-lg',
}: {
  aberto: boolean
  aoFechar: () => void
  titulo: string
  descricao?: string
  children: ReactNode
  largura?: string
}) {
  return (
    <Dialog.Root open={aberto} onOpenChange={(estado) => !estado && aoFechar()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm" />
        <Dialog.Content
          className={clsx(
            'fixed left-1/2 top-1/2 z-50 max-h-[92vh] w-[calc(100vw-2rem)] -translate-x-1/2',
            '-translate-y-1/2 overflow-y-auto rounded-xl bg-white p-5 shadow-xl',
            largura,
          )}
        >
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-lg font-semibold text-slate-900">{titulo}</Dialog.Title>
              {descricao && (
                <Dialog.Description className="mt-0.5 text-sm text-slate-500">
                  {descricao}
                </Dialog.Description>
              )}
            </div>
            <Dialog.Close className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600">
              <X size={18} />
              <span className="sr-only">Fechar</span>
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

// ------------------------------------------------------------------ Estrutura

export function Cartao({
  titulo,
  acao,
  children,
  className,
  semCorpo = false,
}: {
  titulo?: string
  acao?: ReactNode
  children: ReactNode
  className?: string
  semCorpo?: boolean
}) {
  return (
    <section className={clsx('cartao', className)}>
      {(titulo || acao) && (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
          {titulo && <h2 className="text-sm font-semibold text-slate-700">{titulo}</h2>}
          {acao}
        </header>
      )}
      <div className={semCorpo ? '' : 'p-4'}>{children}</div>
    </section>
  )
}

export function CabecalhoPagina({
  titulo,
  descricao,
  acoes,
}: {
  titulo: string
  descricao?: string
  acoes?: ReactNode
}) {
  return (
    <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-bold text-slate-900 sm:text-2xl">{titulo}</h1>
        {descricao && <p className="mt-0.5 text-sm text-slate-500">{descricao}</p>}
      </div>
      {acoes && <div className="flex flex-wrap gap-2">{acoes}</div>}
    </header>
  )
}

/**
 * Botão só de ícone, das colunas de ação.
 *
 * Existe para padronizar a área de toque: solto, o ícone de 15px deixava um
 * alvo de ~27px, abaixo do mínimo confortável no celular.
 */
export function BotaoIcone({
  titulo,
  aoClicar,
  children,
  perigo = false,
}: {
  titulo: string
  aoClicar: () => void
  children: ReactNode
  perigo?: boolean
}) {
  return (
    <button
      type="button"
      onClick={aoClicar}
      title={titulo}
      aria-label={titulo}
      className={clsx(
        'acao-icone inline-flex items-center justify-center rounded-lg p-2 text-slate-400 transition',
        perigo ? 'hover:bg-rose-50 hover:text-rose-600' : 'hover:bg-slate-100 hover:text-marca-700',
      )}
    >
      {children}
    </button>
  )
}

export function TabelaEnvolvida({ children }: { children: ReactNode }) {
  /* Tabela larga rola sozinha; a página nunca rola na horizontal. */
  return <div className="overflow-x-auto">{children}</div>
}

/**
 * Navegação de páginas das listagens.
 *
 * A API pagina de 50 em 50; sem este controle, tudo além da primeira página
 * ficaria inacessível na tela.
 */
export function Paginacao({
  pagina,
  total,
  porPagina = 50,
  aoMudar,
}: {
  pagina: number
  total: number
  porPagina?: number
  aoMudar: (pagina: number) => void
}) {
  const ultimaPagina = Math.max(Math.ceil(total / porPagina), 1)
  if (total === 0) return null

  const primeiro = (pagina - 1) * porPagina + 1
  const ultimo = Math.min(pagina * porPagina, total)

  return (
    <nav className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3">
      <p className="text-xs text-slate-500">
        Mostrando <strong className="numerico">{primeiro}</strong>–
        <strong className="numerico">{ultimo}</strong> de{' '}
        <strong className="numerico">{total}</strong>
      </p>
      {ultimaPagina > 1 && (
        <div className="flex items-center gap-1">
          <Botao
            tamanho="pequeno"
            variante="secundario"
            disabled={pagina <= 1}
            onClick={() => aoMudar(pagina - 1)}
          >
            Anterior
          </Botao>
          <span className="numerico px-2 text-xs text-slate-500">
            {pagina} / {ultimaPagina}
          </span>
          <Botao
            tamanho="pequeno"
            variante="secundario"
            disabled={pagina >= ultimaPagina}
            onClick={() => aoMudar(pagina + 1)}
          >
            Próxima
          </Botao>
        </div>
      )}
    </nav>
  )
}
