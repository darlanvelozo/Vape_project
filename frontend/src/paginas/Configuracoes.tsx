/** Dados da loja, preferências de operação e equipe. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, RotateCcw, Trash2 } from 'lucide-react'
import { useState } from 'react'

import {
  Alerta, Botao, BotaoIcone, CabecalhoPagina, Campo, Carregando, Cartao, Modal,
  Selecao, Selo, TabelaEnvolvida,
} from '../componentes/ui'
import { ErroApi, api } from '../lib/api'
import { useAutenticacao } from '../lib/auth'
import { formatarData, formatarTelefone } from '../lib/formato'
import type { ConfiguracaoLoja, Loja, Pagina, Papel, UsuarioEquipe } from '../lib/tipos'

const PAPEIS: { valor: Papel; rotulo: string; descricao: string }[] = [
  { valor: 'dono', rotulo: 'Dono', descricao: 'Acesso total, inclusive financeiro e equipe.' },
  { valor: 'gerente', rotulo: 'Gerente', descricao: 'Tudo menos gerenciar o dono da loja.' },
  { valor: 'vendedor', rotulo: 'Vendedor', descricao: 'PDV, caixa e clientes. Sem financeiro.' },
]

export function Configuracoes() {
  const { usuario, podeGerenciar, atualizarUsuario } = useAutenticacao()
  const [aba, setAba] = useState<'loja' | 'operacao' | 'vitrine' | 'equipe' | 'conta'>('loja')

  const abas = [
    { chave: 'loja' as const, rotulo: 'Dados da loja' },
    { chave: 'operacao' as const, rotulo: 'Operação' },
    { chave: 'vitrine' as const, rotulo: 'Vitrine pública' },
    ...(podeGerenciar ? [{ chave: 'equipe' as const, rotulo: 'Equipe' }] : []),
    { chave: 'conta' as const, rotulo: 'Minha conta' },
  ]

  return (
    <>
      <CabecalhoPagina titulo="Configurações" descricao={usuario?.loja.nome} />

      {/* No celular as abas quebram em duas linhas: com rolagem lateral,
          "Equipe" e "Minha conta" (onde se troca a senha) ficavam escondidas. */}
      <div className="mb-4 flex flex-wrap gap-x-1 border-b border-slate-200 sm:flex-nowrap sm:overflow-x-auto">
        {abas.map((item) => (
          <button
            key={item.chave}
            onClick={() => setAba(item.chave)}
            className={`min-h-[44px] whitespace-nowrap px-3 text-sm font-medium transition sm:px-4 ${
              aba === item.chave
                ? 'border-b-2 border-marca-700 text-marca-800'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {item.rotulo}
          </button>
        ))}
      </div>

      {aba === 'loja' && <DadosDaLoja podeEditar={podeGerenciar} />}
      {aba === 'operacao' && <Operacao podeEditar={podeGerenciar} />}
      {aba === 'vitrine' && <VitrinePublica podeEditar={podeGerenciar} slug={usuario?.loja.slug ?? ''} />}
      {aba === 'equipe' && podeGerenciar && <Equipe />}
      {aba === 'conta' && <MinhaConta aoAtualizar={atualizarUsuario} />}
    </>
  )
}

function DadosDaLoja({ podeEditar }: { podeEditar: boolean }) {
  const clienteQuery = useQueryClient()
  const [erro, setErro] = useState<ErroApi | null>(null)
  const [salvo, setSalvo] = useState(false)

  const { data: loja, isLoading } = useQuery({
    queryKey: ['minha-loja'],
    queryFn: () => api.get<Loja>('/loja/'),
  })

  const [dados, setDados] = useState<Partial<Loja> | null>(null)
  const atual = dados ?? loja

  const salvar = useMutation({
    mutationFn: () =>
      api.patch<Loja>('/loja/', {
        nome: atual?.nome,
        cnpj: atual?.cnpj,
        telefone: atual?.telefone,
        email: atual?.email,
        endereco: atual?.endereco,
        cidade: atual?.cidade,
        uf: atual?.uf,
        cep: atual?.cep,
      }),
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['minha-loja'] })
      setSalvo(true)
      setTimeout(() => setSalvo(false), 3000)
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha : null),
  })

  if (isLoading || !atual) return <Carregando />

  function alterar(campo: keyof Loja, valor: string) {
    setDados({ ...(atual as Loja), [campo]: valor })
  }

  return (
    <Cartao titulo="Dados cadastrais">
      <form
        className="space-y-3"
        onSubmit={(evento) => { evento.preventDefault(); salvar.mutate() }}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <Campo
            rotulo="Nome da loja"
            value={atual.nome ?? ''}
            onChange={(evento) => alterar('nome', evento.target.value)}
            disabled={!podeEditar}
            erro={erro?.doCampo('nome')}
          />
          <Campo
            rotulo="CNPJ"
            value={atual.cnpj ?? ''}
            onChange={(evento) => alterar('cnpj', evento.target.value)}
            disabled={!podeEditar}
            erro={erro?.doCampo('cnpj')}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Campo
            rotulo="Telefone"
            value={atual.telefone ?? ''}
            onChange={(evento) => alterar('telefone', formatarTelefone(evento.target.value))}
            disabled={!podeEditar}
          />
          <Campo
            rotulo="E-mail"
            type="email"
            value={atual.email ?? ''}
            onChange={(evento) => alterar('email', evento.target.value)}
            disabled={!podeEditar}
          />
        </div>

        <Campo
          rotulo="Endereço"
          value={atual.endereco ?? ''}
          onChange={(evento) => alterar('endereco', evento.target.value)}
          disabled={!podeEditar}
        />

        <div className="grid gap-3 sm:grid-cols-3">
          <Campo
            rotulo="Cidade"
            value={atual.cidade ?? ''}
            onChange={(evento) => alterar('cidade', evento.target.value)}
            disabled={!podeEditar}
          />
          <Campo
            rotulo="UF"
            maxLength={2}
            value={atual.uf ?? ''}
            onChange={(evento) => alterar('uf', evento.target.value.toUpperCase())}
            disabled={!podeEditar}
          />
          <Campo
            rotulo="CEP"
            value={atual.cep ?? ''}
            onChange={(evento) => alterar('cep', evento.target.value)}
            disabled={!podeEditar}
          />
        </div>

        {erro && <Alerta>{erro.message}</Alerta>}
        {salvo && <Alerta tipo="sucesso">Dados da loja atualizados.</Alerta>}

        {podeEditar && (
          <Botao type="submit" carregando={salvar.isPending}>
            Salvar alterações
          </Botao>
        )}
      </form>
    </Cartao>
  )
}

function Operacao({ podeEditar }: { podeEditar: boolean }) {
  const clienteQuery = useQueryClient()
  const [salvo, setSalvo] = useState(false)

  const { data: configuracao, isLoading } = useQuery({
    queryKey: ['configuracao-loja'],
    queryFn: () => api.get<ConfiguracaoLoja>('/loja/configuracao/'),
  })

  const salvar = useMutation({
    mutationFn: (mudanca: Partial<ConfiguracaoLoja>) =>
      api.patch<ConfiguracaoLoja>('/loja/configuracao/', mudanca),
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['configuracao-loja'] })
      setSalvo(true)
      setTimeout(() => setSalvo(false), 2500)
    },
  })

  if (isLoading || !configuracao) return <Carregando />

  const opcoes: { campo: keyof ConfiguracaoLoja; rotulo: string; descricao: string }[] = [
    {
      campo: 'exigir_cliente_na_venda',
      rotulo: 'Exigir cliente em toda venda',
      descricao: 'Bloqueia a venda anônima de balcão. Útil para quem trabalha só com cadastro.',
    },
    {
      campo: 'permitir_venda_sem_estoque',
      rotulo: 'Permitir vender sem estoque',
      descricao: 'Deixa o saldo ficar negativo. Só marque se a loja trabalha com pré-venda.',
    },
    {
      campo: 'permitir_fiado',
      rotulo: 'Permitir venda fiada',
      descricao: 'Habilita a forma de pagamento “fiado”, respeitando o limite de cada cliente.',
    },
    {
      campo: 'alerta_estoque_minimo',
      rotulo: 'Alertar estoque mínimo',
      descricao: 'Destaca no painel os itens que chegaram ao mínimo configurado.',
    },
  ]

  return (
    <div className="space-y-4">
      <Cartao titulo="Regras de operação">
        <ul className="divide-y divide-slate-100">
          {opcoes.map((opcao) => (
            <li key={opcao.campo} className="flex items-start justify-between gap-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-800">{opcao.rotulo}</p>
                <p className="mt-0.5 text-xs text-slate-500">{opcao.descricao}</p>
              </div>
              <label className="relative inline-flex shrink-0 cursor-pointer items-center py-2.5">
                <input
                  type="checkbox"
                  className="peer sr-only"
                  disabled={!podeEditar}
                  checked={Boolean(configuracao[opcao.campo])}
                  onChange={(evento) => salvar.mutate({ [opcao.campo]: evento.target.checked })}
                />
                <div className="h-6 w-11 rounded-full bg-slate-300 transition peer-checked:bg-marca-700 peer-disabled:opacity-50 after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition peer-checked:after:translate-x-5" />
              </label>
            </li>
          ))}
        </ul>
      </Cartao>

      <Cartao titulo="Crediário">
        <Campo
          rotulo="Prazo padrão do fiado (dias)"
          type="number"
          min={0}
          defaultValue={configuracao.prazo_fiado_dias}
          disabled={!podeEditar}
          onBlur={(evento) => {
            const valor = Number(evento.target.value)
            if (valor !== configuracao.prazo_fiado_dias && valor >= 0) {
              salvar.mutate({ prazo_fiado_dias: valor })
            }
          }}
          dica="Prazo de vencimento da venda fiada. Zero faz vencer no mesmo dia."
        />
      </Cartao>

      <Cartao titulo="Recibo">
        <Campo
          rotulo="Mensagem do rodapé"
          defaultValue={configuracao.mensagem_recibo}
          disabled={!podeEditar}
          onBlur={(evento) => {
            if (evento.target.value !== configuracao.mensagem_recibo) {
              salvar.mutate({ mensagem_recibo: evento.target.value })
            }
          }}
          dica="Aparece no comprovante. O aviso “documento sem valor fiscal” é sempre impresso."
        />
      </Cartao>

      {salvo && <Alerta tipo="sucesso">Configuração salva.</Alerta>}
    </div>
  )
}

function VitrinePublica({ podeEditar, slug }: { podeEditar: boolean; slug: string }) {
  const clienteQuery = useQueryClient()
  const [copiado, setCopiado] = useState(false)

  const { data: configuracao, isLoading } = useQuery({
    queryKey: ['configuracao-loja'],
    queryFn: () => api.get<ConfiguracaoLoja>('/loja/configuracao/'),
  })

  const salvar = useMutation({
    mutationFn: (mudanca: Partial<ConfiguracaoLoja>) =>
      api.patch<ConfiguracaoLoja>('/loja/configuracao/', mudanca),
    onSuccess: () => clienteQuery.invalidateQueries({ queryKey: ['configuracao-loja'] }),
  })

  if (isLoading || !configuracao) return <Carregando />

  const endereco = `${window.location.origin}/vitrine/${slug}`

  async function copiar() {
    try {
      await navigator.clipboard.writeText(endereco)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2500)
    } catch {
      // Sem permissão de área de transferência (comum em HTTP ou navegador
      // antigo): o link continua visível e selecionável na tela.
      setCopiado(false)
    }
  }

  return (
    <div className="space-y-4">
      <Cartao titulo="Página pública de catálogo">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-800">Vitrine ativa</p>
            <p className="mt-0.5 text-xs text-slate-500">
              Publica um link sem senha com o que está disponível em estoque. Itens
              esgotados somem sozinhos; custo, margem e quantidade exata nunca aparecem.
            </p>
          </div>
          <label className="relative inline-flex shrink-0 cursor-pointer items-center">
            <input
              type="checkbox"
              className="peer sr-only"
              disabled={!podeEditar}
              checked={configuracao.vitrine_publica}
              onChange={(evento) => salvar.mutate({ vitrine_publica: evento.target.checked })}
            />
            <div className="h-6 w-11 rounded-full bg-slate-300 transition peer-checked:bg-marca-700 peer-disabled:opacity-50 after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:transition peer-checked:after:translate-x-5" />
          </label>
        </div>

        {configuracao.vitrine_publica && (
          <div className="mt-4 rounded-lg border border-marca-200 bg-marca-50 p-3">
            <p className="rotulo">Link para enviar aos clientes</p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                readOnly
                value={endereco}
                onFocus={(evento) => evento.target.select()}
                className="campo flex-1 bg-white text-xs sm:text-sm"
              />
              <div className="flex gap-2">
                <Botao variante="secundario" onClick={copiar} className="flex-1 sm:flex-none">
                  {copiado ? 'Copiado!' : 'Copiar'}
                </Botao>
                <a href={endereco} target="_blank" rel="noopener noreferrer" className="flex-1 sm:flex-none">
                  <Botao variante="secundario" className="w-full">Abrir</Botao>
                </a>
              </div>
            </div>
          </div>
        )}
      </Cartao>

      {configuracao.vitrine_publica && (
        <>
          <Cartao titulo="O que aparece">
            <div className="space-y-3">
              <label className="flex cursor-pointer items-start justify-between gap-4 py-2">
                <span>
                  <span className="block text-sm font-medium text-slate-800">Mostrar preços</span>
                  <span className="mt-0.5 block text-xs text-slate-500">
                    Desligado, a vitrine lista só os modelos e sabores disponíveis.
                  </span>
                </span>
                <input
                  type="checkbox"
                  disabled={!podeEditar}
                  checked={configuracao.vitrine_mostrar_preco}
                  onChange={(evento) => salvar.mutate({ vitrine_mostrar_preco: evento.target.checked })}
                  className="mt-1 h-5 w-5 shrink-0 rounded border-slate-300"
                />
              </label>

              <Campo
                rotulo="Mensagem do topo"
                defaultValue={configuracao.vitrine_mensagem}
                disabled={!podeEditar}
                onBlur={(evento) => {
                  if (evento.target.value !== configuracao.vitrine_mensagem) {
                    salvar.mutate({ vitrine_mensagem: evento.target.value })
                  }
                }}
                placeholder="Chame no WhatsApp para reservar."
              />

              <Campo
                rotulo="WhatsApp de contato"
                defaultValue={configuracao.vitrine_whatsapp}
                disabled={!podeEditar}
                onBlur={(evento) => {
                  const numero = evento.target.value.replace(/\D/g, '')
                  if (numero !== configuracao.vitrine_whatsapp) {
                    salvar.mutate({ vitrine_whatsapp: numero })
                  }
                }}
                placeholder="11999998888"
                dica="DDD + número. Vazio esconde o botão de contato na vitrine."
              />
            </div>
          </Cartao>

          <Alerta tipo="aviso">
            A vitrine é um catálogo informativo, sem venda on-line, e traz o aviso de
            idade mínima. Ela não é indexada por buscadores, mas o link é público:
            quem tiver o endereço consegue abrir.
          </Alerta>
        </>
      )}
    </div>
  )
}

function Equipe() {
  const clienteQuery = useQueryClient()
  const [modal, setModal] = useState<UsuarioEquipe | 'novo' | null>(null)

  const { data: equipe, isLoading } = useQuery({
    queryKey: ['equipe'],
    queryFn: () => api.get<Pagina<UsuarioEquipe>>('/usuarios/'),
  })

  const desativar = useMutation({
    mutationFn: (id: number) => api.delete(`/usuarios/${id}/`),
    onSuccess: () => clienteQuery.invalidateQueries({ queryKey: ['equipe'] }),
  })

  const reativar = useMutation({
    mutationFn: (id: number) => api.post(`/usuarios/${id}/reativar/`, {}),
    onSuccess: () => clienteQuery.invalidateQueries({ queryKey: ['equipe'] }),
  })

  return (
    <>
      <Cartao
        titulo="Usuários da loja"
        acao={
          <Botao tamanho="pequeno" icone={<Plus size={14} />} onClick={() => setModal('novo')}>
            Novo usuário
          </Botao>
        }
        semCorpo
      >
        {isLoading ? (
          <Carregando />
        ) : (
          <TabelaEnvolvida>
            <table className="tabela">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>E-mail</th>
                  <th>Papel</th>
                  <th>Desde</th>
                  <th>Situação</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {equipe?.results.map((membro) => (
                  <tr key={membro.id}>
                    <td className="text-sm font-medium">{membro.nome}</td>
                    <td className="text-sm text-slate-600">{membro.email}</td>
                    <td className="text-sm capitalize">{membro.papel}</td>
                    <td className="text-xs text-slate-500">{formatarData(membro.date_joined)}</td>
                    <td>
                      <Selo cor={membro.is_active ? 'verde' : 'cinza'}>
                        {membro.is_active ? 'ativo' : 'inativo'}
                      </Selo>
                    </td>
                    <td className="text-right">
                      {membro.is_active ? (
                        <BotaoIcone
                          titulo="Desativar acesso"
                          perigo
                          aoClicar={() => {
                            if (confirm(`Desativar o acesso de ${membro.nome}?`)) {
                              desativar.mutate(membro.id)
                            }
                          }}
                        >
                          <Trash2 size={16} />
                        </BotaoIcone>
                      ) : (
                        <BotaoIcone titulo="Reativar acesso" aoClicar={() => reativar.mutate(membro.id)}>
                          <RotateCcw size={16} />
                        </BotaoIcone>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TabelaEnvolvida>
        )}
      </Cartao>

      {modal && (
        <ModalUsuario
          usuario={modal === 'novo' ? null : modal}
          aoFechar={() => setModal(null)}
        />
      )}
    </>
  )
}

function ModalUsuario({
  usuario, aoFechar,
}: {
  usuario: UsuarioEquipe | null
  aoFechar: () => void
}) {
  const clienteQuery = useQueryClient()
  const [erro, setErro] = useState<ErroApi | null>(null)
  const [dados, setDados] = useState({
    nome: usuario?.nome ?? '',
    email: usuario?.email ?? '',
    papel: usuario?.papel ?? ('vendedor' as Papel),
    telefone: usuario?.telefone ?? '',
    senha: '',
  })

  const salvar = useMutation({
    mutationFn: () => {
      const corpo: Record<string, unknown> = {
        nome: dados.nome,
        email: dados.email,
        papel: dados.papel,
        telefone: dados.telefone,
      }
      if (dados.senha) corpo.senha = dados.senha
      return usuario ? api.patch(`/usuarios/${usuario.id}/`, corpo) : api.post('/usuarios/', corpo)
    },
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['equipe'] })
      aoFechar()
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha : null),
  })

  return (
    <Modal aberto aoFechar={aoFechar} titulo={usuario ? 'Editar usuário' : 'Novo usuário'}>
      <form className="space-y-3" onSubmit={(evento) => { evento.preventDefault(); salvar.mutate() }}>
        <Campo
          rotulo="Nome"
          value={dados.nome}
          onChange={(evento) => setDados({ ...dados, nome: evento.target.value })}
          required
          autoFocus
          erro={erro?.doCampo('nome')}
        />
        <Campo
          rotulo="E-mail"
          type="email"
          value={dados.email}
          onChange={(evento) => setDados({ ...dados, email: evento.target.value })}
          required
          erro={erro?.doCampo('email')}
        />
        <Campo
          rotulo="Telefone"
          value={dados.telefone}
          onChange={(evento) => setDados({ ...dados, telefone: formatarTelefone(evento.target.value) })}
        />
        <div>
          <Selecao
            rotulo="Papel"
            value={dados.papel}
            onChange={(evento) => setDados({ ...dados, papel: evento.target.value as Papel })}
            erro={erro?.doCampo('papel')}
          >
            {PAPEIS.map((papel) => (
              <option key={papel.valor} value={papel.valor}>{papel.rotulo}</option>
            ))}
          </Selecao>
          <p className="mt-1 text-xs text-slate-500">
            {PAPEIS.find((papel) => papel.valor === dados.papel)?.descricao}
          </p>
        </div>
        <Campo
          rotulo={usuario ? 'Nova senha (deixe em branco para manter)' : 'Senha'}
          type="password"
          value={dados.senha}
          onChange={(evento) => setDados({ ...dados, senha: evento.target.value })}
          required={!usuario}
          erro={erro?.doCampo('senha')}
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

function MinhaConta({ aoAtualizar }: { aoAtualizar: (usuario: never) => void }) {
  const { usuario } = useAutenticacao()
  const [nome, setNome] = useState(usuario?.nome ?? '')
  const [telefone, setTelefone] = useState(usuario?.telefone ?? '')
  const [senhaAtual, setSenhaAtual] = useState('')
  const [senhaNova, setSenhaNova] = useState('')
  const [erro, setErro] = useState<ErroApi | null>(null)
  const [mensagem, setMensagem] = useState<string | null>(null)

  const salvarPerfil = useMutation({
    mutationFn: () => api.patch('/auth/eu/', { nome, telefone }),
    onSuccess: (atualizado) => {
      aoAtualizar(atualizado as never)
      setMensagem('Perfil atualizado.')
      setTimeout(() => setMensagem(null), 3000)
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha : null),
  })

  const trocarSenha = useMutation({
    mutationFn: () => api.post('/auth/senha/', { senha_atual: senhaAtual, senha_nova: senhaNova }),
    onSuccess: () => {
      setSenhaAtual('')
      setSenhaNova('')
      setErro(null)
      setMensagem('Senha alterada.')
      setTimeout(() => setMensagem(null), 3000)
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha : null),
  })

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Cartao titulo="Meus dados">
        <form
          className="space-y-3"
          onSubmit={(evento) => { evento.preventDefault(); salvarPerfil.mutate() }}
        >
          <Campo rotulo="Nome" value={nome} onChange={(evento) => setNome(evento.target.value)} />
          <Campo
            rotulo="Telefone"
            value={telefone}
            onChange={(evento) => setTelefone(formatarTelefone(evento.target.value))}
          />
          <Campo rotulo="E-mail" value={usuario?.email ?? ''} disabled dica="O e-mail de acesso não pode ser alterado aqui." />
          <Botao type="submit" carregando={salvarPerfil.isPending}>
            Salvar
          </Botao>
        </form>
      </Cartao>

      <Cartao titulo="Trocar senha">
        <form
          className="space-y-3"
          onSubmit={(evento) => { evento.preventDefault(); trocarSenha.mutate() }}
        >
          <Campo
            rotulo="Senha atual"
            type="password"
            value={senhaAtual}
            onChange={(evento) => setSenhaAtual(evento.target.value)}
            required
            erro={erro?.doCampo('senha_atual')}
          />
          <Campo
            rotulo="Nova senha"
            type="password"
            value={senhaNova}
            onChange={(evento) => setSenhaNova(evento.target.value)}
            required
            erro={erro?.doCampo('senha_nova')}
            dica="Mínimo de 8 caracteres."
          />
          <Botao type="submit" carregando={trocarSenha.isPending}>
            Alterar senha
          </Botao>
        </form>
      </Cartao>

      {mensagem && (
        <div className="lg:col-span-2">
          <Alerta tipo="sucesso">{mensagem}</Alerta>
        </div>
      )}
    </div>
  )
}
