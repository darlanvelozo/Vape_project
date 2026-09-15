/**
 * PDV — a tela do balcão.
 *
 * Prioridade absoluta é a velocidade: o foco nasce na busca e volta para ela
 * depois de cada item, o leitor de código de barras adiciona direto ao
 * carrinho, e F2 finaliza sem tirar a mão do teclado.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Minus, Plus, Search, ShoppingCart, Trash2, UserPlus, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Alerta, Botao, Campo, Carregando, Modal, Selo } from '../componentes/ui'
import { ErroApi, api } from '../lib/api'
import { formatarMoeda, paraCentavos } from '../lib/formato'
import type { CaixaAtual, Cliente, Venda, VariacaoResumo, FormaPagamento } from '../lib/tipos'

interface ItemCarrinho {
  variacao: VariacaoResumo
  quantidade: number
  precoCentavos: number
}

const FORMAS: { valor: FormaPagamento; rotulo: string; atalho: string }[] = [
  { valor: 'dinheiro', rotulo: 'Dinheiro', atalho: '1' },
  { valor: 'pix', rotulo: 'Pix', atalho: '2' },
  { valor: 'debito', rotulo: 'Débito', atalho: '3' },
  { valor: 'credito', rotulo: 'Crédito', atalho: '4' },
  { valor: 'fiado', rotulo: 'Fiado', atalho: '5' },
]

export function PDV() {
  const clienteQuery = useQueryClient()
  const campoBusca = useRef<HTMLInputElement>(null)

  const [termo, setTermo] = useState('')
  const [carrinho, setCarrinho] = useState<ItemCarrinho[]>([])
  const [cliente, setCliente] = useState<Cliente | null>(null)
  const [descontoTexto, setDescontoTexto] = useState('')
  const [pagamentoAberto, setPagamentoAberto] = useState(false)
  const [buscaClienteAberta, setBuscaClienteAberta] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [recibo, setRecibo] = useState<Venda | null>(null)
  const [resumoMovelAberto, setResumoMovelAberto] = useState(false)

  const { data: caixa, isLoading: carregandoCaixa } = useQuery({
    queryKey: ['caixa-atual'],
    queryFn: () => api.get<CaixaAtual>('/caixas/atual/'),
  })

  const { data: resultados = [], isFetching } = useQuery({
    queryKey: ['busca-pdv', termo],
    queryFn: () =>
      api.get<VariacaoResumo[]>(`/variacoes/busca-pdv/?q=${encodeURIComponent(termo)}`),
    enabled: Boolean(caixa?.aberto),
  })

  const descontoCentavos = paraCentavos(descontoTexto)
  const subtotal = carrinho.reduce((soma, item) => soma + item.precoCentavos * item.quantidade, 0)
  const total = Math.max(subtotal - descontoCentavos, 0)

  const adicionar = useCallback((variacao: VariacaoResumo) => {
    setErro(null)
    setCarrinho((atual) => {
      const existente = atual.find((item) => item.variacao.id === variacao.id)
      if (existente) {
        return atual.map((item) =>
          item.variacao.id === variacao.id
            ? { ...item, quantidade: item.quantidade + 1 }
            : item,
        )
      }
      return [
        ...atual,
        { variacao, quantidade: 1, precoCentavos: variacao.preco_venda_centavos },
      ]
    })
    setTermo('')
    campoBusca.current?.focus()
  }, [])

  function alterarQuantidade(id: number, delta: number) {
    setCarrinho((atual) =>
      atual
        .map((item) =>
          item.variacao.id === id
            ? { ...item, quantidade: Math.max(item.quantidade + delta, 0) }
            : item,
        )
        .filter((item) => item.quantidade > 0),
    )
  }

  function alterarPreco(id: number, texto: string) {
    const centavos = paraCentavos(texto)
    setCarrinho((atual) =>
      atual.map((item) =>
        item.variacao.id === id ? { ...item, precoCentavos: centavos } : item,
      ),
    )
  }

  function limpar() {
    setCarrinho([])
    setCliente(null)
    setDescontoTexto('')
    setErro(null)
    campoBusca.current?.focus()
  }

  const finalizar = useMutation({
    mutationFn: (pagamentos: { forma: FormaPagamento; valor_centavos: number }[]) =>
      api.post<Venda>('/vendas/rapida/', {
        cliente: cliente?.id ?? null,
        desconto_centavos: descontoCentavos,
        itens: carrinho.map((item) => ({
          variacao: item.variacao.id,
          quantidade: item.quantidade,
          preco_unitario_centavos: item.precoCentavos,
        })),
        pagamentos,
      }),
    onSuccess: (venda) => {
      setPagamentoAberto(false)
      setRecibo(venda)
      limpar()
      clienteQuery.invalidateQueries({ queryKey: ['caixa-atual'] })
      clienteQuery.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onError: (falha) => {
      setErro(falha instanceof ErroApi ? falha.message : 'Não foi possível finalizar a venda.')
    },
  })

  // F2 finaliza, Esc limpa — o vendedor não solta o teclado no balcão cheio.
  useEffect(() => {
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === 'F2' && carrinho.length > 0 && !pagamentoAberto) {
        evento.preventDefault()
        setPagamentoAberto(true)
      }
      if (evento.key === 'Escape' && !pagamentoAberto && carrinho.length > 0) {
        campoBusca.current?.focus()
      }
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [carrinho.length, pagamentoAberto])

  useEffect(() => {
    campoBusca.current?.focus()
  }, [])

  if (carregandoCaixa) return <Carregando texto="Verificando o caixa…" />

  if (!caixa?.aberto) {
    return (
      <div className="mx-auto max-w-lg py-10 text-center">
        <ShoppingCart size={40} className="mx-auto text-slate-300" />
        <h1 className="mt-3 text-xl font-bold text-slate-900">O caixa está fechado</h1>
        <p className="mt-1 text-sm text-slate-500">
          Toda venda precisa pertencer a um caixa aberto — é isso que permite
          conferir o dinheiro da gaveta no fim do dia.
        </p>
        <Link to="/caixa" className="mt-5 inline-block">
          <Botao tamanho="grande">Abrir o caixa</Botao>
        </Link>
      </div>
    )
  }

  return (
    <div className="grid gap-4 pb-24 lg:grid-cols-[1fr_400px] lg:pb-0">
      {/* ------------------------------------------------ busca e catálogo */}
      <div>
        <div className="relative mb-3">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            ref={campoBusca}
            value={termo}
            onChange={(evento) => setTermo(evento.target.value)}
            onKeyDown={(evento) => {
              // Leitor de código de barras termina com Enter: cai direto no carrinho.
              if (evento.key === 'Enter' && resultados.length > 0) {
                evento.preventDefault()
                adicionar(resultados[0])
              }
            }}
            placeholder="Buscar por nome, sabor, SKU ou código de barras…"
            className="campo py-3 pl-10 text-base"
            autoComplete="off"
          />
          {termo && (
            <button
              onClick={() => { setTermo(''); campoBusca.current?.focus() }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {isFetching && !resultados.length ? (
          <Carregando texto="Buscando…" />
        ) : resultados.length === 0 ? (
          <div className="cartao p-8 text-center text-sm text-slate-500">
            Nenhum produto encontrado
            {termo && <> para “{termo}”</>}.
          </div>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {resultados.map((variacao) => {
              const semEstoque = variacao.saldo <= 0
              return (
                <button
                  key={variacao.id}
                  onClick={() => adicionar(variacao)}
                  className="cartao flex flex-col gap-1 p-3 text-left transition hover:border-marca-400 hover:shadow-md"
                >
                  <p className="line-clamp-2 text-sm font-medium text-slate-800">
                    {variacao.descricao_completa}
                  </p>
                  <div className="mt-auto flex items-center justify-between gap-2 pt-1">
                    <span className="numerico font-bold text-marca-800">
                      {formatarMoeda(variacao.preco_venda_centavos)}
                    </span>
                    <Selo cor={semEstoque ? 'vermelho' : variacao.saldo <= variacao.estoque_minimo ? 'ambar' : 'cinza'}>
                      {semEstoque ? 'sem estoque' : `${variacao.saldo} un.`}
                    </Selo>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/*
        Carrinho: painel fixo no desktop; no celular ele some daqui e vira a
        barra inferior — no balcão o vendedor busca primeiro, e o carrinho
        acima da busca só empurraria o campo para fora da tela.
      */}
      <aside className="hidden lg:block">
        <div className="cartao sticky top-20 flex max-h-[calc(100vh-6rem)] flex-col">
          <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <h2 className="flex items-center gap-2 font-semibold text-slate-800">
              <ShoppingCart size={17} />
              Venda
              {carrinho.length > 0 && (
                <span className="rounded-full bg-marca-700 px-2 py-0.5 text-xs text-white">
                  {carrinho.reduce((soma, item) => soma + item.quantidade, 0)}
                </span>
              )}
            </h2>
            {carrinho.length > 0 && (
              <button onClick={limpar} className="text-xs text-rose-600 hover:underline">
                Limpar
              </button>
            )}
          </header>

          {/* cliente */}
          <div className="border-b border-slate-100 px-4 py-2.5">
            {cliente ? (
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-800">{cliente.nome}</p>
                  {cliente.credito_disponivel_centavos > 0 && (
                    <p className="text-xs text-slate-500">
                      Crédito: {formatarMoeda(cliente.credito_disponivel_centavos)}
                    </p>
                  )}
                </div>
                <button onClick={() => setCliente(null)} className="shrink-0 text-slate-400 hover:text-rose-600">
                  <X size={16} />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setBuscaClienteAberta(true)}
                className="flex w-full items-center gap-2 text-sm text-slate-500 transition hover:text-marca-700"
              >
                <UserPlus size={15} />
                Identificar cliente (opcional)
              </button>
            )}
          </div>

          {/* itens */}
          <div className="flex-1 overflow-y-auto">
            {carrinho.length === 0 ? (
              <p className="px-4 py-10 text-center text-sm text-slate-400">
                Busque um produto para começar a venda.
              </p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {carrinho.map((item) => (
                  <li key={item.variacao.id} className="px-4 py-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <p className="flex-1 text-sm font-medium text-slate-800">
                        {item.variacao.descricao_completa}
                      </p>
                      <button
                        onClick={() => alterarQuantidade(item.variacao.id, -item.quantidade)}
                        className="shrink-0 text-slate-300 transition hover:text-rose-600"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                    <div className="mt-1.5 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => alterarQuantidade(item.variacao.id, -1)}
                          className="rounded border border-slate-300 p-1 text-slate-600 hover:bg-slate-50"
                        >
                          <Minus size={13} />
                        </button>
                        <span className="numerico w-8 text-center text-sm font-semibold">
                          {item.quantidade}
                        </span>
                        <button
                          onClick={() => alterarQuantidade(item.variacao.id, 1)}
                          className="rounded border border-slate-300 p-1 text-slate-600 hover:bg-slate-50"
                        >
                          <Plus size={13} />
                        </button>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <input
                          value={(item.precoCentavos / 100).toFixed(2).replace('.', ',')}
                          onChange={(evento) => alterarPreco(item.variacao.id, evento.target.value)}
                          className="numerico w-20 rounded border border-slate-200 px-1.5 py-1 text-right text-xs"
                          aria-label="Preço unitário"
                        />
                        <span className="numerico w-20 text-right text-sm font-semibold text-slate-800">
                          {formatarMoeda(item.precoCentavos * item.quantidade)}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* totais */}
          <footer className="border-t border-slate-200 p-4">
            {erro && <div className="mb-3"><Alerta>{erro}</Alerta></div>}

            <div className="space-y-1.5 text-sm">
              <div className="flex justify-between text-slate-600">
                <span>Subtotal</span>
                <span className="numerico">{formatarMoeda(subtotal)}</span>
              </div>
              <div className="flex items-center justify-between gap-2 text-slate-600">
                <label htmlFor="desconto">Desconto</label>
                <input
                  id="desconto"
                  value={descontoTexto}
                  onChange={(evento) => setDescontoTexto(evento.target.value)}
                  placeholder="0,00"
                  className="numerico w-24 rounded border border-slate-300 px-2 py-1 text-right text-sm"
                />
              </div>
              <div className="flex justify-between border-t border-slate-200 pt-2 text-lg font-bold text-slate-900">
                <span>Total</span>
                <span className="numerico">{formatarMoeda(total)}</span>
              </div>
            </div>

            <Botao
              className="mt-3 w-full"
              tamanho="grande"
              variante="sucesso"
              disabled={carrinho.length === 0}
              onClick={() => setPagamentoAberto(true)}
            >
              Finalizar venda · F2
            </Botao>
          </footer>
        </div>
      </aside>

      {/* ------------------------------------------------ carrinho no celular */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white p-3 shadow-[0_-4px_12px_rgba(15,23,42,0.08)] lg:hidden">
        {carrinho.length > 0 && (
          <button
            onClick={() => setResumoMovelAberto(true)}
            className="mb-2 flex w-full items-center justify-between text-sm"
          >
            <span className="text-slate-600">
              {carrinho.reduce((soma, item) => soma + item.quantidade, 0)} item(ns) — ver detalhes
            </span>
            <span className="text-marca-700">abrir</span>
          </button>
        )}
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs text-slate-500">Total</p>
            <p className="numerico truncate text-xl font-bold text-slate-900">
              {formatarMoeda(total)}
            </p>
          </div>
          <Botao
            variante="sucesso"
            disabled={carrinho.length === 0}
            onClick={() => setPagamentoAberto(true)}
          >
            Finalizar
          </Botao>
        </div>
      </div>

      <Modal
        aberto={resumoMovelAberto}
        aoFechar={() => setResumoMovelAberto(false)}
        titulo="Itens da venda"
      >
        <ul className="divide-y divide-slate-100">
          {carrinho.map((item) => (
            <li key={item.variacao.id} className="flex items-center gap-2 py-2.5">
              <span className="min-w-0 flex-1 text-sm">{item.variacao.descricao_completa}</span>
              <div className="flex shrink-0 items-center gap-1">
                <button
                  onClick={() => alterarQuantidade(item.variacao.id, -1)}
                  className="rounded border border-slate-300 p-1"
                >
                  <Minus size={13} />
                </button>
                <span className="numerico w-7 text-center text-sm font-semibold">
                  {item.quantidade}
                </span>
                <button
                  onClick={() => alterarQuantidade(item.variacao.id, 1)}
                  className="rounded border border-slate-300 p-1"
                >
                  <Plus size={13} />
                </button>
              </div>
              <span className="numerico w-20 shrink-0 text-right text-sm font-semibold">
                {formatarMoeda(item.precoCentavos * item.quantidade)}
              </span>
            </li>
          ))}
        </ul>
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between gap-2 text-sm">
            <label htmlFor="desconto-movel" className="text-slate-600">Desconto</label>
            <input
              id="desconto-movel"
              value={descontoTexto}
              onChange={(evento) => setDescontoTexto(evento.target.value)}
              placeholder="0,00"
              inputMode="decimal"
              className="numerico w-28 rounded border border-slate-300 px-2 py-1 text-right text-sm"
            />
          </div>
          <div className="flex gap-2">
            <Botao variante="secundario" className="flex-1" onClick={() => { limpar(); setResumoMovelAberto(false) }}>
              Limpar
            </Botao>
            <Botao className="flex-1" onClick={() => setResumoMovelAberto(false)}>
              Continuar
            </Botao>
          </div>
        </div>
      </Modal>

      <ModalPagamento
        aberto={pagamentoAberto}
        aoFechar={() => setPagamentoAberto(false)}
        total={total}
        temCliente={Boolean(cliente)}
        erro={erro}
        enviando={finalizar.isPending}
        aoConfirmar={(pagamentos) => finalizar.mutate(pagamentos)}
      />

      <ModalBuscaCliente
        aberto={buscaClienteAberta}
        aoFechar={() => setBuscaClienteAberta(false)}
        aoSelecionar={(selecionado) => {
          setCliente(selecionado)
          setBuscaClienteAberta(false)
        }}
      />

      <ModalRecibo venda={recibo} aoFechar={() => setRecibo(null)} />
    </div>
  )
}

// ------------------------------------------------------------------ pagamento

function ModalPagamento({
  aberto,
  aoFechar,
  total,
  temCliente,
  erro,
  enviando,
  aoConfirmar,
}: {
  aberto: boolean
  aoFechar: () => void
  total: number
  temCliente: boolean
  erro: string | null
  enviando: boolean
  aoConfirmar: (pagamentos: { forma: FormaPagamento; valor_centavos: number }[]) => void
}) {
  const [forma, setForma] = useState<FormaPagamento>('dinheiro')
  const [recebidoTexto, setRecebidoTexto] = useState('')

  useEffect(() => {
    if (aberto) {
      setForma('dinheiro')
      setRecebidoTexto('')
    }
  }, [aberto])

  const recebido = recebidoTexto ? paraCentavos(recebidoTexto) : total
  const troco = forma === 'dinheiro' ? Math.max(recebido - total, 0) : 0
  const insuficiente = recebido < total

  return (
    <Modal aberto={aberto} aoFechar={aoFechar} titulo="Pagamento" descricao={`Total: ${formatarMoeda(total)}`}>
      <div className="space-y-4">
        <div>
          <p className="rotulo">Forma de pagamento</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {FORMAS.map((opcao) => {
              const bloqueado = opcao.valor === 'fiado' && !temCliente
              return (
                <button
                  key={opcao.valor}
                  onClick={() => setForma(opcao.valor)}
                  disabled={bloqueado}
                  title={bloqueado ? 'Venda fiada exige cliente identificado.' : undefined}
                  className={`rounded-lg border px-3 py-2.5 text-sm font-medium transition ${
                    forma === opcao.valor
                      ? 'border-marca-600 bg-marca-50 text-marca-800'
                      : 'border-slate-300 text-slate-600 hover:bg-slate-50'
                  } ${bloqueado ? 'cursor-not-allowed opacity-40' : ''}`}
                >
                  {opcao.rotulo}
                </button>
              )
            })}
          </div>
        </div>

        {forma === 'dinheiro' && (
          <Campo
            rotulo="Valor recebido"
            value={recebidoTexto}
            onChange={(evento) => setRecebidoTexto(evento.target.value)}
            placeholder={formatarMoeda(total).replace('R$', '').trim()}
            inputMode="decimal"
            dica="Deixe em branco se o cliente pagou o valor exato."
          />
        )}

        {troco > 0 && (
          <div className="rounded-lg bg-emerald-50 px-3 py-2.5 text-sm">
            <span className="text-emerald-700">Troco: </span>
            <span className="numerico text-lg font-bold text-emerald-800">{formatarMoeda(troco)}</span>
          </div>
        )}

        {insuficiente && recebidoTexto && (
          <Alerta tipo="aviso">
            Valor recebido menor que o total da venda. Faltam {formatarMoeda(total - recebido)}.
          </Alerta>
        )}

        {erro && <Alerta>{erro}</Alerta>}

        <div className="flex gap-2">
          <Botao variante="secundario" onClick={aoFechar} className="flex-1">
            Voltar
          </Botao>
          <Botao
            variante="sucesso"
            className="flex-[2]"
            carregando={enviando}
            disabled={insuficiente && Boolean(recebidoTexto)}
            onClick={() =>
              aoConfirmar([
                { forma, valor_centavos: forma === 'dinheiro' ? Math.max(recebido, total) : total },
              ])
            }
          >
            Confirmar {formatarMoeda(total)}
          </Botao>
        </div>
      </div>
    </Modal>
  )
}

// ------------------------------------------------------------------ cliente

function ModalBuscaCliente({
  aberto,
  aoFechar,
  aoSelecionar,
}: {
  aberto: boolean
  aoFechar: () => void
  aoSelecionar: (cliente: Cliente) => void
}) {
  const [termo, setTermo] = useState('')
  const { data: clientes = [] } = useQuery({
    queryKey: ['busca-cliente', termo],
    queryFn: () => api.get<Cliente[]>(`/clientes/busca/?q=${encodeURIComponent(termo)}`),
    enabled: aberto,
  })

  return (
    <Modal aberto={aberto} aoFechar={aoFechar} titulo="Identificar cliente">
      <Campo
        placeholder="Nome, telefone ou CPF…"
        value={termo}
        onChange={(evento) => setTermo(evento.target.value)}
        autoFocus
      />
      <ul className="mt-3 max-h-72 divide-y divide-slate-100 overflow-y-auto">
        {clientes.length === 0 && (
          <li className="py-6 text-center text-sm text-slate-400">Nenhum cliente encontrado.</li>
        )}
        {clientes.map((cliente) => (
          <li key={cliente.id}>
            <button
              onClick={() => aoSelecionar(cliente)}
              className="flex w-full items-center justify-between gap-3 px-1 py-2.5 text-left transition hover:bg-slate-50"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-800">{cliente.nome}</p>
                <p className="text-xs text-slate-500">{cliente.telefone || 'sem telefone'}</p>
              </div>
              {cliente.credito_disponivel_centavos > 0 && (
                <Selo cor="azul">{formatarMoeda(cliente.credito_disponivel_centavos)}</Selo>
              )}
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-slate-500">
        Cliente novo? Cadastre em <Link to="/clientes" className="text-marca-700 hover:underline">Clientes</Link>.
      </p>
    </Modal>
  )
}

// ------------------------------------------------------------------ recibo

function ModalRecibo({ venda, aoFechar }: { venda: Venda | null; aoFechar: () => void }) {
  if (!venda) return null
  const troco = venda.pagamentos.reduce((soma, pagamento) => soma + pagamento.troco_centavos, 0)

  return (
    <Modal
      aberto={Boolean(venda)}
      aoFechar={aoFechar}
      titulo={`Venda #${venda.numero} concluída`}
      descricao="Documento sem valor fiscal."
    >
      <div className="space-y-3">
        <div className="rounded-lg bg-emerald-50 p-4 text-center">
          <p className="text-sm text-emerald-700">Total da venda</p>
          <p className="numerico text-3xl font-bold text-emerald-800">
            {formatarMoeda(venda.total_centavos)}
          </p>
          {troco > 0 && (
            <p className="mt-1 text-sm font-medium text-emerald-700">
              Troco: {formatarMoeda(troco)}
            </p>
          )}
        </div>

        <ul className="divide-y divide-slate-100 text-sm">
          {venda.itens.map((item) => (
            <li key={item.id} className="flex justify-between gap-3 py-1.5">
              <span className="text-slate-600">
                {item.quantidade}× {item.descricao}
              </span>
              <span className="numerico shrink-0 font-medium">
                {formatarMoeda(item.total_centavos)}
              </span>
            </li>
          ))}
        </ul>

        <div className="flex gap-2">
          <Botao variante="secundario" className="flex-1" onClick={() => window.print()}>
            Imprimir
          </Botao>
          <Botao className="flex-1" onClick={aoFechar}>
            Nova venda
          </Botao>
        </div>
      </div>
    </Modal>
  )
}
