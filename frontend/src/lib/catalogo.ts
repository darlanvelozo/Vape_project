/** Regras do catálogo que a tela precisa conhecer. */

import type { Variacao } from './tipos'

type Precos = Pick<Variacao, 'preco_custo_centavos' | 'preco_venda_centavos' | 'ativo'>

/**
 * Preço do modelo: o valor que os sabores têm em comum.
 *
 * Em loja de vape o preço é do modelo, não do sabor. Quando algum sabor foge
 * da regra (uma exceção pontual), o campo vem `null` e a tela mostra "varia
 * por sabor" em vez de inventar um valor. Sabor inativo só conta se não
 * houver nenhum ativo — preço antigo de sabor que saiu da prateleira não deve
 * esconder o preço atual.
 */
export function precoDoModelo(variacoes: Precos[]): { custo: number | null; venda: number | null } {
  const ativas = variacoes.filter((variacao) => variacao.ativo)
  const base = ativas.length > 0 ? ativas : variacoes
  const unico = (valores: number[]) =>
    valores.length > 0 && valores.every((valor) => valor === valores[0]) ? valores[0] : null
  return {
    custo: unico(base.map((variacao) => variacao.preco_custo_centavos)),
    venda: unico(base.map((variacao) => variacao.preco_venda_centavos)),
  }
}

/** Centavos no formato que o campo de texto espera ("95,00"); vazio quando não há valor. */
export function centavosParaCampo(centavos: number | null | undefined): string {
  return centavos == null ? '' : (centavos / 100).toFixed(2).replace('.', ',')
}
