/** Histórico de vendas, com detalhe e cancelamento. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Ban, Eye } from 'lucide-react'
import { useState } from 'react'

import {
  Alerta, Botao, CabecalhoPagina, Campo, Carregando, Cartao, Modal, Paginacao,
  Selecao, Selo, TabelaEnvolvida, Vazio,
} from '../componentes/ui'
import { ErroApi, api, querystring } from '../lib/api'
import { useAutenticacao } from '../lib/auth'
import { diasAtras, formatarDataHora, formatarMoeda } from '../lib/formato'
import type { Pagina, Venda, VendaResumo } from '../lib/tipos'

const CORES_STATUS: Record<string, 'verde' | 'ambar' | 'vermelho'> = {
  finalizada: 'verde',
  aberta: 'ambar',
  cancelada: 'vermelho',
}

export function Vendas() {
  const { podeGerenciar } = useAutenticacao()
  const [status, setStatus] = useState('')
  const [inicio, setInicio] = useState(diasAtras(30))
  const [fim, setFim] = useState('')
  const [detalhe, setDetalhe] = useState<number | null>(null)
  const [pagina, setPagina] = useState(1)

  const { data: vendas, isLoading } = useQuery({
    queryKey: ['vendas', status, inicio, fim, pagina],
    queryFn: () =>
      api.get<Pagina<VendaResumo>>(
        `/vendas/${querystring({
          status,
          data_inicio: inicio,
          data_fim: fim,
          ordering: '-criado_em',
          page: pagina,
        })}`,
      ),
  })

  return (
    <>
      <CabecalhoPagina titulo="Vendas" descricao="Tudo que foi vendido, com detalhe e estorno." />

      <div className="mb-3 grid gap-2 sm:grid-cols-3">
        <Selecao
          value={status}
          onChange={(evento) => { setStatus(evento.target.value); setPagina(1) }}
        >
          <option value="">Todos os status</option>
          <option value="finalizada">Finalizadas</option>
          <option value="aberta">Abertas</option>
          <option value="cancelada">Canceladas</option>
        </Selecao>
        <Campo
          type="date"
          value={inicio}
          onChange={(evento) => { setInicio(evento.target.value); setPagina(1) }}
        />
        <Campo
          type="date"
          value={fim}
          onChange={(evento) => { setFim(evento.target.value); setPagina(1) }}
        />
      </div>

      <Cartao semCorpo>
        {isLoading ? (
          <Carregando />
        ) : !vendas?.results.length ? (
          <Vazio titulo="Nenhuma venda no período" />
        ) : (
          <TabelaEnvolvida>
            <table className="tabela">
              <thead>
                <tr>
                  <th>Nº</th>
                  <th>Data</th>
                  <th>Cliente</th>
                  <th>Vendedor</th>
                  <th className="text-right">Itens</th>
                  <th className="text-right">Total</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {vendas.results.map((venda) => (
                  <tr key={venda.id}>
                    <td className="numerico font-semibold">#{venda.numero}</td>
                    <td className="whitespace-nowrap text-xs text-slate-500">
                      {formatarDataHora(venda.finalizada_em ?? venda.criado_em)}
                    </td>
                    <td className="text-sm">{venda.cliente_nome || '—'}</td>
                    <td className="text-sm text-slate-600">{venda.vendedor_nome}</td>
                    <td className="numerico text-right">{venda.quantidade_itens}</td>
                    <td className="numerico text-right font-semibold">
                      {formatarMoeda(venda.total_centavos)}
                    </td>
                    <td>
                      <Selo cor={CORES_STATUS[venda.status] ?? 'cinza'}>{venda.status_display}</Selo>
                    </td>
                    <td className="text-right">
                      <button
                        onClick={() => setDetalhe(venda.id)}
                        className="rounded p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-marca-700"
                        title="Ver detalhes"
                      >
                        <Eye size={15} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TabelaEnvolvida>
        )}
        <Paginacao pagina={pagina} total={vendas?.count ?? 0} aoMudar={setPagina} />
      </Cartao>

      {detalhe && (
        <ModalDetalhe id={detalhe} podeCancelar={podeGerenciar} aoFechar={() => setDetalhe(null)} />
      )}
    </>
  )
}

function ModalDetalhe({
  id, podeCancelar, aoFechar,
}: {
  id: number
  podeCancelar: boolean
  aoFechar: () => void
}) {
  const clienteQuery = useQueryClient()
  const [motivo, setMotivo] = useState('')
  const [confirmando, setConfirmando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const { data: venda, isLoading } = useQuery({
    queryKey: ['venda', id],
    queryFn: () => api.get<Venda>(`/vendas/${id}/`),
  })

  const cancelar = useMutation({
    mutationFn: () => api.post(`/vendas/${id}/cancelar/`, { motivo }),
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['vendas'] })
      clienteQuery.invalidateQueries({ queryKey: ['venda', id] })
      clienteQuery.invalidateQueries({ queryKey: ['dashboard'] })
      clienteQuery.invalidateQueries({ queryKey: ['caixa-atual'] })
      setConfirmando(false)
    },
    onError: (falha) =>
      setErro(falha instanceof ErroApi ? falha.message : 'Não foi possível cancelar.'),
  })

  return (
    <Modal
      aberto
      aoFechar={aoFechar}
      titulo={venda ? `Venda #${venda.numero}` : 'Venda'}
      descricao={venda ? venda.status_display : undefined}
      largura="max-w-2xl"
    >
      {isLoading || !venda ? (
        <Carregando />
      ) : (
        <div className="space-y-4">
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-slate-500">Data</dt>
              <dd className="font-medium">{formatarDataHora(venda.finalizada_em ?? venda.criado_em)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Vendedor</dt>
              <dd className="font-medium">{venda.vendedor_nome}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Cliente</dt>
              <dd className="font-medium">{venda.cliente_nome || '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Lucro</dt>
              <dd className="numerico font-medium text-emerald-700">
                {formatarMoeda(venda.lucro_centavos)}
              </dd>
            </div>
          </dl>

          <div className="rounded-lg border border-slate-200">
            <TabelaEnvolvida>
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th className="text-right">Qtd.</th>
                    <th className="text-right">Unitário</th>
                    <th className="text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {venda.itens.map((item) => (
                    <tr key={item.id}>
                      <td className="text-sm">{item.descricao}</td>
                      <td className="numerico text-right">{item.quantidade}</td>
                      <td className="numerico text-right">
                        {formatarMoeda(item.preco_unitario_centavos)}
                      </td>
                      <td className="numerico text-right font-semibold">
                        {formatarMoeda(item.total_centavos)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TabelaEnvolvida>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Subtotal</span>
                <span className="numerico">{formatarMoeda(venda.subtotal_centavos)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Desconto</span>
                <span className="numerico">− {formatarMoeda(venda.desconto_centavos)}</span>
              </div>
              <div className="flex justify-between border-t border-slate-200 pt-1 text-base font-bold">
                <span>Total</span>
                <span className="numerico">{formatarMoeda(venda.total_centavos)}</span>
              </div>
            </div>

            <div>
              <p className="rotulo">Pagamentos</p>
              <ul className="space-y-1 text-sm">
                {venda.pagamentos.map((pagamento) => (
                  <li key={pagamento.id} className="flex justify-between">
                    <span className="text-slate-600">{pagamento.forma_display}</span>
                    <span className="numerico">
                      {formatarMoeda(pagamento.valor_centavos)}
                      {pagamento.troco_centavos > 0 && (
                        <span className="ml-1 text-xs text-slate-400">
                          (troco {formatarMoeda(pagamento.troco_centavos)})
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {venda.status === 'cancelada' && (
            <Alerta tipo="aviso">
              Venda cancelada em {formatarDataHora(venda.cancelada_em)}.
              {venda.motivo_cancelamento && <> Motivo: {venda.motivo_cancelamento}</>}
            </Alerta>
          )}

          {erro && <Alerta>{erro}</Alerta>}

          {podeCancelar && venda.status !== 'cancelada' && (
            <div className="border-t border-slate-200 pt-3">
              {confirmando ? (
                <div className="space-y-2">
                  <Alerta tipo="aviso">
                    O cancelamento devolve os itens ao estoque, estorna o dinheiro do caixa e
                    cancela o lançamento financeiro.
                  </Alerta>
                  <Campo
                    rotulo="Motivo do cancelamento"
                    value={motivo}
                    onChange={(evento) => setMotivo(evento.target.value)}
                    placeholder="Ex.: cliente desistiu"
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <Botao variante="secundario" className="flex-1" onClick={() => setConfirmando(false)}>
                      Voltar
                    </Botao>
                    <Botao
                      variante="perigo"
                      className="flex-1"
                      carregando={cancelar.isPending}
                      onClick={() => cancelar.mutate()}
                    >
                      Confirmar cancelamento
                    </Botao>
                  </div>
                </div>
              ) : (
                <Botao variante="perigo" icone={<Ban size={15} />} onClick={() => setConfirmando(true)}>
                  Cancelar venda
                </Botao>
              )}
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
