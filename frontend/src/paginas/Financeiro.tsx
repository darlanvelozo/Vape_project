/** Contas a pagar e a receber, com fluxo de caixa realizado. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Check, Plus, RotateCcw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import {
  Alerta, AreaTexto, Botao, BotaoIcone, CabecalhoPagina, Campo, Carregando, Cartao,
  Modal, Paginacao, Selecao, Selo, TabelaEnvolvida, Vazio,
} from '../componentes/ui'
import { ErroApi, api, querystring } from '../lib/api'
import {
  dataISO, diasAtras, formatarData, formatarMoeda, formatarPercentual, paraCentavos,
} from '../lib/formato'
import type { CategoriaFinanceira, Lancamento, Pagina } from '../lib/tipos'

interface Resultado {
  inicio: string
  fim: string
  resultado: {
    faturamento_centavos: number
    descontos_centavos: number
    vendas: number
    custo_mercadoria_centavos: number
    lucro_bruto_centavos: number
    margem_bruta: number
    despesas_operacionais_centavos: number
    resultado_centavos: number
    ticket_medio_centavos: number
  }
  caixa: {
    entradas_centavos: number
    saidas_centavos: number
    compras_centavos: number
    saldo_centavos: number
  }
  a_receber: { total_centavos: number; atrasado_centavos: number; quantidade: number }
  a_pagar: { total_centavos: number; atrasado_centavos: number; quantidade: number }
  estoque: {
    unidades: number
    custo_centavos: number
    venda_centavos: number
    lucro_previsto_centavos: number
  }
}

interface ResumoFinanceiro {
  a_receber_centavos: number
  a_pagar_centavos: number
  a_receber_atrasado_centavos: number
  a_pagar_atrasado_centavos: number
  recebido_no_mes_centavos: number
  pago_no_mes_centavos: number
  quantidade_atrasados: number
}

interface FluxoCaixa {
  dias: { data: string; entradas_centavos: number; saidas_centavos: number; saldo_centavos: number }[]
  total_entradas_centavos: number
  total_saidas_centavos: number
  saldo_centavos: number
}

export function Financeiro() {
  const clienteQuery = useQueryClient()
  const [parametros] = useSearchParams()
  const [tipo, setTipo] = useState('')
  const [status, setStatus] = useState(parametros.get('filtro') === 'atrasados' ? 'pendente' : '')
  const [atrasados, setAtrasados] = useState(parametros.get('filtro') === 'atrasados')
  const [modal, setModal] = useState<Lancamento | 'novo' | null>(null)
  const [pagina, setPagina] = useState(1)
  const [aba, setAba] = useState<'visao' | 'lancamentos'>('visao')
  const [inicio, setInicio] = useState(diasAtras(30))
  const [fim, setFim] = useState('')

  const { data: resumo } = useQuery({
    queryKey: ['financeiro-resumo'],
    queryFn: () => api.get<ResumoFinanceiro>('/financeiro/lancamentos/resumo/'),
  })

  const { data: gestao } = useQuery({
    queryKey: ['resultado', inicio, fim],
    queryFn: () => api.get<Resultado>(`/relatorios/resultado/${querystring({ inicio, fim })}`),
  })

  const { data: fluxo } = useQuery({
    queryKey: ['fluxo-caixa', inicio, fim],
    queryFn: () =>
      api.get<FluxoCaixa>(`/financeiro/lancamentos/fluxo-de-caixa/${querystring({ inicio, fim })}`),
  })

  const { data: lancamentos, isLoading } = useQuery({
    queryKey: ['lancamentos', tipo, status, atrasados, pagina],
    queryFn: () =>
      api.get<Pagina<Lancamento>>(
        `/financeiro/lancamentos/${querystring({
          tipo,
          status,
          atrasados: atrasados ? 'true' : undefined,
          ordering: '-vencimento',
          page: pagina,
        })}`,
      ),
  })

  const { data: categorias } = useQuery({
    queryKey: ['categorias-financeiras'],
    queryFn: () => api.get<Pagina<CategoriaFinanceira>>('/financeiro/categorias/'),
  })

  function invalidar() {
    clienteQuery.invalidateQueries({ queryKey: ['lancamentos'] })
    clienteQuery.invalidateQueries({ queryKey: ['financeiro-resumo'] })
    clienteQuery.invalidateQueries({ queryKey: ['fluxo-caixa'] })
    clienteQuery.invalidateQueries({ queryKey: ['resultado'] })
    clienteQuery.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const baixar = useMutation({
    mutationFn: (id: number) => api.post(`/financeiro/lancamentos/${id}/baixar/`, {}),
    onSuccess: invalidar,
  })

  const estornar = useMutation({
    mutationFn: (id: number) => api.post(`/financeiro/lancamentos/${id}/estornar/`, {}),
    onSuccess: invalidar,
  })

  const excluir = useMutation({
    mutationFn: (id: number) => api.delete(`/financeiro/lancamentos/${id}/`),
    onSuccess: invalidar,
  })

  return (
    <>
      <CabecalhoPagina
        titulo="Financeiro"
        descricao="Quanto a loja ganhou, quanto entrou no caixa e o que ainda falta receber."
        acoes={
          <Botao icone={<Plus size={16} />} onClick={() => setModal('novo')}>
            Novo lançamento
          </Botao>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="flex gap-1 rounded-lg bg-slate-200/60 p-1">
          {([['visao', 'Visão de gestão'], ['lancamentos', 'Lançamentos']] as const).map(
            ([valor, rotulo]) => (
              <button
                key={valor}
                onClick={() => setAba(valor)}
                className={`min-h-[40px] rounded-md px-3 text-sm font-medium transition ${
                  aba === valor ? 'bg-white text-marca-800 shadow-sm' : 'text-slate-600'
                }`}
              >
                {rotulo}
              </button>
            ),
          )}
        </div>
        <div className="flex flex-1 flex-wrap gap-2 sm:justify-end">
          <Campo
            type="date"
            value={inicio}
            onChange={(evento) => setInicio(evento.target.value)}
            className="min-w-[150px] flex-1 sm:max-w-[170px]"
          />
          <Campo
            type="date"
            value={fim}
            onChange={(evento) => setFim(evento.target.value)}
            className="min-w-[150px] flex-1 sm:max-w-[170px]"
          />
        </div>
      </div>

      {aba === 'visao' && gestao && (
        <VisaoDeGestao dados={gestao} fluxo={fluxo} />
      )}

      {aba === 'lancamentos' && (
        <>
      <div className="mb-3 grid gap-2 sm:grid-cols-3">
        <Selecao value={tipo} onChange={(evento) => { setTipo(evento.target.value); setPagina(1) }}>
          <option value="">Receitas e despesas</option>
          <option value="receita">Só receitas</option>
          <option value="despesa">Só despesas</option>
        </Selecao>
        <Selecao value={status} onChange={(evento) => { setStatus(evento.target.value); setPagina(1) }}>
          <option value="">Todos os status</option>
          <option value="pendente">Pendentes</option>
          <option value="pago">Baixados</option>
          <option value="cancelado">Cancelados</option>
        </Selecao>
        <label className="flex min-h-[44px] cursor-pointer items-center gap-2 rounded-lg px-2
                          text-sm text-slate-700 transition active:bg-slate-100">
          <input
            type="checkbox"
            checked={atrasados}
            onChange={(evento) => { setAtrasados(evento.target.checked); setPagina(1) }}
            className="h-5 w-5 rounded border-slate-300"
          />
          Só em atraso
          {(resumo?.quantidade_atrasados ?? 0) > 0 && (
            <Selo cor="vermelho">{resumo!.quantidade_atrasados}</Selo>
          )}
        </label>
      </div>

      <Cartao semCorpo>
        {isLoading ? (
          <Carregando />
        ) : !lancamentos?.results.length ? (
          <Vazio titulo="Nenhum lançamento encontrado" />
        ) : (
          <TabelaEnvolvida>
            <table className="tabela">
              <thead>
                <tr>
                  <th>Descrição</th>
                  <th>Categoria</th>
                  <th>Vencimento</th>
                  <th className="text-right">Valor</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {lancamentos.results.map((lancamento) => (
                  <tr key={lancamento.id}>
                    <td>
                      <p className="text-sm font-medium text-slate-800">{lancamento.descricao}</p>
                      <p className="text-xs text-slate-400">
                        {lancamento.cliente_nome || lancamento.fornecedor_nome || lancamento.tipo_display}
                      </p>
                    </td>
                    <td className="text-sm text-slate-600">{lancamento.categoria_nome || '—'}</td>
                    <td className="text-sm">
                      {formatarData(lancamento.vencimento)}
                      {lancamento.atrasado && (
                        <p className="text-xs text-rose-600">
                          {lancamento.dias_de_atraso} dia(s) em atraso
                        </p>
                      )}
                    </td>
                    <td
                      className={`numerico text-right font-semibold ${
                        lancamento.tipo === 'receita' ? 'text-emerald-700' : 'text-rose-700'
                      }`}
                    >
                      {lancamento.tipo === 'receita' ? '+' : '−'}{' '}
                      {formatarMoeda(lancamento.valor_centavos)}
                    </td>
                    <td>
                      <Selo
                        cor={
                          lancamento.status === 'pago'
                            ? 'verde'
                            : lancamento.status === 'cancelado'
                              ? 'cinza'
                              : lancamento.atrasado
                                ? 'vermelho'
                                : 'ambar'
                        }
                      >
                        {lancamento.status_display}
                      </Selo>
                    </td>
                    <td className="text-right">
                      <div className="flex justify-end gap-1">
                        {lancamento.status === 'pendente' && (
                          <BotaoIcone titulo="Dar baixa" aoClicar={() => baixar.mutate(lancamento.id)}>
                            <Check size={16} />
                          </BotaoIcone>
                        )}
                        {lancamento.status === 'pago' && (
                          <BotaoIcone titulo="Estornar baixa" aoClicar={() => estornar.mutate(lancamento.id)}>
                            <RotateCcw size={16} />
                          </BotaoIcone>
                        )}
                        {!lancamento.venda && !lancamento.compra && (
                          <BotaoIcone
                            titulo="Excluir lançamento"
                            perigo
                            aoClicar={() => {
                              if (confirm('Excluir este lançamento?')) excluir.mutate(lancamento.id)
                            }}
                          >
                            <Trash2 size={16} />
                          </BotaoIcone>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TabelaEnvolvida>
        )}
        <Paginacao pagina={pagina} total={lancamentos?.count ?? 0} aoMudar={setPagina} />
      </Cartao>
        </>
      )}

      {modal && (
        <ModalLancamento
          lancamento={modal === 'novo' ? null : modal}
          categorias={categorias?.results ?? []}
          aoFechar={() => setModal(null)}
        />
      )}
    </>
  )
}

function ModalLancamento({
  lancamento, categorias, aoFechar,
}: {
  lancamento: Lancamento | null
  categorias: CategoriaFinanceira[]
  aoFechar: () => void
}) {
  const clienteQuery = useQueryClient()
  const [erro, setErro] = useState<ErroApi | null>(null)
  const [novaCategoria, setNovaCategoria] = useState('')
  const [dados, setDados] = useState({
    tipo: lancamento?.tipo ?? 'despesa',
    categoria: lancamento?.categoria?.toString() ?? '',
    descricao: lancamento?.descricao ?? '',
    valor: lancamento ? (lancamento.valor_centavos / 100).toFixed(2).replace('.', ',') : '',
    vencimento: lancamento?.vencimento ?? dataISO(new Date()),
    observacoes: lancamento?.observacoes ?? '',
  })

  const criarCategoria = useMutation({
    mutationFn: (nome: string) =>
      api.post<CategoriaFinanceira>('/financeiro/categorias/', { nome, tipo: dados.tipo }),
    onSuccess: (categoria) => {
      clienteQuery.invalidateQueries({ queryKey: ['categorias-financeiras'] })
      setDados((atual) => ({ ...atual, categoria: String(categoria.id) }))
      setNovaCategoria('')
    },
  })

  const salvar = useMutation({
    mutationFn: () => {
      const corpo = {
        tipo: dados.tipo,
        categoria: dados.categoria ? Number(dados.categoria) : null,
        descricao: dados.descricao,
        valor_centavos: paraCentavos(dados.valor),
        vencimento: dados.vencimento,
        observacoes: dados.observacoes,
      }
      return lancamento
        ? api.patch(`/financeiro/lancamentos/${lancamento.id}/`, corpo)
        : api.post('/financeiro/lancamentos/', corpo)
    },
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['lancamentos'] })
      clienteQuery.invalidateQueries({ queryKey: ['financeiro-resumo'] })
      aoFechar()
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha : null),
  })

  const categoriasDoTipo = categorias.filter((categoria) => categoria.tipo === dados.tipo)

  return (
    <Modal
      aberto
      aoFechar={aoFechar}
      titulo={lancamento ? 'Editar lançamento' : 'Novo lançamento'}
      largura="max-w-xl"
    >
      <form className="space-y-3" onSubmit={(evento) => { evento.preventDefault(); salvar.mutate() }}>
        <div className="grid grid-cols-2 gap-2">
          {(['despesa', 'receita'] as const).map((valor) => (
            <button
              key={valor}
              type="button"
              onClick={() => setDados({ ...dados, tipo: valor, categoria: '' })}
              className={`rounded-lg border px-3 py-2.5 text-sm font-medium capitalize transition ${
                dados.tipo === valor
                  ? valor === 'receita'
                    ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                    : 'border-rose-500 bg-rose-50 text-rose-700'
                  : 'border-slate-300 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {valor === 'receita' ? 'Receita (a receber)' : 'Despesa (a pagar)'}
            </button>
          ))}
        </div>

        <Campo
          rotulo="Descrição"
          value={dados.descricao}
          onChange={(evento) => setDados({ ...dados, descricao: evento.target.value })}
          placeholder="Ex.: aluguel de setembro"
          required
          autoFocus
          erro={erro?.doCampo('descricao')}
        />

        <div className="grid gap-3 sm:grid-cols-2">
          <Campo
            rotulo="Valor"
            value={dados.valor}
            onChange={(evento) => setDados({ ...dados, valor: evento.target.value })}
            placeholder="0,00"
            inputMode="decimal"
            required
            erro={erro?.doCampo('valor_centavos')}
          />
          <Campo
            rotulo="Vencimento"
            type="date"
            value={dados.vencimento}
            onChange={(evento) => setDados({ ...dados, vencimento: evento.target.value })}
            required
          />
        </div>

        <div>
          <Selecao
            rotulo="Categoria"
            value={dados.categoria}
            onChange={(evento) => setDados({ ...dados, categoria: evento.target.value })}
            erro={erro?.doCampo('categoria')}
          >
            <option value="">Sem categoria</option>
            {categoriasDoTipo.map((categoria) => (
              <option key={categoria.id} value={categoria.id}>{categoria.nome}</option>
            ))}
          </Selecao>
          <div className="mt-2 flex gap-2">
            <input
              className="campo flex-1 text-xs"
              placeholder="Criar nova categoria…"
              value={novaCategoria}
              onChange={(evento) => setNovaCategoria(evento.target.value)}
            />
            <Botao
              type="button"
              tamanho="pequeno"
              variante="secundario"
              disabled={!novaCategoria.trim()}
              carregando={criarCategoria.isPending}
              onClick={() => criarCategoria.mutate(novaCategoria.trim())}
            >
              Criar
            </Botao>
          </div>
        </div>

        <AreaTexto
          rotulo="Observações"
          value={dados.observacoes}
          onChange={(evento) => setDados({ ...dados, observacoes: evento.target.value })}
        />

        {erro && <Alerta>{erro.message}</Alerta>}

        <div className="flex gap-2 pt-1">
          <Botao type="button" variante="secundario" className="flex-1" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" className="flex-1" carregando={salvar.isPending}>
            Salvar
          </Botao>
        </div>
      </form>
    </Modal>
  )
}


/**
 * Visão de gestão.
 *
 * Separa de propósito duas contas que o lojista costuma misturar: o
 * **resultado** (o que a loja ganhou) e o **caixa** (o dinheiro que entrou e
 * saiu). Comprar estoque derruba o caixa sem ser prejuízo — o dinheiro virou
 * mercadoria —, e essa diferença aparece explicada no rodapé.
 */
function VisaoDeGestao({ dados, fluxo }: { dados: Resultado; fluxo?: FluxoCaixa }) {
  const { resultado, caixa, a_receber, a_pagar, estoque } = dados
  const positivo = resultado.resultado_centavos >= 0

  const grafico = (fluxo?.dias ?? []).map((dia) => ({
    data: formatarData(dia.data).slice(0, 5),
    entradas: dia.entradas_centavos / 100,
    saidas: dia.saidas_centavos / 100,
  }))

  return (
    <div className="space-y-4">
      {/* ---------------- O que a loja ganhou ---------------- */}
      <Cartao titulo="Resultado do período">
        <dl className="space-y-2.5 text-sm">
          <Linha rotulo="Faturamento" valor={resultado.faturamento_centavos}
                 detalhe={`${resultado.vendas} venda(s) · ticket ${formatarMoeda(resultado.ticket_medio_centavos)}`} />
          <Linha rotulo="Custo da mercadoria vendida" valor={-resultado.custo_mercadoria_centavos}
                 detalhe="o que as peças vendidas custaram para a loja" />
          <Linha
            rotulo="Lucro bruto"
            valor={resultado.lucro_bruto_centavos}
            detalhe={`margem de ${formatarPercentual(resultado.margem_bruta)}`}
            destaque
          />
          <Linha rotulo="Despesas da loja" valor={-resultado.despesas_operacionais_centavos}
                 detalhe="aluguel, energia, salários — sem contar compra de mercadoria" />

          <div className={`flex items-baseline justify-between gap-3 rounded-lg px-3 py-3 ${
            positivo ? 'bg-emerald-50' : 'bg-rose-50'
          }`}>
            <div>
              <dt className={`font-semibold ${positivo ? 'text-emerald-800' : 'text-rose-800'}`}>
                {positivo ? 'Lucro do período' : 'Prejuízo do período'}
              </dt>
              <dd className="mt-0.5 text-xs text-slate-500">
                é isto que a loja ganhou de verdade
              </dd>
            </div>
            <span className={`numerico shrink-0 text-2xl font-bold ${
              positivo ? 'text-emerald-700' : 'text-rose-700'
            }`}>
              {formatarMoeda(resultado.resultado_centavos)}
            </span>
          </div>
        </dl>
      </Cartao>

      {/* ---------------- A receber e a pagar ---------------- */}
      <div className="grid gap-3 sm:grid-cols-2">
        <Cartao titulo="A receber">
          <p className="numerico text-3xl font-bold text-emerald-700">
            {formatarMoeda(a_receber.total_centavos)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {a_receber.quantidade === 0
              ? 'Nada em aberto — todas as vendas foram recebidas.'
              : `${a_receber.quantidade} lançamento(s) em aberto, de vendas fiadas.`}
          </p>
          {a_receber.atrasado_centavos > 0 && (
            <p className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-rose-50 px-2.5 py-1.5 text-xs font-medium text-rose-700">
              <AlertTriangle size={13} />
              {formatarMoeda(a_receber.atrasado_centavos)} vencido
            </p>
          )}
        </Cartao>

        <Cartao titulo="A pagar">
          <p className="numerico text-3xl font-bold text-rose-700">
            {formatarMoeda(a_pagar.total_centavos)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {a_pagar.quantidade === 0
              ? 'Nenhuma conta em aberto.'
              : `${a_pagar.quantidade} conta(s) a vencer.`}
          </p>
          {a_pagar.atrasado_centavos > 0 && (
            <p className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-rose-50 px-2.5 py-1.5 text-xs font-medium text-rose-700">
              <AlertTriangle size={13} />
              {formatarMoeda(a_pagar.atrasado_centavos)} vencido
            </p>
          )}
        </Cartao>
      </div>

      {/* ---------------- Caixa ---------------- */}
      <Cartao titulo="Dinheiro no período">
        <dl className="space-y-2.5 text-sm">
          <Linha rotulo="Entrou" valor={caixa.entradas_centavos} detalhe="recebimentos de vendas" />
          <Linha rotulo="Saiu" valor={-caixa.saidas_centavos}
                 detalhe={`inclui ${formatarMoeda(caixa.compras_centavos)} em compra de mercadoria`} />
          <Linha
            rotulo="Saldo"
            valor={caixa.saldo_centavos}
            detalhe={caixa.saldo_centavos < 0 ? 'saiu mais do que entrou no período' : undefined}
            destaque
          />
        </dl>

        {resultado.resultado_centavos !== caixa.saldo_centavos && (
          <Alerta tipo="informacao">
            O lucro ({formatarMoeda(resultado.resultado_centavos)}) e o saldo de caixa
            ({formatarMoeda(caixa.saldo_centavos)}) são diferentes porque{' '}
            <strong>{formatarMoeda(estoque.custo_centavos)}</strong> viraram mercadoria na
            prateleira. Esse dinheiro não sumiu — volta quando as {estoque.unidades} unidades
            forem vendidas.
          </Alerta>
        )}
      </Cartao>

      {/* ---------------- Estoque como patrimônio ---------------- */}
      <Cartao titulo="Estoque parado">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { rotulo: 'Unidades', valor: String(estoque.unidades) },
            { rotulo: 'Custou', valor: formatarMoeda(estoque.custo_centavos) },
            { rotulo: 'Vale (a venda)', valor: formatarMoeda(estoque.venda_centavos) },
            { rotulo: 'Lucro previsto', valor: formatarMoeda(estoque.lucro_previsto_centavos) },
          ].map((item) => (
            <div key={item.rotulo} className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs text-slate-500">{item.rotulo}</p>
              <p className="numerico mt-0.5 font-bold text-slate-900">{item.valor}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Se tudo for vendido pelo preço atual, entram mais{' '}
          {formatarMoeda(estoque.lucro_previsto_centavos)} de lucro.
        </p>
      </Cartao>

      {/* ---------------- Fluxo diário ---------------- */}
      <Cartao titulo="Entradas e saídas por dia">
        {grafico.length === 0 ? (
          <Vazio titulo="Nenhum movimento no período" />
        ) : (
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={grafico} margin={{ top: 5, right: 14, left: 4, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis
                  dataKey="data"
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  tickLine={false}
                  padding={{ left: 4, right: 4 }}
                  minTickGap={18}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={false}
                  width={54}
                  tickFormatter={(valor: number) =>
                    valor >= 1000
                      ? `${(valor / 1000).toFixed(1).replace('.0', '').replace('.', ',')}k`
                      : String(valor)
                  }
                />
                <Tooltip
                  formatter={(valor: number, nome: string) => [
                    formatarMoeda(Math.round(valor * 100)),
                    nome === 'entradas' ? 'Entradas' : 'Saídas',
                  ]}
                  contentStyle={{ borderRadius: 8, fontSize: 12, border: '1px solid #e2e8f0' }}
                />
                <Bar dataKey="entradas" fill="#059669" radius={[3, 3, 0, 0]} />
                <Bar dataKey="saidas" fill="#e11d48" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Cartao>
    </div>
  )
}

/** Linha de um demonstrativo: rótulo à esquerda, valor com sinal à direita. */
function Linha({
  rotulo,
  valor,
  detalhe,
  destaque = false,
}: {
  rotulo: string
  valor: number
  detalhe?: string
  destaque?: boolean
}) {
  // `-0 < 0` é falso em JavaScript, mas o Intl formata -0 como "-R$ 0,00":
  // uma despesa zerada apareceria com sinal de menos.
  const negativo = valor < 0

  return (
    <div
      className={`flex items-baseline justify-between gap-3 ${
        destaque ? 'border-t border-slate-200 pt-2.5' : ''
      }`}
    >
      <div className="min-w-0">
        <dt className={destaque ? 'font-semibold text-slate-800' : 'text-slate-600'}>{rotulo}</dt>
        {detalhe && <dd className="mt-0.5 text-xs text-slate-400">{detalhe}</dd>}
      </div>
      <dd
        className={`numerico shrink-0 ${destaque ? 'text-lg font-bold' : 'font-medium'} ${
          negativo ? 'text-rose-600' : 'text-slate-800'
        }`}
      >
        {negativo ? `− ${formatarMoeda(Math.abs(valor))}` : formatarMoeda(Math.abs(valor))}
      </dd>
    </div>
  )
}
