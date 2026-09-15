/** Painel inicial: o resumo que o lojista abre de manhã. */

import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle, ArrowDownRight, ArrowUpRight, Boxes, PackageX,
  ShoppingCart, TrendingUp, Wallet,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

import { CabecalhoPagina, Carregando, Cartao, Selo, Vazio } from '../componentes/ui'
import { api } from '../lib/api'
import { formatarData, formatarMoeda, formatarNumero, formatarValor } from '../lib/formato'
import type { Dashboard } from '../lib/tipos'

interface SeriePeriodo {
  dias: { data: string; vendas: number; faturamento_centavos: number; lucro_centavos: number }[]
  total_faturamento_centavos: number
}

interface MaisVendidos {
  itens: { variacao: number; descricao: string; unidades: number; receita_centavos: number }[]
}

function Indicador({
  titulo,
  valor,
  detalhe,
  icone,
  cor = 'text-marca-700',
  destino,
}: {
  titulo: string
  valor: string
  detalhe?: ReactNode
  icone: ReactNode
  cor?: string
  destino?: string
}) {
  const conteudo = (
    <div className="cartao flex items-start justify-between gap-3 p-4 transition hover:shadow-md">
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{titulo}</p>
        <p className="numerico mt-1 truncate text-xl font-bold text-slate-900 sm:text-2xl">{valor}</p>
        {detalhe && <div className="mt-1 text-xs text-slate-500">{detalhe}</div>}
      </div>
      <span className={`shrink-0 rounded-lg bg-slate-50 p-2 ${cor}`}>{icone}</span>
    </div>
  )
  return destino ? <Link to={destino}>{conteudo}</Link> : conteudo
}

export function Painel() {
  const { data: painel, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<Dashboard>('/relatorios/dashboard/'),
    refetchInterval: 60_000,
  })

  const { data: serie } = useQuery({
    queryKey: ['vendas-periodo'],
    queryFn: () => api.get<SeriePeriodo>('/relatorios/vendas-por-periodo/'),
  })

  const { data: ranking } = useQuery({
    queryKey: ['mais-vendidos-painel'],
    queryFn: () => api.get<MaisVendidos>('/relatorios/mais-vendidos/?limite=6'),
  })

  if (isLoading || !painel) return <Carregando texto="Montando o painel…" />

  const grafico = (serie?.dias ?? []).map((dia) => ({
    data: formatarData(dia.data).slice(0, 5),
    faturamento: dia.faturamento_centavos / 100,
    lucro: dia.lucro_centavos / 100,
  }))

  return (
    <>
      <CabecalhoPagina
        titulo="Painel"
        descricao="Como a loja está hoje e no mês."
        acoes={
          painel.caixa.aberto ? (
            <Link to="/pdv" className="flex min-h-[44px] items-center">
              <Selo cor="verde">
                Caixa aberto · {formatarMoeda(painel.caixa.saldo_centavos)}
              </Selo>
            </Link>
          ) : (
            <Link to="/caixa" className="flex min-h-[44px] items-center">
              <Selo cor="ambar">Caixa fechado — abra para vender</Selo>
            </Link>
          )
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Indicador
          titulo="Vendas hoje"
          valor={formatarMoeda(painel.hoje.faturamento_centavos)}
          detalhe={
            <span>
              {formatarNumero(painel.hoje.vendas)} venda(s) · ticket{' '}
              {formatarMoeda(painel.hoje.ticket_medio_centavos)}
            </span>
          }
          icone={<ShoppingCart size={20} />}
          destino="/vendas"
        />
        <Indicador
          titulo="Lucro hoje"
          valor={formatarMoeda(painel.hoje.lucro_centavos)}
          detalhe={
            <span className="inline-flex items-center gap-1 text-emerald-600">
              <ArrowUpRight size={13} />
              Mês: {formatarMoeda(painel.mes.lucro_centavos)}
            </span>
          }
          icone={<TrendingUp size={20} />}
          cor="text-emerald-600"
        />
        <Indicador
          titulo="Estoque"
          valor={formatarNumero(painel.estoque.unidades)}
          detalhe={
            <span>
              unidades · {formatarMoeda(painel.estoque.valor_custo_centavos)} em custo
            </span>
          }
          icone={<Boxes size={20} />}
          destino="/estoque"
        />
        <Indicador
          titulo="A receber"
          valor={formatarMoeda(painel.financeiro.a_receber_centavos)}
          detalhe={
            <span className="inline-flex items-center gap-1 text-rose-600">
              <ArrowDownRight size={13} />
              A pagar: {formatarMoeda(painel.financeiro.a_pagar_centavos)}
            </span>
          }
          icone={<Wallet size={20} />}
          destino="/financeiro"
        />
      </div>

      {(painel.estoque.abaixo_do_minimo > 0 ||
        painel.estoque.zerados > 0 ||
        painel.financeiro.atrasados > 0) && (
        <div className="mt-4 flex flex-wrap gap-2">
          {painel.estoque.abaixo_do_minimo > 0 && (
            <Link to="/estoque?filtro=minimo">
              <span className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 text-sm text-amber-800 transition hover:bg-amber-100">
                <AlertTriangle size={15} />
                {painel.estoque.abaixo_do_minimo} item(ns) no estoque mínimo
              </span>
            </Link>
          )}
          {painel.estoque.zerados > 0 && (
            <Link to="/estoque?filtro=zerados">
              <span className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 text-sm text-rose-800 transition hover:bg-rose-100">
                <PackageX size={15} />
                {painel.estoque.zerados} item(ns) zerado(s)
              </span>
            </Link>
          )}
          {painel.financeiro.atrasados > 0 && (
            <Link to="/financeiro?filtro=atrasados">
              <span className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 text-sm text-rose-800 transition hover:bg-rose-100">
                <AlertTriangle size={15} />
                {painel.financeiro.atrasados} conta(s) em atraso
              </span>
            </Link>
          )}
        </div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Cartao titulo="Faturamento dos últimos 30 dias" className="lg:col-span-2">
          {grafico.length === 0 ? (
            <Vazio
              titulo="Ainda não há vendas no período"
              descricao="Assim que a primeira venda for registrada, o gráfico aparece aqui."
            />
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={grafico} margin={{ top: 5, right: 5, left: 4, bottom: 0 }}>
                  <defs>
                    <linearGradient id="corFaturamento" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3d55b4" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#3d55b4" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="corLucro" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#059669" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#059669" stopOpacity={0} />
                    </linearGradient>
                  </defs>
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
                      nome === 'faturamento' ? 'Faturamento' : 'Lucro',
                    ]}
                    contentStyle={{ borderRadius: 8, fontSize: 12, border: '1px solid #e2e8f0' }}
                  />
                  <Area
                    type="monotone" dataKey="faturamento" stroke="#3d55b4"
                    strokeWidth={2} fill="url(#corFaturamento)"
                  />
                  <Area
                    type="monotone" dataKey="lucro" stroke="#059669"
                    strokeWidth={2} fill="url(#corLucro)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Cartao>

        <Cartao titulo="Mais vendidos (30 dias)" semCorpo>
          {!ranking?.itens.length ? (
            <Vazio titulo="Sem vendas no período" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {ranking.itens.map((item, indice) => (
                <li key={item.variacao} className="flex items-center gap-3 px-4 py-2.5">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-marca-50 text-xs font-bold text-marca-700">
                    {indice + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800">{item.descricao}</p>
                    <p className="text-xs text-slate-500">{item.unidades} unidade(s)</p>
                  </div>
                  <span className="numerico shrink-0 text-sm font-semibold text-slate-700">
                    {formatarValor(item.receita_centavos)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Cartao>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Cartao titulo="Mês atual">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Vendas</dt>
              <dd className="numerico font-medium">{formatarNumero(painel.mes.vendas)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Faturamento</dt>
              <dd className="numerico font-medium">{formatarMoeda(painel.mes.faturamento_centavos)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Ticket médio</dt>
              <dd className="numerico font-medium">{formatarMoeda(painel.mes.ticket_medio_centavos)}</dd>
            </div>
          </dl>
        </Cartao>
        <Cartao titulo="Caixa">
          {painel.caixa.aberto ? (
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">Situação</dt>
                <dd><Selo cor="verde">Aberto</Selo></dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Dinheiro na gaveta</dt>
                <dd className="numerico font-medium">{formatarMoeda(painel.caixa.saldo_centavos)}</dd>
              </div>
              <Link
                to="/caixa"
                className="-mx-1 flex min-h-[44px] items-center px-1 text-sm font-medium
                           text-marca-700 hover:underline"
              >
                Conferir e fechar →
              </Link>
            </dl>
          ) : (
            <div className="text-sm text-slate-500">
              <p>Nenhum caixa aberto.</p>
              <Link
                to="/caixa"
                className="-mx-1 mt-1 flex min-h-[44px] items-center px-1 text-sm font-medium
                           text-marca-700 hover:underline"
              >
                Abrir caixa →
              </Link>
            </div>
          )}
        </Cartao>
        <Cartao titulo="Cadastros">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Clientes ativos</dt>
              <dd className="numerico font-medium">{formatarNumero(painel.clientes_ativos)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Itens zerados</dt>
              <dd className="numerico font-medium">{formatarNumero(painel.estoque.zerados)}</dd>
            </div>
            <Link
              to="/produtos"
              className="-mx-1 flex min-h-[44px] items-center px-1 text-sm font-medium
                         text-marca-700 hover:underline"
            >
              Gerenciar produtos →
            </Link>
          </dl>
        </Cartao>
      </div>
    </>
  )
}
