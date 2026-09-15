/** Entrada no sistema: login e cadastro de nova loja, na mesma tela. */

import { useState } from 'react'

import { Alerta, Botao, Campo } from '../componentes/ui'
import { ErroApi } from '../lib/api'
import { useAutenticacao } from '../lib/auth'

type Modo = 'entrar' | 'cadastrar'

export function Entrar() {
  const { entrar, cadastrar } = useAutenticacao()
  const [modo, setModo] = useState<Modo>('entrar')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<ErroApi | null>(null)

  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [nome, setNome] = useState('')
  const [nomeLoja, setNomeLoja] = useState('')
  const [telefone, setTelefone] = useState('')

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      if (modo === 'entrar') {
        await entrar(email, senha)
      } else {
        await cadastrar({ loja_nome: nomeLoja, nome, email, senha, telefone })
      }
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha : new ErroApi(0, 'Falha de conexão com o servidor.'))
    } finally {
      setEnviando(false)
    }
  }

  function trocarModo(novo: Modo) {
    setModo(novo)
    setErro(null)
  }

  return (
    <div className="flex min-h-screen flex-col justify-center bg-gradient-to-br from-marca-950 via-marca-900 to-slate-900 px-4 py-10">
      <div className="mx-auto w-full max-w-md">
        <div className="mb-6 text-center">
          <p className="text-4xl">💨</p>
          <h1 className="mt-2 text-2xl font-bold text-white">Vape Project</h1>
          <p className="mt-1 text-sm text-marca-200">
            Gestão e vendas para loja de vapes
          </p>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-2xl">
          <div className="mb-5 grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => trocarModo('entrar')}
              className={`rounded-md px-3 py-2 text-sm font-medium transition ${
                modo === 'entrar' ? 'bg-white text-marca-800 shadow-sm' : 'text-slate-500'
              }`}
            >
              Entrar
            </button>
            <button
              type="button"
              onClick={() => trocarModo('cadastrar')}
              className={`rounded-md px-3 py-2 text-sm font-medium transition ${
                modo === 'cadastrar' ? 'bg-white text-marca-800 shadow-sm' : 'text-slate-500'
              }`}
            >
              Criar minha loja
            </button>
          </div>

          <form onSubmit={enviar} className="space-y-3.5">
            {modo === 'cadastrar' && (
              <>
                <Campo
                  rotulo="Nome da loja"
                  name="loja_nome"
                  value={nomeLoja}
                  onChange={(e) => setNomeLoja(e.target.value)}
                  placeholder="Vape Store Centro"
                  required
                  erro={erro?.doCampo('loja_nome')}
                />
                <Campo
                  rotulo="Seu nome"
                  name="nome"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  placeholder="Maria Souza"
                  required
                  erro={erro?.doCampo('nome')}
                />
              </>
            )}

            <Campo
              rotulo="E-mail"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="voce@sualoja.com"
              required
              erro={erro?.doCampo('email')}
            />

            <Campo
              rotulo="Senha"
              name="senha"
              type="password"
              autoComplete={modo === 'entrar' ? 'current-password' : 'new-password'}
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
              erro={erro?.doCampo('senha') ?? erro?.doCampo('password')}
              dica={modo === 'cadastrar' ? 'Mínimo de 8 caracteres, não pode ser só números.' : undefined}
            />

            {modo === 'cadastrar' && (
              <Campo
                rotulo="Telefone (opcional)"
                name="telefone"
                value={telefone}
                onChange={(e) => setTelefone(e.target.value)}
                placeholder="(11) 90000-0000"
              />
            )}

            {erro && !erro.doCampo('email') && !erro.doCampo('senha') && (
              <Alerta>{erro.message}</Alerta>
            )}

            <Botao type="submit" carregando={enviando} className="w-full" tamanho="grande">
              {modo === 'entrar' ? 'Entrar' : 'Criar loja e entrar'}
            </Botao>
          </form>
        </div>

        <p className="mt-5 text-center text-xs text-marca-300">
          Sistema de uso interno. Não emite documento fiscal.
        </p>
      </div>
    </div>
  )
}
