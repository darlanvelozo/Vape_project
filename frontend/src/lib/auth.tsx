/**
 * Contexto de autenticação.
 *
 * O usuário fica em memória; o token, no localStorage. Ao montar, o app
 * revalida o token com `/auth/eu/` — assim uma sessão revogada no servidor
 * não continua parecendo válida na tela.
 */

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'

import { api, armazenamento } from './api'
import type { Usuario } from './tipos'

interface RespostaLogin {
  access: string
  refresh: string
  usuario: Usuario
}

interface ContextoAutenticacao {
  usuario: Usuario | null
  carregando: boolean
  entrar: (email: string, senha: string) => Promise<void>
  cadastrar: (dados: DadosCadastro) => Promise<void>
  sair: () => void
  atualizarUsuario: (usuario: Usuario) => void
  podeGerenciar: boolean
  ehDono: boolean
}

export interface DadosCadastro {
  loja_nome: string
  nome: string
  email: string
  senha: string
  telefone?: string
}

const Contexto = createContext<ContextoAutenticacao | null>(null)

export function ProvedorAutenticacao({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [carregando, setCarregando] = useState(true)

  const sair = useCallback(() => {
    armazenamento.limpar()
    setUsuario(null)
  }, [])

  useEffect(() => {
    let cancelado = false

    async function revalidar() {
      if (!armazenamento.access()) {
        setCarregando(false)
        return
      }
      try {
        const atual = await api.get<Usuario>('/auth/eu/')
        if (!cancelado) setUsuario(atual)
      } catch {
        if (!cancelado) armazenamento.limpar()
      } finally {
        if (!cancelado) setCarregando(false)
      }
    }

    revalidar()

    // O cliente HTTP avisa quando o refresh falhou de vez.
    const aoExpirar = () => setUsuario(null)
    window.addEventListener('vape:sessao-expirada', aoExpirar)
    return () => {
      cancelado = true
      window.removeEventListener('vape:sessao-expirada', aoExpirar)
    }
  }, [])

  const entrar = useCallback(async (email: string, senha: string) => {
    const dados = await api.post<RespostaLogin>(
      '/auth/token/',
      { email, password: senha },
      true,
    )
    armazenamento.salvar(dados.access, dados.refresh)
    setUsuario(dados.usuario)
  }, [])

  const cadastrar = useCallback(async (dados: DadosCadastro) => {
    const resposta = await api.post<RespostaLogin>('/auth/cadastrar/', dados, true)
    armazenamento.salvar(resposta.access, resposta.refresh)
    setUsuario(resposta.usuario)
  }, [])

  const valor: ContextoAutenticacao = {
    usuario,
    carregando,
    entrar,
    cadastrar,
    sair,
    atualizarUsuario: setUsuario,
    podeGerenciar: usuario?.papel === 'dono' || usuario?.papel === 'gerente',
    ehDono: usuario?.papel === 'dono',
  }

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}

export function useAutenticacao() {
  const contexto = useContext(Contexto)
  if (!contexto) {
    throw new Error('useAutenticacao precisa estar dentro de ProvedorAutenticacao.')
  }
  return contexto
}
