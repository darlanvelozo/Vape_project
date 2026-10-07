/** Posição de estoque, entradas, perdas e inventário. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ClipboardCheck, PackageMinus, PackagePlus } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import {
  Alerta, Botao, CabecalhoPagina, Campo, Carregando, Cartao, Modal, Paginacao,
  Selo, TabelaEnvolvida, Vazio,
} from '../componentes/ui'
import { ErroApi, api, querystring } from '../lib/api'
import { useAutenticacao } from '../lib/auth'
import { formatarDataHora, formatarMoeda, formatarNumero, paraCentavos } from '../lib/formato'
import type { MovimentoEstoque, Pagina, PosicaoEstoque, VariacaoResumo } from '../lib/tipos'

interface ResumoEstoque {
  variacoes_ativas: number
  unidades_em_estoque: number
  valor_custo_centavos: number
  valor_venda_centavos: number
  abaixo_do_minimo: number
  zerados: number
}

type Operacao = 'entrada' | 'perda' | 'inventario'

export function Estoque() {
  const { podeGerenciar } = useAutenticacao()
  const [parametros] = useSearchParams()
  const [aba, setAba] = useState<'posicao' | 'movimentos'>('posicao')
  const [busca, setBusca] = useState('')
  const [filtro, setFiltro] = useState(parametros.get('filtro') ?? '')
  const [operacao, setOperacao] = useState<Operacao | null>(null)
  const [pagina, setPagina] = useState(1)

  const { data: resumo } = useQuery({
    queryKey: ['estoque-resumo'],
    queryFn: () => api.get<ResumoEstoque>('/estoque/posicao/resumo/'),
  })

  const { data: posicao, isLoading } = useQuery({
    queryKey: ['estoque-posicao', busca, filtro, pagina],
    queryFn: () =>
      api.get<Pagina<PosicaoEstoque>>(
        `/estoque/posicao/${querystring({
          search: busca,
          abaixo_do_minimo: filtro === 'minimo' ? 'true' : undefined,
          zerados: filtro === 'zerados' ? 'true' : undefined,
          ordering: 'saldo',
          page: pagina,
        })}`,
      ),
    enabled: aba === 'posicao',
  })

  const { data: movimentos } = useQuery({
    queryKey: ['estoque-movimentos', busca, pagina],
    queryFn: () =>
      api.get<Pagina<MovimentoEstoque>>(
        `/estoque/movimentos/${querystring({ search: busca, page: pagina })}`,
      ),
    enabled: aba === 'movimentos',
  })

  return (
    <>
      <CabecalhoPagina
        titulo="Estoque"
        descricao="Saldo por variação e o extrato de tudo que entrou e saiu."
        acoes={
          podeGerenciar && (
            <>
              <Botao icone={<PackagePlus size={16} />} onClick={() => setOperacao('entrada')}>
                Entrada
              </Botao>
              <Botao variante="secundario" icone={<PackageMinus size={16} />} onClick={() => setOperacao('perda')}>
                Perda
              </Botao>
              <Botao variante="secundario" icone={<ClipboardCheck size={16} />} onClick={() => setOperacao('inventario')}>
                Inventário
              </Botao>
            </>
          )
        }
      />

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <div className="cartao p-3 sm:p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Unidades</p>
          <p className="numerico mt-1 text-lg font-bold sm:text-2xl text-slate-900">
            {formatarNumero(resumo?.unidades_em_estoque ?? 0)}
          </p>
          <p className="text-xs text-slate-500">{resumo?.variacoes_ativas ?? 0} variações ativas</p>
        </div>
        <div className="cartao p-3 sm:p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Valor a custo</p>
          <p className="numerico mt-1 text-lg font-bold sm:text-2xl text-slate-900">
            {formatarMoeda(resumo?.valor_custo_centavos ?? 0)}
          </p>
          <p className="text-xs text-slate-500">
            a venda: {formatarMoeda(resumo?.valor_venda_centavos ?? 0)}
          </p>
        </div>
        <button
          onClick={() => { setAba('posicao'); setFiltro(filtro === 'minimo' ? '' : 'minimo') }}
          className={`cartao p-3 sm:p-4 text-left transition hover:shadow-md ${filtro === 'minimo' ? 'ring-2 ring-amber-400' : ''}`}
        >
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">No mínimo</p>
          <p className="numerico mt-1 text-lg font-bold sm:text-2xl text-amber-600">
            {formatarNumero(resumo?.abaixo_do_minimo ?? 0)}
          </p>
          <p className="text-xs text-slate-500">item(ns) para repor</p>
        </button>
        <button
          onClick={() => { setAba('posicao'); setFiltro(filtro === 'zerados' ? '' : 'zerados') }}
          className={`cartao p-3 sm:p-4 text-left transition hover:shadow-md ${filtro === 'zerados' ? 'ring-2 ring-rose-400' : ''}`}
        >
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Zerados</p>
          <p className="numerico mt-1 text-lg font-bold sm:text-2xl text-rose-600">
            {formatarNumero(resumo?.zerados ?? 0)}
          </p>
          <p className="text-xs text-slate-500">sem saldo</p>
        </button>
      </div>

      <div className="mb-3 mt-5 flex flex-wrap items-center gap-2">
        <div className="flex gap-1 rounded-lg bg-slate-200/60 p-1">
          {(['posicao', 'movimentos'] as const).map((valor) => (
            <button
              key={valor}
              onClick={() => { setAba(valor); setPagina(1) }}
              className={`min-h-[44px] rounded-md px-3 text-sm font-medium transition ${
                aba === valor ? 'bg-white text-marca-800 shadow-sm' : 'text-slate-600'
              }`}
            >
              {valor === 'posicao' ? 'Posição' : 'Movimentações'}
            </button>
          ))}
        </div>
        <Campo
          className="min-w-[200px] flex-1"
          placeholder="Buscar produto, sabor ou SKU…"
          value={busca}
          onChange={(evento) => { setBusca(evento.target.value); setPagina(1) }}
        />
      </div>

      <Cartao semCorpo>
        {aba === 'posicao' ? (
          isLoading ? (
            <Carregando />
          ) : !posicao?.results.length ? (
            <Vazio titulo="Nenhum item encontrado" />
          ) : (
            <TabelaEnvolvida>
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Produto</th>
                    <th>SKU</th>
                    <th className="text-right">Saldo</th>
                    <th className="text-right">Mínimo</th>
                    <th className="text-right">Custo un.</th>
                    <th className="text-right">Valor total</th>
                  </tr>
                </thead>
                <tbody>
                  {posicao.results.map((linha) => (
                    <tr key={linha.id}>
                      <td>
                        <p className="text-sm font-medium text-slate-800">{linha.descricao_completa}</p>
                        {linha.categoria_nome && (
                          <p className="text-xs text-slate-400">{linha.categoria_nome}</p>
                        )}
                      </td>
                      <td className="text-xs text-slate-500">{linha.sku || '—'}</td>
                      <td className="text-right">
                        <Selo
                          cor={linha.saldo <= 0 ? 'vermelho' : linha.abaixo_do_minimo ? 'ambar' : 'verde'}
                        >
                          {linha.saldo}
                        </Selo>
                      </td>
                      <td className="numerico text-right text-slate-500">{linha.estoque_minimo || '—'}</td>
                      <td className="numerico text-right">{formatarMoeda(linha.preco_custo_centavos)}</td>
                      <td className="numerico text-right font-semibold">
                        {formatarMoeda(linha.valor_custo_total_centavos)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TabelaEnvolvida>
          )
        ) : !movimentos?.results.length ? (
          <Vazio titulo="Nenhuma movimentação registrada" />
        ) : (
          <TabelaEnvolvida>
            <table className="tabela">
              <thead>
                <tr>
                  <th>Quando</th>
                  <th>Produto</th>
                  <th>Tipo</th>
                  <th className="text-right">Qtd.</th>
                  <th className="text-right">Saldo após</th>
                  <th>Motivo</th>
                  <th>Usuário</th>
                </tr>
              </thead>
              <tbody>
                {movimentos.results.map((movimento) => (
                  <tr key={movimento.id}>
                    <td className="whitespace-nowrap text-xs text-slate-500">
                      {formatarDataHora(movimento.criado_em)}
                    </td>
                    <td className="text-sm">{movimento.variacao_descricao}</td>
                    <td className="text-sm">{movimento.tipo_display}</td>
                    <td
                      className={`numerico text-right font-semibold ${
                        movimento.quantidade_com_sinal < 0 ? 'text-rose-600' : 'text-emerald-700'
                      }`}
                    >
                      {movimento.quantidade_com_sinal > 0 ? '+' : ''}
                      {movimento.quantidade_com_sinal}
                    </td>
                    <td className="numerico text-right">{movimento.saldo_apos}</td>
                    <td className="max-w-[16rem] truncate text-xs text-slate-500">
                      {movimento.motivo || '—'}
                    </td>
                    <td className="text-xs text-slate-500">{movimento.usuario_nome || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TabelaEnvolvida>
        )}
        <Paginacao
          pagina={pagina}
          total={(aba === 'posicao' ? posicao?.count : movimentos?.count) ?? 0}
          aoMudar={setPagina}
        />
      </Cartao>

      {operacao && <ModalMovimento operacao={operacao} aoFechar={() => setOperacao(null)} />}
    </>
  )
}

function ModalMovimento({ operacao, aoFechar }: { operacao: Operacao; aoFechar: () => void }) {
  const clienteQuery = useQueryClient()
  const [termo, setTermo] = useState('')
  const [selecionada, setSelecionada] = useState<VariacaoResumo | null>(null)
  const [quantidade, setQuantidade] = useState('')
  const [custo, setCusto] = useState('')
  const [motivo, setMotivo] = useState('')
  const [documento, setDocumento] = useState('')
  const [erro, setErro] = useState<string | null>(null)

  const { data: opcoes = [] } = useQuery({
    queryKey: ['busca-variacao', termo],
    queryFn: () => api.get<VariacaoResumo[]>(`/variacoes/busca-pdv/?q=${encodeURIComponent(termo)}`),
  })

  const titulos: Record<Operacao, { titulo: string; descricao: string; rotulo: string }> = {
    entrada: {
      titulo: 'Entrada de estoque',
      descricao: 'Reposição avulsa. Compras com fornecedor têm fluxo próprio.',
      rotulo: 'Quantidade que entrou',
    },
    perda: {
      titulo: 'Registrar perda',
      descricao: 'Quebra, vencimento, furto — sai do estoque sem virar venda.',
      rotulo: 'Quantidade perdida',
    },
    inventario: {
      titulo: 'Ajuste por inventário',
      descricao: 'Informe quanto foi contado na prateleira; o sistema calcula a diferença.',
      rotulo: 'Quantidade contada',
    },
  }

  const enviar = useMutation({
    mutationFn: () => {
      const caminho =
        operacao === 'inventario'
          ? '/estoque/movimentos/inventario/'
          : `/estoque/movimentos/${operacao}/`

      const corpo: Record<string, unknown> =
        operacao === 'inventario'
          ? { variacao: selecionada!.id, contagem: Number(quantidade), motivo }
          : { variacao: selecionada!.id, quantidade: Number(quantidade), motivo, documento }

      if (operacao === 'entrada' && custo) {
        corpo.custo_unitario_centavos = paraCentavos(custo)
      }
      return api.post(caminho, corpo)
    },
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['estoque-posicao'] })
      clienteQuery.invalidateQueries({ queryKey: ['estoque-movimentos'] })
      clienteQuery.invalidateQueries({ queryKey: ['estoque-resumo'] })
      clienteQuery.invalidateQueries({ queryKey: ['produtos'] })
      aoFechar()
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha.message : 'Falha ao registrar.'),
  })

  const info = titulos[operacao]

  return (
    <Modal aberto aoFechar={aoFechar} titulo={info.titulo} descricao={info.descricao}>
      <form className="space-y-3" onSubmit={(evento) => { evento.preventDefault(); enviar.mutate() }}>
        {selecionada ? (
          <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2.5">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-800">
                {selecionada.descricao_completa}
              </p>
              <p className="text-xs text-slate-500">Saldo atual: {selecionada.saldo}</p>
            </div>
            <button
              type="button"
              onClick={() => setSelecionada(null)}
              className="shrink-0 text-xs text-marca-700 hover:underline"
            >
              trocar
            </button>
          </div>
        ) : (
          <div>
            <Campo
              rotulo="Produto"
              placeholder="Buscar por nome, sabor, SKU…"
              value={termo}
              onChange={(evento) => setTermo(evento.target.value)}
              autoFocus
            />
            <ul className="mt-2 max-h-48 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
              {opcoes.length === 0 && (
                <li className="px-3 py-4 text-center text-sm text-slate-400">
                  Nenhum produto encontrado.
                </li>
              )}
              {opcoes.map((variacao) => (
                <li key={variacao.id}>
                  <button
                    type="button"
                    onClick={() => setSelecionada(variacao)}
                    className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left transition hover:bg-slate-50"
                  >
                    <span className="truncate text-sm">{variacao.descricao_completa}</span>
                    <span className="numerico shrink-0 text-xs text-slate-500">
                      {variacao.saldo} un.
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {selecionada && (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              <Campo
                rotulo={info.rotulo}
                value={quantidade}
                onChange={(evento) => setQuantidade(evento.target.value)}
                inputMode="numeric"
                required
                autoFocus
              />
              {operacao === 'entrada' && (
                <Campo
                  rotulo="Custo unitário"
                  value={custo}
                  onChange={(evento) => setCusto(evento.target.value)}
                  placeholder="0,00"
                  inputMode="decimal"
                  dica="Recalcula o custo médio."
                />
              )}
            </div>

            <Campo
              rotulo="Motivo"
              value={motivo}
              onChange={(evento) => setMotivo(evento.target.value)}
              placeholder="Opcional"
            />

            {operacao !== 'inventario' && (
              <Campo
                rotulo="Documento"
                value={documento}
                onChange={(evento) => setDocumento(evento.target.value)}
                placeholder="Nota, pedido… (opcional)"
              />
            )}
          </>
        )}

        {erro && <Alerta>{erro}</Alerta>}

        <div className="flex gap-2 pt-1">
          <Botao type="button" variante="secundario" className="flex-1" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao
            type="submit"
            className="flex-1"
            carregando={enviar.isPending}
            disabled={!selecionada || !quantidade}
          >
            Registrar
          </Botao>
        </div>
      </form>
    </Modal>
  )
}
