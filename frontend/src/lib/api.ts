/**
 * Cliente HTTP da API.
 *
 * Centraliza três coisas que não podem ficar espalhadas: o token JWT, a
 * renovação automática quando o access expira, e a tradução dos erros do DRF
 * para uma mensagem em português que a tela possa exibir direto.
 */

const BASE = import.meta.env.VITE_API_URL ?? '/api'

const CHAVE_ACCESS = 'vape.access'
const CHAVE_REFRESH = 'vape.refresh'

export const armazenamento = {
  access: () => localStorage.getItem(CHAVE_ACCESS),
  refresh: () => localStorage.getItem(CHAVE_REFRESH),
  salvar(access: string, refresh?: string) {
    localStorage.setItem(CHAVE_ACCESS, access)
    if (refresh) localStorage.setItem(CHAVE_REFRESH, refresh)
  },
  limpar() {
    localStorage.removeItem(CHAVE_ACCESS)
    localStorage.removeItem(CHAVE_REFRESH)
  },
}

export class ErroApi extends Error {
  status: number
  campos: Record<string, string[]>

  constructor(status: number, mensagem: string, campos: Record<string, string[]> = {}) {
    super(mensagem)
    this.status = status
    this.campos = campos
  }

  /** Mensagem de um campo específico, para exibir abaixo do input. */
  doCampo(nome: string): string | undefined {
    return this.campos[nome]?.[0]
  }
}

/** Extrai uma frase legível do corpo de erro do DRF. */
function mensagemDoCorpo(corpo: unknown, status: number): string {
  if (typeof corpo === 'string' && corpo) return corpo
  if (corpo && typeof corpo === 'object') {
    const registro = corpo as Record<string, unknown>
    for (const chave of ['detalhe', 'detail', 'non_field_errors', 'erro']) {
      const valor = registro[chave]
      if (typeof valor === 'string') return valor
      if (Array.isArray(valor) && typeof valor[0] === 'string') return valor[0]
    }
    // Primeiro erro de campo que aparecer.
    for (const valor of Object.values(registro)) {
      if (Array.isArray(valor) && typeof valor[0] === 'string') return valor[0]
      if (typeof valor === 'string') return valor
    }
  }
  if (status === 401) return 'Sessão expirada. Entre novamente.'
  if (status === 403) return 'Você não tem permissão para esta ação.'
  if (status === 404) return 'Registro não encontrado.'
  if (status >= 500) return 'Erro no servidor. Tente novamente em instantes.'
  return 'Não foi possível completar a operação.'
}

function camposDoCorpo(corpo: unknown): Record<string, string[]> {
  if (!corpo || typeof corpo !== 'object') return {}
  const campos: Record<string, string[]> = {}
  for (const [chave, valor] of Object.entries(corpo as Record<string, unknown>)) {
    if (Array.isArray(valor)) campos[chave] = valor.map(String)
    else if (typeof valor === 'string') campos[chave] = [valor]
  }
  return campos
}

let renovacaoEmCurso: Promise<boolean> | null = null

/**
 * Renova o access token. Concorrentes compartilham a mesma promessa para não
 * disparar N renovações quando várias telas recebem 401 ao mesmo tempo.
 */
async function renovarToken(): Promise<boolean> {
  if (renovacaoEmCurso) return renovacaoEmCurso

  renovacaoEmCurso = (async () => {
    const refresh = armazenamento.refresh()
    if (!refresh) return false
    try {
      const resposta = await fetch(`${BASE}/auth/token/atualizar/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      })
      if (!resposta.ok) return false
      const dados = await resposta.json()
      armazenamento.salvar(dados.access, dados.refresh)
      return true
    } catch {
      return false
    } finally {
      renovacaoEmCurso = null
    }
  })()

  return renovacaoEmCurso
}

type Opcoes = {
  metodo?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  corpo?: unknown
  semAutenticacao?: boolean
}

export async function requisicao<T = unknown>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const { metodo = 'GET', corpo, semAutenticacao = false } = opcoes

  const executar = async (): Promise<Response> => {
    const cabecalhos: Record<string, string> = {}
    if (corpo !== undefined) cabecalhos['Content-Type'] = 'application/json'
    if (!semAutenticacao) {
      const token = armazenamento.access()
      if (token) cabecalhos.Authorization = `Bearer ${token}`
    }
    return fetch(`${BASE}${caminho}`, {
      method: metodo,
      headers: cabecalhos,
      body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
    })
  }

  let resposta = await executar()

  // 401 com refresh válido: renova uma vez e repete a chamada.
  if (resposta.status === 401 && !semAutenticacao && armazenamento.refresh()) {
    if (await renovarToken()) {
      resposta = await executar()
    } else {
      armazenamento.limpar()
      window.dispatchEvent(new CustomEvent('vape:sessao-expirada'))
    }
  }

  if (resposta.status === 204) return undefined as T

  const texto = await resposta.text()
  const dados = texto ? JSON.parse(texto) : null

  if (!resposta.ok) {
    throw new ErroApi(resposta.status, mensagemDoCorpo(dados, resposta.status), camposDoCorpo(dados))
  }
  return dados as T
}

/**
 * Envio de arquivo (multipart).
 *
 * Não passa pelo `requisicao` comum porque ali o corpo é serializado em JSON
 * e o Content-Type é fixado — no multipart quem define o cabeçalho, com o
 * boundary correto, é o próprio navegador.
 */
export async function enviarArquivo<T>(
  caminho: string,
  campos: Record<string, string | Blob>,
  metodo: 'POST' | 'PATCH' = 'PATCH',
): Promise<T> {
  const corpo = new FormData()
  for (const [chave, valor] of Object.entries(campos)) corpo.append(chave, valor)

  const executar = async () => {
    const cabecalhos: Record<string, string> = {}
    const token = armazenamento.access()
    if (token) cabecalhos.Authorization = `Bearer ${token}`
    return fetch(`${BASE}${caminho}`, { method: metodo, headers: cabecalhos, body: corpo })
  }

  let resposta = await executar()
  if (resposta.status === 401 && armazenamento.refresh()) {
    if (await renovarToken()) resposta = await executar()
  }

  const texto = await resposta.text()
  const dados = texto ? JSON.parse(texto) : null
  if (!resposta.ok) {
    throw new ErroApi(resposta.status, mensagemDoCorpo(dados, resposta.status), camposDoCorpo(dados))
  }
  return dados as T
}

export const api = {
  get: <T>(caminho: string) => requisicao<T>(caminho),
  post: <T>(caminho: string, corpo?: unknown, semAutenticacao = false) =>
    requisicao<T>(caminho, { metodo: 'POST', corpo, semAutenticacao }),
  patch: <T>(caminho: string, corpo: unknown) =>
    requisicao<T>(caminho, { metodo: 'PATCH', corpo }),
  put: <T>(caminho: string, corpo: unknown) => requisicao<T>(caminho, { metodo: 'PUT', corpo }),
  delete: <T>(caminho: string) => requisicao<T>(caminho, { metodo: 'DELETE' }),
}

/** Monta querystring ignorando valores vazios. */
export function querystring(parametros: Record<string, string | number | boolean | undefined>) {
  const partes = Object.entries(parametros)
    .filter(([, valor]) => valor !== undefined && valor !== '' && valor !== false)
    .map(([chave, valor]) => `${encodeURIComponent(chave)}=${encodeURIComponent(String(valor))}`)
  return partes.length ? `?${partes.join('&')}` : ''
}
