/** Preço do modelo: o que a tela mostra como "vale para todos os sabores". */

import { describe, expect, it } from 'vitest'

import { centavosParaCampo, precoDoModelo } from '../catalogo'

const sabor = (custo: number, venda: number, ativo = true) => ({
  preco_custo_centavos: custo,
  preco_venda_centavos: venda,
  ativo,
})

describe('precoDoModelo', () => {
  it('devolve o preço quando todos os sabores têm o mesmo', () => {
    expect(precoDoModelo([sabor(6175, 9500), sabor(6175, 9500)])).toEqual({ custo: 6175, venda: 9500 })
  })

  it('marca como variável só o campo que diverge', () => {
    expect(precoDoModelo([sabor(6175, 9500), sabor(6000, 9500)])).toEqual({ custo: null, venda: 9500 })
  })

  it('ignora sabor inativo com preço antigo', () => {
    expect(precoDoModelo([sabor(6175, 9500), sabor(5000, 8000, false)])).toEqual({ custo: 6175, venda: 9500 })
  })

  it('usa os inativos quando não há nenhum ativo', () => {
    expect(precoDoModelo([sabor(5000, 8000, false)])).toEqual({ custo: 5000, venda: 8000 })
  })

  it('modelo sem sabores não tem preço', () => {
    expect(precoDoModelo([])).toEqual({ custo: null, venda: null })
  })
})

describe('centavosParaCampo', () => {
  it('formata com vírgula e duas casas', () => {
    expect(centavosParaCampo(9500)).toBe('95,00')
    expect(centavosParaCampo(6175)).toBe('61,75')
  })

  it('fica vazio sem valor', () => {
    expect(centavosParaCampo(null)).toBe('')
  })
})
