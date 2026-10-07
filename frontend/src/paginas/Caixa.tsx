/** Abertura, movimentação e fechamento do caixa. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownCircle, ArrowUpCircle, Lock, Unlock } from 'lucide-react'
import { useState } from 'react'

import {
  Alerta, Botao, CabecalhoPagina, Campo, Carregando, Cartao, Modal, Selo,
  TabelaEnvolvida, Vazio,
} from '../componentes/ui'
import { ErroApi, api } from '../lib/api'
import { formatarDataHora, formatarMoeda, paraCentavos } from '../lib/formato'
import type { Caixa as TipoCaixa, CaixaAtual, MovimentoCaixa, Pagina } from '../lib/tipos'

interface Conferencia {
  caixa: TipoCaixa
  saldo_atual_centavos: number
  total_vendas: number
  total_vendido_centavos: number
  por_forma_pagamento: {
    forma: string
    forma_display: string
    total_centavos: number
    troco_centavos: number
    quantidade: number
  }[]
  movimentos: MovimentoCaixa[]
}

export function Caixa() {
  const clienteQuery = useQueryClient()
  const [modal, setModal] = useState<'abrir' | 'fechar' | 'sangria' | 'suprimento' | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  const { data: atual, isLoading } = useQuery({
    queryKey: ['caixa-atual'],
    queryFn: () => api.get<CaixaAtual>('/caixas/atual/'),
  })

  const { data: conferencia } = useQuery({
    queryKey: ['conferencia', atual?.caixa?.id],
    queryFn: () => api.get<Conferencia>(`/caixas/${atual!.caixa!.id}/conferencia/`),
    enabled: Boolean(atual?.aberto && atual.caixa),
  })

  const { data: historico } = useQuery({
    queryKey: ['caixas-fechados'],
    queryFn: () => api.get<Pagina<TipoCaixa>>('/caixas/?status=fechado'),
  })

  function aoConcluir() {
    setModal(null)
    setErro(null)
    clienteQuery.invalidateQueries({ queryKey: ['caixa-atual'] })
    clienteQuery.invalidateQueries({ queryKey: ['conferencia'] })
    clienteQuery.invalidateQueries({ queryKey: ['caixas-fechados'] })
    clienteQuery.invalidateQueries({ queryKey: ['dashboard'] })
  }

  function aoFalhar(falha: unknown) {
    setErro(falha instanceof ErroApi ? falha.message : 'Operação não concluída.')
  }

  const abrir = useMutation({
    mutationFn: (centavos: number) =>
      api.post('/caixas/abrir/', { saldo_inicial_centavos: centavos }),
    onSuccess: aoConcluir,
    onError: aoFalhar,
  })

  const fechar = useMutation({
    mutationFn: ({ centavos, observacoes }: { centavos: number; observacoes: string }) =>
      api.post(`/caixas/${atual!.caixa!.id}/fechar/`, {
        saldo_informado_centavos: centavos,
        observacoes,
      }),
    onSuccess: aoConcluir,
    onError: aoFalhar,
  })

  const movimentar = useMutation({
    mutationFn: ({ tipo, centavos, descricao }: { tipo: string; centavos: number; descricao: string }) =>
      api.post(`/caixas/${atual!.caixa!.id}/movimentar/`, {
        tipo,
        valor_centavos: centavos,
        descricao,
      }),
    onSuccess: aoConcluir,
    onError: aoFalhar,
  })

  if (isLoading) return <Carregando />

  return (
    <>
      <CabecalhoPagina
        titulo="Caixa"
        descricao="Controle do dinheiro em espécie. Pix e cartão não entram na gaveta."
        acoes={
          atual?.aberto ? (
            <>
              <Botao variante="secundario" icone={<ArrowUpCircle size={16} />} onClick={() => setModal('suprimento')}>
                Suprimento
              </Botao>
              <Botao variante="secundario" icone={<ArrowDownCircle size={16} />} onClick={() => setModal('sangria')}>
                Sangria
              </Botao>
              <Botao variante="perigo" icone={<Lock size={16} />} onClick={() => setModal('fechar')}>
                Fechar caixa
              </Botao>
            </>
          ) : (
            <Botao icone={<Unlock size={16} />} onClick={() => setModal('abrir')}>
              Abrir caixa
            </Botao>
          )
        }
      />

      {!atual?.aberto ? (
        <Cartao>
          <Vazio
            titulo="Nenhum caixa aberto"
            descricao="Abra o caixa informando o fundo de troco para começar a vender."
            acao={<Botao onClick={() => setModal('abrir')}>Abrir caixa</Botao>}
          />
        </Cartao>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            <div className="cartao p-3 sm:p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Dinheiro na gaveta
              </p>
              <p className="numerico mt-1 text-lg font-bold sm:text-2xl text-emerald-700">
                {formatarMoeda(atual.saldo_atual_centavos ?? 0)}
              </p>
            </div>
            <div className="cartao p-3 sm:p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Total vendido
              </p>
              <p className="numerico mt-1 text-lg font-bold sm:text-2xl text-slate-900">
                {formatarMoeda(conferencia?.total_vendido_centavos ?? 0)}
              </p>
              <p className="text-xs text-slate-500">
                {conferencia?.total_vendas ?? 0} venda(s) neste caixa
              </p>
            </div>
            <div className="cartao p-3 sm:p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Fundo de troco
              </p>
              <p className="numerico mt-1 text-lg font-bold sm:text-2xl text-slate-900">
                {formatarMoeda(atual.caixa?.saldo_inicial_centavos ?? 0)}
              </p>
            </div>
            <div className="cartao p-3 sm:p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Aberto em</p>
              <p className="mt-1 text-sm font-semibold text-slate-900 sm:text-base">
                {formatarDataHora(atual.caixa?.aberto_em)}
              </p>
              <p className="text-xs text-slate-500">por {atual.caixa?.usuario_abertura_nome}</p>
            </div>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Cartao titulo="Recebimentos por forma de pagamento" semCorpo>
              {!conferencia?.por_forma_pagamento.length ? (
                <Vazio titulo="Nenhuma venda registrada ainda" />
              ) : (
                <TabelaEnvolvida>
                  <table className="tabela">
                    <thead>
                      <tr>
                        <th>Forma</th>
                        <th className="text-right">Vendas</th>
                        <th className="text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {conferencia.por_forma_pagamento.map((linha) => (
                        <tr key={linha.forma}>
                          <td>
                            {linha.forma_display}
                            {linha.forma === 'dinheiro' && (
                              <span className="ml-2 text-xs text-slate-400">(na gaveta)</span>
                            )}
                          </td>
                          <td className="numerico text-right">{linha.quantidade}</td>
                          <td className="numerico text-right font-semibold">
                            {formatarMoeda(linha.total_centavos)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TabelaEnvolvida>
              )}
            </Cartao>

            <Cartao titulo="Movimentos do caixa" semCorpo>
              {!conferencia?.movimentos.length ? (
                <Vazio titulo="Sem movimentos" />
              ) : (
                <div className="max-h-80 overflow-y-auto">
                  <TabelaEnvolvida>
                    <table className="tabela">
                      <thead>
                        <tr>
                          <th>Quando</th>
                          <th>Tipo</th>
                          <th className="text-right">Valor</th>
                        </tr>
                      </thead>
                      <tbody>
                        {conferencia.movimentos.map((movimento) => (
                          <tr key={movimento.id}>
                            <td className="whitespace-nowrap text-xs text-slate-500">
                              {formatarDataHora(movimento.criado_em)}
                            </td>
                            <td>
                              <span className="text-sm">{movimento.tipo_display}</span>
                              {movimento.descricao && (
                                <p className="text-xs text-slate-400">{movimento.descricao}</p>
                              )}
                            </td>
                            <td
                              className={`numerico whitespace-nowrap text-right font-semibold ${
                                movimento.valor_com_sinal_centavos < 0 ? 'text-rose-600' : 'text-emerald-700'
                              }`}
                            >
                              {formatarMoeda(movimento.valor_com_sinal_centavos)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </TabelaEnvolvida>
                </div>
              )}
            </Cartao>
          </div>
        </>
      )}

      <Cartao titulo="Caixas fechados" className="mt-4" semCorpo>
        {!historico?.results.length ? (
          <Vazio titulo="Nenhum caixa fechado ainda" />
        ) : (
          <TabelaEnvolvida>
            <table className="tabela">
              <thead>
                <tr>
                  <th>Abertura</th>
                  <th>Fechamento</th>
                  <th>Responsável</th>
                  <th className="text-right">Sistema</th>
                  <th className="text-right">Conferido</th>
                  <th className="text-right">Diferença</th>
                </tr>
              </thead>
              <tbody>
                {historico.results.map((caixa) => (
                  <tr key={caixa.id}>
                    <td className="whitespace-nowrap text-xs">{formatarDataHora(caixa.aberto_em)}</td>
                    <td className="whitespace-nowrap text-xs">{formatarDataHora(caixa.fechado_em)}</td>
                    <td className="text-sm">{caixa.usuario_fechamento_nome || '—'}</td>
                    <td className="numerico text-right">{formatarMoeda(caixa.saldo_calculado_centavos)}</td>
                    <td className="numerico text-right">{formatarMoeda(caixa.saldo_informado_centavos)}</td>
                    <td className="text-right">
                      <Selo
                        cor={
                          caixa.diferenca_centavos === 0
                            ? 'verde'
                            : caixa.diferenca_centavos > 0
                              ? 'azul'
                              : 'vermelho'
                        }
                      >
                        {formatarMoeda(caixa.diferenca_centavos)}
                      </Selo>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TabelaEnvolvida>
        )}
      </Cartao>

      <ModalValor
        aberto={modal === 'abrir'}
        aoFechar={() => setModal(null)}
        titulo="Abrir caixa"
        descricao="Informe o fundo de troco que está na gaveta agora."
        rotulo="Fundo de troco"
        enviando={abrir.isPending}
        erro={erro}
        aoConfirmar={(centavos) => abrir.mutate(centavos)}
      />

      <ModalFechamento
        aberto={modal === 'fechar'}
        aoFechar={() => setModal(null)}
        esperado={atual?.saldo_atual_centavos ?? 0}
        enviando={fechar.isPending}
        erro={erro}
        aoConfirmar={(centavos, observacoes) => fechar.mutate({ centavos, observacoes })}
      />

      <ModalValor
        aberto={modal === 'sangria'}
        aoFechar={() => setModal(null)}
        titulo="Sangria"
        descricao="Retirada de dinheiro do caixa."
        rotulo="Valor retirado"
        comDescricao
        enviando={movimentar.isPending}
        erro={erro}
        aoConfirmar={(centavos, descricao) =>
          movimentar.mutate({ tipo: 'sangria', centavos, descricao: descricao ?? '' })
        }
      />

      <ModalValor
        aberto={modal === 'suprimento'}
        aoFechar={() => setModal(null)}
        titulo="Suprimento"
        descricao="Entrada de dinheiro no caixa (reforço de troco)."
        rotulo="Valor adicionado"
        comDescricao
        enviando={movimentar.isPending}
        erro={erro}
        aoConfirmar={(centavos, descricao) =>
          movimentar.mutate({ tipo: 'suprimento', centavos, descricao: descricao ?? '' })
        }
      />
    </>
  )
}

function ModalValor({
  aberto, aoFechar, titulo, descricao, rotulo, comDescricao = false,
  enviando, erro, aoConfirmar,
}: {
  aberto: boolean
  aoFechar: () => void
  titulo: string
  descricao: string
  rotulo: string
  comDescricao?: boolean
  enviando: boolean
  erro: string | null
  aoConfirmar: (centavos: number, descricao?: string) => void
}) {
  const [valor, setValor] = useState('')
  const [texto, setTexto] = useState('')

  return (
    <Modal aberto={aberto} aoFechar={aoFechar} titulo={titulo} descricao={descricao}>
      <div className="space-y-3">
        <Campo
          rotulo={rotulo}
          value={valor}
          onChange={(evento) => setValor(evento.target.value)}
          placeholder="0,00"
          inputMode="decimal"
          autoFocus
        />
        {comDescricao && (
          <Campo
            rotulo="Descrição"
            value={texto}
            onChange={(evento) => setTexto(evento.target.value)}
            placeholder="Ex.: depósito no banco"
          />
        )}
        {erro && <Alerta>{erro}</Alerta>}
        <div className="flex gap-2">
          <Botao variante="secundario" className="flex-1" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao
            className="flex-1"
            carregando={enviando}
            onClick={() => { aoConfirmar(paraCentavos(valor), texto); setValor(''); setTexto('') }}
          >
            Confirmar
          </Botao>
        </div>
      </div>
    </Modal>
  )
}

function ModalFechamento({
  aberto, aoFechar, esperado, enviando, erro, aoConfirmar,
}: {
  aberto: boolean
  aoFechar: () => void
  esperado: number
  enviando: boolean
  erro: string | null
  aoConfirmar: (centavos: number, observacoes: string) => void
}) {
  const [contado, setContado] = useState('')
  const [observacoes, setObservacoes] = useState('')
  const diferenca = contado ? paraCentavos(contado) - esperado : 0

  return (
    <Modal
      aberto={aberto}
      aoFechar={aoFechar}
      titulo="Fechar caixa"
      descricao="Conte o dinheiro da gaveta e informe o valor encontrado."
    >
      <div className="space-y-3">
        <div className="rounded-lg bg-slate-50 px-3 py-2.5 text-sm">
          <span className="text-slate-600">O sistema calculou: </span>
          <span className="numerico font-bold text-slate-900">{formatarMoeda(esperado)}</span>
        </div>

        <Campo
          rotulo="Dinheiro contado na gaveta"
          value={contado}
          onChange={(evento) => setContado(evento.target.value)}
          placeholder="0,00"
          inputMode="decimal"
          autoFocus
        />

        {contado && diferenca !== 0 && (
          <Alerta tipo={diferenca > 0 ? 'informacao' : 'aviso'}>
            {diferenca > 0
              ? `Sobra de ${formatarMoeda(diferenca)} na gaveta.`
              : `Falta de ${formatarMoeda(Math.abs(diferenca))} na gaveta.`}{' '}
            A diferença fica registrada no fechamento.
          </Alerta>
        )}

        <Campo
          rotulo="Observações"
          value={observacoes}
          onChange={(evento) => setObservacoes(evento.target.value)}
          placeholder="Opcional"
        />

        {erro && <Alerta>{erro}</Alerta>}

        <div className="flex gap-2">
          <Botao variante="secundario" className="flex-1" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao
            variante="perigo"
            className="flex-1"
            carregando={enviando}
            disabled={!contado}
            onClick={() => aoConfirmar(paraCentavos(contado), observacoes)}
          >
            Fechar caixa
          </Botao>
        </div>
      </div>
    </Modal>
  )
}
