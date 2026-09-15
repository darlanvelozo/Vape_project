/**
 * Formatação de dinheiro, datas e números.
 *
 * Dinheiro trafega e é calculado em **centavos inteiros** (ADR-0002); estas
 * funções só existem na fronteira com a tela.
 */

export function formatarMoeda(centavos: number | null | undefined): string {
  const valor = (centavos ?? 0) / 100
  return valor.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  })
}

/** Versão curta, sem o "R$" — para tabelas densas. */
export function formatarValor(centavos: number | null | undefined): string {
  return ((centavos ?? 0) / 100).toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/**
 * Converte o que o usuário digitou em centavos.
 *
 * Aceita "12,34", "12.34", "1.234,56" e "R$ 12,34". Sem isto, cada campo de
 * preço reinventaria o parsing — e erraria no separador de milhar.
 */
export function paraCentavos(texto: string): number {
  if (!texto) return 0
  const limpo = texto.replace(/[^\d,.-]/g, '')
  // Se tem vírgula, ela é o separador decimal e o ponto é milhar.
  const normalizado = limpo.includes(',')
    ? limpo.replace(/\./g, '').replace(',', '.')
    : limpo
  const numero = Number.parseFloat(normalizado)
  if (Number.isNaN(numero)) return 0
  return Math.round(numero * 100)
}

export function formatarData(iso: string | null | undefined): string {
  if (!iso) return '—'
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return '—'
  return data.toLocaleDateString('pt-BR')
}

export function formatarDataHora(iso: string | null | undefined): string {
  if (!iso) return '—'
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return '—'
  return data.toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

/** "2026-09-15" — formato que a API espera em filtros de data. */
export function dataISO(data: Date): string {
  return data.toISOString().slice(0, 10)
}

export function diasAtras(dias: number): string {
  const data = new Date()
  data.setDate(data.getDate() - dias)
  return dataISO(data)
}

export function formatarNumero(valor: number | null | undefined): string {
  return (valor ?? 0).toLocaleString('pt-BR')
}

export function formatarPercentual(valor: number | null | undefined): string {
  return `${(valor ?? 0).toFixed(1).replace('.', ',')}%`
}

export function formatarTelefone(texto: string): string {
  const digitos = texto.replace(/\D/g, '').slice(0, 11)
  if (digitos.length <= 10) {
    return digitos.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3').replace(/-$/, '')
  }
  return digitos.replace(/(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3').replace(/-$/, '')
}
