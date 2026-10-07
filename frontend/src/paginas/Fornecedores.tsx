/** Fornecedores e compras (entrada de mercadoria). */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Ban, Check, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'

import {
  Alerta, AreaTexto, Botao, BotaoIcone, CabecalhoPagina, Campo, Carregando, Cartao,
  Modal, Paginacao, Selecao, Selo, TabelaEnvolvida, Vazio,
} from '../componentes/ui'
import { ErroApi, api, querystring } from '../lib/api'
import { dataISO, formatarData, formatarMoeda, formatarTelefone, paraCentavos } from '../lib/formato'
import type { Compra, Fornecedor, ItemCompra, Pagina, VariacaoResumo } from '../lib/tipos'

export function Fornecedores() {
  const [aba, setAba] = useState<'fornecedores' | 'compras'>('fornecedores')
  const [busca, setBusca] = useState('')
  const [modalFornecedor, setModalFornecedor] = useState<Fornecedor | 'novo' | null>(null)
  const [modalCompra, setModalCompra] = useState<'nova' | null>(null)
  const [pagina, setPagina] = useState(1)
  const clienteQuery = useQueryClient()

  const { data: fornecedores, isLoading } = useQuery({
    queryKey: ['fornecedores', busca, pagina],
    queryFn: () =>
      api.get<Pagina<Fornecedor>>(`/fornecedores/${querystring({ search: busca, page: pagina })}`),
  })

  const { data: compras } = useQuery({
    queryKey: ['compras', pagina],
    queryFn: () => api.get<Pagina<Compra>>(`/compras/?ordering=-data&page=${pagina}`),
    enabled: aba === 'compras',
  })

  const excluir = useMutation({
    mutationFn: (id: number) => api.delete(`/fornecedores/${id}/`),
    onSuccess: () => clienteQuery.invalidateQueries({ queryKey: ['fornecedores'] }),
  })

  const receber = useMutation({
    mutationFn: (id: number) => api.post(`/compras/${id}/receber/`, {}),
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['compras'] })
      clienteQuery.invalidateQueries({ queryKey: ['estoque-posicao'] })
      clienteQuery.invalidateQueries({ queryKey: ['estoque-resumo'] })
    },
  })

  const cancelarCompra = useMutation({
    mutationFn: (id: number) => api.post(`/compras/${id}/cancelar/`, { motivo: 'Cancelada pelo usuário' }),
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['compras'] })
      clienteQuery.invalidateQueries({ queryKey: ['estoque-posicao'] })
    },
  })

  return (
    <>
      <CabecalhoPagina
        titulo="Fornecedores e compras"
        descricao="Quem abastece a loja e as entradas de mercadoria."
        acoes={
          aba === 'fornecedores' ? (
            <Botao icone={<Plus size={16} />} onClick={() => setModalFornecedor('novo')}>
              Novo fornecedor
            </Botao>
          ) : (
            <Botao icone={<Plus size={16} />} onClick={() => setModalCompra('nova')}>
              Nova compra
            </Botao>
          )
        }
      />

      <div className="mb-4 flex gap-1 border-b border-slate-200">
        {(['fornecedores', 'compras'] as const).map((valor) => (
          <button
            key={valor}
            onClick={() => { setAba(valor); setPagina(1) }}
            className={`min-h-[44px] px-4 text-sm font-medium capitalize transition ${
              aba === valor
                ? 'border-b-2 border-marca-700 text-marca-800'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {valor}
          </button>
        ))}
      </div>

      {aba === 'fornecedores' ? (
        <>
          <Campo
            className="mb-3"
            placeholder="Buscar fornecedor…"
            value={busca}
            onChange={(evento) => { setBusca(evento.target.value); setPagina(1) }}
          />
          <Cartao semCorpo>
            {isLoading ? (
              <Carregando />
            ) : !fornecedores?.results.length ? (
              <Vazio
                titulo="Nenhum fornecedor cadastrado"
                acao={<Botao onClick={() => setModalFornecedor('novo')}>Novo fornecedor</Botao>}
              />
            ) : (
              <TabelaEnvolvida>
                <table className="tabela">
                  <thead>
                    <tr>
                      <th>Nome</th>
                      <th>Contato</th>
                      <th>Telefone</th>
                      <th>Cidade</th>
                      <th className="text-right">Compras</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {fornecedores.results.map((fornecedor) => (
                      <tr key={fornecedor.id}>
                        <td>
                          <p className="text-sm font-medium text-slate-800">{fornecedor.nome}</p>
                          {!fornecedor.ativo && <Selo cor="cinza">inativo</Selo>}
                        </td>
                        <td className="text-sm text-slate-600">{fornecedor.contato || '—'}</td>
                        <td className="text-sm text-slate-600">{fornecedor.telefone || '—'}</td>
                        <td className="text-sm text-slate-600">{fornecedor.cidade || '—'}</td>
                        <td className="numerico text-right">{fornecedor.total_compras}</td>
                        <td className="text-right">
                          <div className="flex justify-end gap-1">
                            <BotaoIcone
                              titulo="Editar fornecedor"
                              aoClicar={() => setModalFornecedor(fornecedor)}
                            >
                              <Pencil size={16} />
                            </BotaoIcone>
                            <BotaoIcone
                              titulo="Remover fornecedor"
                              perigo
                              aoClicar={() => {
                                if (confirm(`Remover “${fornecedor.nome}”?`)) excluir.mutate(fornecedor.id)
                              }}
                            >
                              <Trash2 size={16} />
                            </BotaoIcone>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TabelaEnvolvida>
            )}
            <Paginacao pagina={pagina} total={fornecedores?.count ?? 0} aoMudar={setPagina} />
          </Cartao>
        </>
      ) : (
        <Cartao semCorpo>
          {!compras?.results.length ? (
            <Vazio
              titulo="Nenhuma compra registrada"
              descricao="Registre a compra como rascunho e receba-a quando a mercadoria chegar — a entrada no estoque acontece no recebimento."
              acao={<Botao onClick={() => setModalCompra('nova')}>Nova compra</Botao>}
            />
          ) : (
            <TabelaEnvolvida>
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Nº</th>
                    <th>Fornecedor</th>
                    <th>Data</th>
                    <th>Documento</th>
                    <th className="text-right">Itens</th>
                    <th className="text-right">Total</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {compras.results.map((compra) => (
                    <tr key={compra.id}>
                      <td className="numerico">#{compra.id}</td>
                      <td className="text-sm font-medium">{compra.fornecedor_nome}</td>
                      <td className="text-sm">{formatarData(compra.data)}</td>
                      <td className="text-xs text-slate-500">{compra.numero_documento || '—'}</td>
                      <td className="numerico text-right">{compra.itens.length}</td>
                      <td className="numerico text-right font-semibold">
                        {formatarMoeda(compra.total_centavos)}
                      </td>
                      <td>
                        <Selo
                          cor={
                            compra.status === 'recebida'
                              ? 'verde'
                              : compra.status === 'cancelada'
                                ? 'vermelho'
                                : 'ambar'
                          }
                        >
                          {compra.status_display}
                        </Selo>
                      </td>
                      <td className="text-right">
                        <div className="flex justify-end gap-1">
                          {compra.status === 'rascunho' && (
                            <BotaoIcone
                              titulo="Receber (dar entrada no estoque)"
                              aoClicar={() => {
                                if (confirm('Receber a compra? Isso dá entrada no estoque e atualiza o custo médio.')) {
                                  receber.mutate(compra.id)
                                }
                              }}
                            >
                              <Check size={16} />
                            </BotaoIcone>
                          )}
                          {compra.status !== 'cancelada' && (
                            <BotaoIcone
                              titulo="Cancelar compra"
                              perigo
                              aoClicar={() => {
                                if (confirm('Cancelar a compra? Se já recebida, o estoque é estornado.')) {
                                  cancelarCompra.mutate(compra.id)
                                }
                              }}
                            >
                              <Ban size={16} />
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
          <Paginacao pagina={pagina} total={compras?.count ?? 0} aoMudar={setPagina} />
        </Cartao>
      )}

      {modalFornecedor && (
        <ModalFornecedor
          fornecedor={modalFornecedor === 'novo' ? null : modalFornecedor}
          aoFechar={() => setModalFornecedor(null)}
        />
      )}
      {modalCompra && (
        <ModalCompra
          fornecedores={fornecedores?.results ?? []}
          aoFechar={() => setModalCompra(null)}
        />
      )}
    </>
  )
}

function ModalFornecedor({
  fornecedor, aoFechar,
}: {
  fornecedor: Fornecedor | null
  aoFechar: () => void
}) {
  const clienteQuery = useQueryClient()
  const [erro, setErro] = useState<ErroApi | null>(null)
  const [dados, setDados] = useState({
    nome: fornecedor?.nome ?? '',
    cnpj: fornecedor?.cnpj ?? '',
    contato: fornecedor?.contato ?? '',
    telefone: fornecedor?.telefone ?? '',
    email: fornecedor?.email ?? '',
    endereco: fornecedor?.endereco ?? '',
    cidade: fornecedor?.cidade ?? '',
    observacoes: fornecedor?.observacoes ?? '',
    ativo: fornecedor?.ativo ?? true,
  })

  const salvar = useMutation({
    mutationFn: () =>
      fornecedor
        ? api.patch(`/fornecedores/${fornecedor.id}/`, dados)
        : api.post('/fornecedores/', dados),
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['fornecedores'] })
      aoFechar()
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha : null),
  })

  return (
    <Modal
      aberto
      aoFechar={aoFechar}
      titulo={fornecedor ? 'Editar fornecedor' : 'Novo fornecedor'}
      largura="max-w-xl"
    >
      <form className="space-y-3" onSubmit={(evento) => { evento.preventDefault(); salvar.mutate() }}>
        <Campo
          rotulo="Nome / razão social"
          value={dados.nome}
          onChange={(evento) => setDados({ ...dados, nome: evento.target.value })}
          required
          autoFocus
          erro={erro?.doCampo('nome')}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <Campo
            rotulo="CNPJ"
            value={dados.cnpj}
            onChange={(evento) => setDados({ ...dados, cnpj: evento.target.value })}
            placeholder="00.000.000/0001-00"
            erro={erro?.doCampo('cnpj')}
          />
          <Campo
            rotulo="Pessoa de contato"
            value={dados.contato}
            onChange={(evento) => setDados({ ...dados, contato: evento.target.value })}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Campo
            rotulo="Telefone"
            value={dados.telefone}
            onChange={(evento) => setDados({ ...dados, telefone: formatarTelefone(evento.target.value) })}
          />
          <Campo
            rotulo="E-mail"
            type="email"
            value={dados.email}
            onChange={(evento) => setDados({ ...dados, email: evento.target.value })}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-[2fr_1fr]">
          <Campo
            rotulo="Endereço"
            value={dados.endereco}
            onChange={(evento) => setDados({ ...dados, endereco: evento.target.value })}
          />
          <Campo
            rotulo="Cidade"
            value={dados.cidade}
            onChange={(evento) => setDados({ ...dados, cidade: evento.target.value })}
          />
        </div>
        <AreaTexto
          rotulo="Observações"
          value={dados.observacoes}
          onChange={(evento) => setDados({ ...dados, observacoes: evento.target.value })}
        />
        {erro && <Alerta>{erro.message}</Alerta>}
        <div className="acoes-modal flex gap-2 pt-1">
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

function ModalCompra({
  fornecedores, aoFechar,
}: {
  fornecedores: Fornecedor[]
  aoFechar: () => void
}) {
  const clienteQuery = useQueryClient()
  const [erro, setErro] = useState<string | null>(null)
  const [fornecedor, setFornecedor] = useState('')
  const [data, setData] = useState(dataISO(new Date()))
  const [documento, setDocumento] = useState('')
  const [vencimento, setVencimento] = useState('')
  const [frete, setFrete] = useState('')
  const [itens, setItens] = useState<(ItemCompra & { descricao: string })[]>([])
  const [termo, setTermo] = useState('')

  const { data: opcoes = [] } = useQuery({
    queryKey: ['busca-variacao-compra', termo],
    queryFn: () => api.get<VariacaoResumo[]>(`/variacoes/busca-pdv/?q=${encodeURIComponent(termo)}`),
  })

  const total =
    itens.reduce((soma, item) => soma + item.quantidade * item.custo_unitario_centavos, 0) +
    paraCentavos(frete)

  const salvar = useMutation({
    mutationFn: () =>
      api.post('/compras/', {
        fornecedor: Number(fornecedor),
        data,
        numero_documento: documento,
        vencimento: vencimento || null,
        frete_centavos: paraCentavos(frete),
        itens: itens.map((item) => ({
          variacao: item.variacao,
          quantidade: item.quantidade,
          custo_unitario_centavos: item.custo_unitario_centavos,
        })),
      }),
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['compras'] })
      aoFechar()
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha.message : 'Falha ao salvar.'),
  })

  return (
    <Modal
      aberto
      aoFechar={aoFechar}
      titulo="Nova compra"
      descricao="A compra nasce como rascunho; o estoque só entra no recebimento."
      largura="max-w-2xl"
    >
      <form className="space-y-3" onSubmit={(evento) => { evento.preventDefault(); salvar.mutate() }}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Selecao
            rotulo="Fornecedor"
            value={fornecedor}
            onChange={(evento) => setFornecedor(evento.target.value)}
            required
          >
            <option value="">Selecione…</option>
            {fornecedores.map((item) => (
              <option key={item.id} value={item.id}>{item.nome}</option>
            ))}
          </Selecao>
          <Campo
            rotulo="Data da compra"
            type="date"
            value={data}
            onChange={(evento) => setData(evento.target.value)}
            required
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <Campo
            rotulo="Documento / nota"
            value={documento}
            onChange={(evento) => setDocumento(evento.target.value)}
          />
          <Campo
            rotulo="Vencimento"
            type="date"
            value={vencimento}
            onChange={(evento) => setVencimento(evento.target.value)}
            dica="Gera conta a pagar."
          />
          <Campo
            rotulo="Frete"
            value={frete}
            onChange={(evento) => setFrete(evento.target.value)}
            placeholder="0,00"
            inputMode="decimal"
          />
        </div>

        <fieldset className="rounded-lg border border-slate-200 p-3">
          <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Itens
          </legend>

          <Campo
            placeholder="Buscar produto para adicionar…"
            value={termo}
            onChange={(evento) => setTermo(evento.target.value)}
          />

          {termo && (
            <ul className="mt-2 max-h-36 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
              {opcoes.map((variacao) => (
                <li key={variacao.id}>
                  <button
                    type="button"
                    onClick={() => {
                      if (itens.some((item) => item.variacao === variacao.id)) return
                      setItens([
                        ...itens,
                        {
                          variacao: variacao.id,
                          descricao: variacao.descricao_completa,
                          quantidade: 1,
                          custo_unitario_centavos: 0,
                        },
                      ])
                      setTermo('')
                    }}
                    className="w-full px-3 py-2 text-left text-sm transition hover:bg-slate-50"
                  >
                    {variacao.descricao_completa}
                  </button>
                </li>
              ))}
            </ul>
          )}

          {itens.length > 0 && (
            <ul className="mt-3 space-y-2">
              {itens.map((item, indice) => (
                <li key={item.variacao} className="flex flex-wrap items-center gap-2">
                  <span className="min-w-0 flex-1 truncate text-sm">{item.descricao}</span>
                  <input
                    value={item.quantidade}
                    onChange={(evento) => {
                      const copia = [...itens]
                      copia[indice].quantidade = Math.max(Number(evento.target.value) || 0, 0)
                      setItens(copia)
                    }}
                    className="numerico w-16 rounded border border-slate-300 px-2 py-1 text-right text-sm"
                    inputMode="numeric"
                    aria-label="Quantidade"
                  />
                  <input
                    value={(item.custo_unitario_centavos / 100).toFixed(2).replace('.', ',')}
                    onChange={(evento) => {
                      const copia = [...itens]
                      copia[indice].custo_unitario_centavos = paraCentavos(evento.target.value)
                      setItens(copia)
                    }}
                    className="numerico w-24 rounded border border-slate-300 px-2 py-1 text-right text-sm"
                    inputMode="decimal"
                    aria-label="Custo unitário"
                  />
                  <button
                    type="button"
                    onClick={() => setItens(itens.filter((_, i) => i !== indice))}
                    className="text-slate-300 hover:text-rose-600"
                  >
                    <Trash2 size={15} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </fieldset>

        <div className="flex justify-between rounded-lg bg-slate-50 px-3 py-2.5 text-sm font-bold">
          <span>Total da compra</span>
          <span className="numerico">{formatarMoeda(total)}</span>
        </div>

        {erro && <Alerta>{erro}</Alerta>}

        <div className="acoes-modal flex gap-2 pt-1">
          <Botao type="button" variante="secundario" className="flex-1" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao
            type="submit"
            className="flex-1"
            carregando={salvar.isPending}
            disabled={!fornecedor || itens.length === 0}
          >
            Salvar rascunho
          </Botao>
        </div>
      </form>
    </Modal>
  )
}
