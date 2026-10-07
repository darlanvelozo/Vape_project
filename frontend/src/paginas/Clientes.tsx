/** Clientes: cadastro, crédito (fiado) e histórico de compras. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { History, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'

import {
  Alerta, AreaTexto, Botao, BotaoIcone, CabecalhoPagina, Campo, Carregando, Cartao,
  Modal, Paginacao, Selo, TabelaEnvolvida, Vazio,
} from '../componentes/ui'
import { ErroApi, api, querystring } from '../lib/api'
import { formatarData, formatarDataHora, formatarMoeda, formatarTelefone, paraCentavos } from '../lib/formato'
import type { Cliente, Pagina, VendaResumo } from '../lib/tipos'

interface Historico {
  cliente: Cliente
  total_compras: number
  valor_total_centavos: number
  ticket_medio_centavos: number
  saldo_devedor_centavos: number
  ultimas_vendas: VendaResumo[]
}

export function Clientes() {
  const clienteQuery = useQueryClient()
  const [busca, setBusca] = useState('')
  const [modal, setModal] = useState<Cliente | 'novo' | null>(null)
  const [historico, setHistorico] = useState<number | null>(null)
  const [pagina, setPagina] = useState(1)

  const { data: clientes, isLoading } = useQuery({
    queryKey: ['clientes', busca, pagina],
    queryFn: () =>
      api.get<Pagina<Cliente>>(`/clientes/${querystring({ search: busca, page: pagina })}`),
  })

  const excluir = useMutation({
    mutationFn: (id: number) => api.delete(`/clientes/${id}/`),
    onSuccess: () => clienteQuery.invalidateQueries({ queryKey: ['clientes'] }),
  })

  return (
    <>
      <CabecalhoPagina
        titulo="Clientes"
        descricao="Cadastro, limite de fiado e histórico de compras."
        acoes={
          <Botao icone={<Plus size={16} />} onClick={() => setModal('novo')}>
            Novo cliente
          </Botao>
        }
      />

      <Campo
        className="mb-3"
        placeholder="Buscar por nome, telefone ou CPF…"
        value={busca}
        onChange={(evento) => { setBusca(evento.target.value); setPagina(1) }}
      />

      <Cartao semCorpo>
        {isLoading ? (
          <Carregando />
        ) : !clientes?.results.length ? (
          <Vazio
            titulo="Nenhum cliente cadastrado"
            descricao="O cadastro é opcional para vender, mas necessário para fiado e histórico."
            acao={<Botao onClick={() => setModal('novo')}>Novo cliente</Botao>}
          />
        ) : (
          <TabelaEnvolvida>
            <table className="tabela">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Telefone</th>
                  <th>Nascimento</th>
                  <th className="text-right">Limite</th>
                  <th className="text-right">Deve</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {clientes.results.map((cliente) => (
                  <tr key={cliente.id}>
                    <td>
                      <p className="text-sm font-medium text-slate-800">{cliente.nome}</p>
                      {!cliente.ativo && <Selo cor="cinza">inativo</Selo>}
                    </td>
                    <td className="text-sm text-slate-600">{cliente.telefone || '—'}</td>
                    <td className="text-sm text-slate-600">
                      {cliente.data_nascimento ? (
                        <>
                          {formatarData(cliente.data_nascimento)}
                          <span className="ml-1 text-xs text-slate-400">({cliente.idade} anos)</span>
                        </>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="numerico text-right">
                      {formatarMoeda(cliente.limite_credito_centavos)}
                    </td>
                    <td className="text-right">
                      {cliente.saldo_devedor_centavos > 0 ? (
                        <Selo cor="ambar">{formatarMoeda(cliente.saldo_devedor_centavos)}</Selo>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="text-right">
                      <div className="flex justify-end gap-1">
                        <BotaoIcone titulo="Histórico de compras" aoClicar={() => setHistorico(cliente.id)}>
                          <History size={16} />
                        </BotaoIcone>
                        <BotaoIcone titulo="Editar cliente" aoClicar={() => setModal(cliente)}>
                          <Pencil size={16} />
                        </BotaoIcone>
                        <BotaoIcone
                          titulo="Remover cliente"
                          perigo
                          aoClicar={() => {
                            if (confirm(`Remover “${cliente.nome}”? Clientes com histórico são apenas desativados.`)) {
                              excluir.mutate(cliente.id)
                            }
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
        <Paginacao pagina={pagina} total={clientes?.count ?? 0} aoMudar={setPagina} />
      </Cartao>

      {modal && (
        <ModalCliente
          cliente={modal === 'novo' ? null : modal}
          aoFechar={() => setModal(null)}
        />
      )}
      {historico && <ModalHistorico id={historico} aoFechar={() => setHistorico(null)} />}
    </>
  )
}

function ModalCliente({ cliente, aoFechar }: { cliente: Cliente | null; aoFechar: () => void }) {
  const clienteQuery = useQueryClient()
  const [erro, setErro] = useState<ErroApi | null>(null)
  const [dados, setDados] = useState({
    nome: cliente?.nome ?? '',
    telefone: cliente?.telefone ?? '',
    email: cliente?.email ?? '',
    cpf: cliente?.cpf ?? '',
    data_nascimento: cliente?.data_nascimento ?? '',
    endereco: cliente?.endereco ?? '',
    cidade: cliente?.cidade ?? '',
    observacoes: cliente?.observacoes ?? '',
    limite: cliente ? (cliente.limite_credito_centavos / 100).toFixed(2).replace('.', ',') : '',
    ativo: cliente?.ativo ?? true,
  })

  const salvar = useMutation({
    mutationFn: () => {
      const corpo = {
        nome: dados.nome,
        telefone: dados.telefone,
        email: dados.email,
        cpf: dados.cpf,
        data_nascimento: dados.data_nascimento || null,
        endereco: dados.endereco,
        cidade: dados.cidade,
        observacoes: dados.observacoes,
        limite_credito_centavos: paraCentavos(dados.limite),
        ativo: dados.ativo,
      }
      return cliente ? api.patch(`/clientes/${cliente.id}/`, corpo) : api.post('/clientes/', corpo)
    },
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['clientes'] })
      aoFechar()
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha : null),
  })

  return (
    <Modal
      aberto
      aoFechar={aoFechar}
      titulo={cliente ? 'Editar cliente' : 'Novo cliente'}
      largura="max-w-xl"
    >
      <form className="space-y-3" onSubmit={(evento) => { evento.preventDefault(); salvar.mutate() }}>
        <Campo
          rotulo="Nome"
          value={dados.nome}
          onChange={(evento) => setDados({ ...dados, nome: evento.target.value })}
          required
          autoFocus
          erro={erro?.doCampo('nome')}
        />

        <div className="grid gap-3 sm:grid-cols-2">
          <Campo
            rotulo="Telefone"
            value={dados.telefone}
            onChange={(evento) => setDados({ ...dados, telefone: formatarTelefone(evento.target.value) })}
            placeholder="(11) 90000-0000"
          />
          <Campo
            rotulo="E-mail"
            type="email"
            value={dados.email}
            onChange={(evento) => setDados({ ...dados, email: evento.target.value })}
            erro={erro?.doCampo('email')}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Campo
            rotulo="CPF"
            value={dados.cpf}
            onChange={(evento) => setDados({ ...dados, cpf: evento.target.value })}
            placeholder="000.000.000-00"
            erro={erro?.doCampo('cpf')}
          />
          <Campo
            rotulo="Data de nascimento"
            type="date"
            value={dados.data_nascimento}
            onChange={(evento) => setDados({ ...dados, data_nascimento: evento.target.value })}
            erro={erro?.doCampo('data_nascimento')}
            dica="Usada para bloquear venda a menor de idade."
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

        <Campo
          rotulo="Limite de crédito (fiado)"
          value={dados.limite}
          onChange={(evento) => setDados({ ...dados, limite: evento.target.value })}
          placeholder="0,00"
          inputMode="decimal"
          dica="Zero desativa a venda fiada para este cliente."
        />

        <AreaTexto
          rotulo="Observações"
          value={dados.observacoes}
          onChange={(evento) => setDados({ ...dados, observacoes: evento.target.value })}
        />

        {cliente && (
          <label className="flex min-h-[44px] cursor-pointer items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={dados.ativo}
              onChange={(evento) => setDados({ ...dados, ativo: evento.target.checked })}
              className="h-5 w-5 rounded border-slate-300"
            />
            Cliente ativo
          </label>
        )}

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

function ModalHistorico({ id, aoFechar }: { id: number; aoFechar: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ['cliente-historico', id],
    queryFn: () => api.get<Historico>(`/clientes/${id}/historico/`),
  })

  return (
    <Modal
      aberto
      aoFechar={aoFechar}
      titulo={data ? data.cliente.nome : 'Histórico'}
      descricao="Compras e saldo devedor"
      largura="max-w-2xl"
    >
      {isLoading || !data ? (
        <Carregando />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { rotulo: 'Compras', valor: String(data.total_compras) },
              { rotulo: 'Total gasto', valor: formatarMoeda(data.valor_total_centavos) },
              { rotulo: 'Ticket médio', valor: formatarMoeda(data.ticket_medio_centavos) },
              { rotulo: 'Em aberto', valor: formatarMoeda(data.saldo_devedor_centavos) },
            ].map((item) => (
              <div key={item.rotulo} className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">{item.rotulo}</p>
                <p className="numerico mt-0.5 font-bold text-slate-900">{item.valor}</p>
              </div>
            ))}
          </div>

          {data.ultimas_vendas.length === 0 ? (
            <Vazio titulo="Nenhuma compra registrada" />
          ) : (
            <div className="rounded-lg border border-slate-200">
              <TabelaEnvolvida>
                <table className="tabela">
                  <thead>
                    <tr>
                      <th>Nº</th>
                      <th>Data</th>
                      <th className="text-right">Itens</th>
                      <th className="text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.ultimas_vendas.map((venda) => (
                      <tr key={venda.id}>
                        <td className="numerico">#{venda.numero}</td>
                        <td className="text-xs text-slate-500">
                          {formatarDataHora(venda.finalizada_em ?? venda.criado_em)}
                        </td>
                        <td className="numerico text-right">{venda.quantidade_itens}</td>
                        <td className="numerico text-right font-semibold">
                          {formatarMoeda(venda.total_centavos)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TabelaEnvolvida>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
