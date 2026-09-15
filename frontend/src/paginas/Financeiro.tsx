/** Contas a pagar e a receber, com fluxo de caixa realizado. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Plus, RotateCcw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import {
  Alerta, AreaTexto, Botao, BotaoIcone, CabecalhoPagina, Campo, Carregando, Cartao,
  Modal, Paginacao, Selecao, Selo, TabelaEnvolvida, Vazio,
} from '../componentes/ui'
import { ErroApi, api, querystring } from '../lib/api'
import { dataISO, formatarData, formatarMoeda, paraCentavos } from '../lib/formato'
import type { CategoriaFinanceira, Lancamento, Pagina } from '../lib/tipos'

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

  const { data: resumo } = useQuery({
    queryKey: ['financeiro-resumo'],
    queryFn: () => api.get<ResumoFinanceiro>('/financeiro/lancamentos/resumo/'),
  })

  const { data: fluxo } = useQuery({
    queryKey: ['fluxo-caixa'],
    queryFn: () => api.get<FluxoCaixa>('/financeiro/lancamentos/fluxo-de-caixa/'),
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

  const grafico = (fluxo?.dias ?? []).map((dia) => ({
    data: formatarData(dia.data).slice(0, 5),
    entradas: dia.entradas_centavos / 100,
    saidas: dia.saidas_centavos / 100,
  }))

  return (
    <>
      <CabecalhoPagina
        titulo="Financeiro"
        descricao="Contas a pagar, a receber e o que já foi realizado."
        acoes={
          <Botao icone={<Plus size={16} />} onClick={() => setModal('novo')}>
            Novo lançamento
          </Botao>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="cartao p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">A receber</p>
          <p className="numerico mt-1 text-2xl font-bold text-emerald-700">
            {formatarMoeda(resumo?.a_receber_centavos ?? 0)}
          </p>
          {(resumo?.a_receber_atrasado_centavos ?? 0) > 0 && (
            <p className="text-xs text-rose-600">
              {formatarMoeda(resumo!.a_receber_atrasado_centavos)} em atraso
            </p>
          )}
        </div>
        <div className="cartao p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">A pagar</p>
          <p className="numerico mt-1 text-2xl font-bold text-rose-700">
            {formatarMoeda(resumo?.a_pagar_centavos ?? 0)}
          </p>
          {(resumo?.a_pagar_atrasado_centavos ?? 0) > 0 && (
            <p className="text-xs text-rose-600">
              {formatarMoeda(resumo!.a_pagar_atrasado_centavos)} em atraso
            </p>
          )}
        </div>
        <div className="cartao p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Recebido no mês
          </p>
          <p className="numerico mt-1 text-2xl font-bold text-slate-900">
            {formatarMoeda(resumo?.recebido_no_mes_centavos ?? 0)}
          </p>
        </div>
        <div className="cartao p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Pago no mês</p>
          <p className="numerico mt-1 text-2xl font-bold text-slate-900">
            {formatarMoeda(resumo?.pago_no_mes_centavos ?? 0)}
          </p>
          <p className="text-xs text-slate-500">
            Saldo: {formatarMoeda((resumo?.recebido_no_mes_centavos ?? 0) - (resumo?.pago_no_mes_centavos ?? 0))}
          </p>
        </div>
      </div>

      <Cartao titulo="Fluxo de caixa realizado (30 dias)" className="mt-4">
        {grafico.length === 0 ? (
          <Vazio titulo="Nenhum lançamento realizado no período" />
        ) : (
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={grafico} margin={{ top: 5, right: 5, left: 4, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="data" tick={{ fontSize: 12, fill: '#64748b' }} tickLine={false} />
                <YAxis
                    tick={{ fontSize: 12, fill: '#64748b' }}
                    tickLine={false}
                    axisLine={false}
                    width={54}
                    tickFormatter={(valor: number) =>
                      // Uma casa decimal: sem ela, 1.500 e 2.400 virariam ambos "2k".
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

      <div className="mb-3 mt-5 grid gap-2 sm:grid-cols-3">
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
