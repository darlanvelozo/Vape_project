/** Relatórios gerenciais: mais vendidos, margem, curva ABC, giro e equipe. */

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import {
  CabecalhoPagina, Campo, Carregando, Cartao, Selo, TabelaEnvolvida, Vazio,
} from '../componentes/ui'
import { api, querystring } from '../lib/api'
import { useAutenticacao } from '../lib/auth'
import { diasAtras, formatarMoeda, formatarNumero, formatarPercentual } from '../lib/formato'

// ------------------------------------------------------------------ tipos

interface LinhaVendida {
  variacao: number
  descricao: string
  unidades: number
  receita_centavos: number
  lucro_centavos: number
}

interface LinhaMargem extends LinhaVendida {
  custo_centavos: number
  margem: number
}

interface LinhaABC {
  variacao: number
  descricao: string
  unidades: number
  receita_centavos: number
  participacao: number
  acumulado: number
  classe: 'A' | 'B' | 'C'
}

interface LinhaGiro {
  variacao: number
  descricao: string
  unidades_vendidas: number
  saldo_atual: number
  giro: number | null
  parado: boolean
}

interface LinhaForma {
  forma: string
  forma_display: string
  quantidade: number
  total_centavos: number
}

interface LinhaVendedor {
  usuario: number
  nome: string
  vendas: number
  faturamento_centavos: number
  lucro_centavos: number
  ticket_medio_centavos: number
}

type Relatorio = 'mais-vendidos' | 'margem' | 'curva-abc' | 'giro' | 'formas-pagamento' | 'vendedores'

const RELATORIOS: { chave: Relatorio; rotulo: string; somenteGestao?: boolean }[] = [
  { chave: 'mais-vendidos', rotulo: 'Mais vendidos' },
  { chave: 'margem', rotulo: 'Margem por produto', somenteGestao: true },
  { chave: 'curva-abc', rotulo: 'Curva ABC', somenteGestao: true },
  { chave: 'giro', rotulo: 'Giro de estoque', somenteGestao: true },
  { chave: 'formas-pagamento', rotulo: 'Formas de pagamento' },
  { chave: 'vendedores', rotulo: 'Equipe', somenteGestao: true },
]

const CORES = ['#3d55b4', '#059669', '#d97706', '#e11d48', '#7c3aed', '#0891b2']

/** Hook de leitura de um relatório, tipado pela resposta esperada. */
function useRelatorio<T>(chave: Relatorio, ativo: Relatorio, inicio: string, fim: string) {
  return useQuery({
    queryKey: ['relatorio', chave, inicio, fim],
    queryFn: () => api.get<T>(`/relatorios/${chave}/${querystring({ inicio, fim })}`),
    enabled: chave === ativo,
  })
}

export function Relatorios() {
  const { podeGerenciar } = useAutenticacao()
  const [ativo, setAtivo] = useState<Relatorio>('mais-vendidos')
  const [inicio, setInicio] = useState(diasAtras(30))
  const [fim, setFim] = useState('')

  const disponiveis = RELATORIOS.filter((item) => !item.somenteGestao || podeGerenciar)

  const maisVendidos = useRelatorio<{ itens: LinhaVendida[] }>('mais-vendidos', ativo, inicio, fim)
  const margem = useRelatorio<{ itens: LinhaMargem[] }>('margem', ativo, inicio, fim)
  const curvaABC = useRelatorio<{ itens: LinhaABC[] }>('curva-abc', ativo, inicio, fim)
  const giro = useRelatorio<{ itens: LinhaGiro[] }>('giro', ativo, inicio, fim)
  const formas = useRelatorio<{ formas: LinhaForma[] }>('formas-pagamento', ativo, inicio, fim)
  const vendedores = useRelatorio<{ vendedores: LinhaVendedor[] }>('vendedores', ativo, inicio, fim)

  const carregando = [maisVendidos, margem, curvaABC, giro, formas, vendedores].some(
    (consulta) => consulta.isLoading && consulta.fetchStatus !== 'idle',
  )

  return (
    <>
      <CabecalhoPagina
        titulo="Relatórios"
        descricao="O que vende, o que dá margem e o que está parado na prateleira."
      />

      <div className="mb-4 grid gap-2 sm:grid-cols-[1fr_auto_auto]">
        <div className="flex flex-wrap gap-1.5">
          {disponiveis.map((item) => (
            <button
              key={item.chave}
              onClick={() => setAtivo(item.chave)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                ativo === item.chave
                  ? 'bg-marca-700 text-white shadow-sm'
                  : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'
              }`}
            >
              {item.rotulo}
            </button>
          ))}
        </div>
        <Campo type="date" value={inicio} onChange={(evento) => setInicio(evento.target.value)} />
        <Campo type="date" value={fim} onChange={(evento) => setFim(evento.target.value)} />
      </div>

      {carregando ? (
        <Carregando />
      ) : (
        <Cartao semCorpo>
          {ativo === 'mais-vendidos' && <TabelaMaisVendidos linhas={maisVendidos.data?.itens ?? []} />}
          {ativo === 'margem' && <TabelaMargem linhas={margem.data?.itens ?? []} />}
          {ativo === 'curva-abc' && <TabelaCurvaABC linhas={curvaABC.data?.itens ?? []} />}
          {ativo === 'giro' && <TabelaGiro linhas={giro.data?.itens ?? []} />}
          {ativo === 'formas-pagamento' && <GraficoFormas linhas={formas.data?.formas ?? []} />}
          {ativo === 'vendedores' && <TabelaVendedores linhas={vendedores.data?.vendedores ?? []} />}
        </Cartao>
      )}
    </>
  )
}

function TabelaMaisVendidos({ linhas }: { linhas: LinhaVendida[] }) {
  if (!linhas.length) return <Vazio titulo="Nenhuma venda no período" />

  return (
    <TabelaEnvolvida>
      <table className="tabela">
        <thead>
          <tr>
            <th>#</th>
            <th>Produto</th>
            <th className="text-right">Unidades</th>
            <th className="text-right">Receita</th>
            <th className="text-right">Lucro</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((linha, indice) => (
            <tr key={linha.variacao}>
              <td className="numerico text-slate-400">{indice + 1}</td>
              <td className="text-sm font-medium">{linha.descricao}</td>
              <td className="numerico text-right">{formatarNumero(linha.unidades)}</td>
              <td className="numerico text-right font-semibold">
                {formatarMoeda(linha.receita_centavos)}
              </td>
              <td className="numerico text-right text-emerald-700">
                {formatarMoeda(linha.lucro_centavos)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TabelaEnvolvida>
  )
}

function TabelaMargem({ linhas }: { linhas: LinhaMargem[] }) {
  if (!linhas.length) return <Vazio titulo="Nenhuma venda no período" />

  return (
    <TabelaEnvolvida>
      <table className="tabela">
        <thead>
          <tr>
            <th>Produto</th>
            <th className="text-right">Unidades</th>
            <th className="text-right">Receita</th>
            <th className="text-right">Custo</th>
            <th className="text-right">Lucro</th>
            <th className="text-right">Margem</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((linha) => (
            <tr key={linha.variacao}>
              <td className="text-sm font-medium">{linha.descricao}</td>
              <td className="numerico text-right">{formatarNumero(linha.unidades)}</td>
              <td className="numerico text-right">{formatarMoeda(linha.receita_centavos)}</td>
              <td className="numerico text-right text-slate-500">
                {formatarMoeda(linha.custo_centavos)}
              </td>
              <td className="numerico text-right font-semibold text-emerald-700">
                {formatarMoeda(linha.lucro_centavos)}
              </td>
              <td className="text-right">
                <Selo cor={linha.margem >= 50 ? 'verde' : linha.margem >= 25 ? 'ambar' : 'vermelho'}>
                  {formatarPercentual(linha.margem)}
                </Selo>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TabelaEnvolvida>
  )
}

function TabelaCurvaABC({ linhas }: { linhas: LinhaABC[] }) {
  if (!linhas.length) return <Vazio titulo="Nenhuma venda no período" />

  return (
    <>
      <div className="border-b border-slate-200 px-4 py-3 text-xs text-slate-500">
        Classe <strong>A</strong>: até 80% da receita acumulada · <strong>B</strong>: até 95% ·{' '}
        <strong>C</strong>: o restante. Os itens A são os que não podem faltar na prateleira.
      </div>
      <TabelaEnvolvida>
        <table className="tabela">
          <thead>
            <tr>
              <th>Classe</th>
              <th>Produto</th>
              <th className="text-right">Unidades</th>
              <th className="text-right">Receita</th>
              <th className="text-right">Participação</th>
              <th className="text-right">Acumulado</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha) => (
              <tr key={linha.variacao}>
                <td>
                  <Selo cor={linha.classe === 'A' ? 'verde' : linha.classe === 'B' ? 'ambar' : 'cinza'}>
                    {linha.classe}
                  </Selo>
                </td>
                <td className="text-sm font-medium">{linha.descricao}</td>
                <td className="numerico text-right">{formatarNumero(linha.unidades)}</td>
                <td className="numerico text-right font-semibold">
                  {formatarMoeda(linha.receita_centavos)}
                </td>
                <td className="numerico text-right">{formatarPercentual(linha.participacao)}</td>
                <td className="numerico text-right text-slate-500">
                  {formatarPercentual(linha.acumulado)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TabelaEnvolvida>
    </>
  )
}

function TabelaGiro({ linhas }: { linhas: LinhaGiro[] }) {
  if (!linhas.length) return <Vazio titulo="Sem dados de giro no período" />

  return (
    <TabelaEnvolvida>
      <table className="tabela">
        <thead>
          <tr>
            <th>Produto</th>
            <th className="text-right">Vendidas</th>
            <th className="text-right">Saldo atual</th>
            <th className="text-right">Giro</th>
            <th>Situação</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((linha) => (
            <tr key={linha.variacao}>
              <td className="text-sm font-medium">{linha.descricao}</td>
              <td className="numerico text-right">{formatarNumero(linha.unidades_vendidas)}</td>
              <td className="numerico text-right">{formatarNumero(linha.saldo_atual)}</td>
              <td className="numerico text-right font-semibold">
                {linha.giro === null ? '—' : linha.giro.toFixed(2).replace('.', ',')}
              </td>
              <td>
                {linha.parado ? (
                  <Selo cor="ambar">parado no estoque</Selo>
                ) : linha.giro === null ? (
                  <Selo cor="vermelho">ruptura (saldo zero)</Selo>
                ) : (
                  <Selo cor="verde">girando</Selo>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TabelaEnvolvida>
  )
}

function GraficoFormas({ linhas }: { linhas: LinhaForma[] }) {
  if (!linhas.length) return <Vazio titulo="Nenhum recebimento no período" />

  const grafico = linhas.map((linha) => ({
    nome: linha.forma_display,
    valor: linha.total_centavos / 100,
  }))
  const total = linhas.reduce((soma, linha) => soma + linha.total_centavos, 0)

  return (
    <div className="grid gap-4 p-4 lg:grid-cols-2">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={grafico} dataKey="valor" nameKey="nome" innerRadius={55} outerRadius={95}>
              {grafico.map((_, indice) => (
                <Cell key={indice} fill={CORES[indice % CORES.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(valor: number) => formatarMoeda(Math.round(valor * 100))}
              contentStyle={{ borderRadius: 8, fontSize: 12, border: '1px solid #e2e8f0' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <TabelaEnvolvida>
        <table className="tabela">
          <thead>
            <tr>
              <th>Forma</th>
              <th className="text-right">Qtd.</th>
              <th className="text-right">Total</th>
              <th className="text-right">%</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha, indice) => (
              <tr key={linha.forma}>
                <td className="flex items-center gap-2 text-sm">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: CORES[indice % CORES.length] }}
                  />
                  {linha.forma_display}
                </td>
                <td className="numerico text-right">{linha.quantidade}</td>
                <td className="numerico text-right font-semibold">
                  {formatarMoeda(linha.total_centavos)}
                </td>
                <td className="numerico text-right text-slate-500">
                  {total ? formatarPercentual((linha.total_centavos / total) * 100) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </TabelaEnvolvida>
    </div>
  )
}

function TabelaVendedores({ linhas }: { linhas: LinhaVendedor[] }) {
  if (!linhas.length) return <Vazio titulo="Nenhuma venda no período" />

  return (
    <TabelaEnvolvida>
      <table className="tabela">
        <thead>
          <tr>
            <th>Vendedor</th>
            <th className="text-right">Vendas</th>
            <th className="text-right">Faturamento</th>
            <th className="text-right">Ticket médio</th>
            <th className="text-right">Lucro gerado</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((linha) => (
            <tr key={linha.usuario}>
              <td className="text-sm font-medium">{linha.nome}</td>
              <td className="numerico text-right">{formatarNumero(linha.vendas)}</td>
              <td className="numerico text-right font-semibold">
                {formatarMoeda(linha.faturamento_centavos)}
              </td>
              <td className="numerico text-right">{formatarMoeda(linha.ticket_medio_centavos)}</td>
              <td className="numerico text-right text-emerald-700">
                {formatarMoeda(linha.lucro_centavos)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TabelaEnvolvida>
  )
}
