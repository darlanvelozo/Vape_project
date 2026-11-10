/** Rota de entrega e linha do tempo do pedido on-line. */

import { describe, expect, it } from 'vitest'

import { indiceEtapa, PARADAS_POR_ROTA, rotasNoMaps } from '../pedidos'

const ponto = (latitude: string | null, longitude: string | null, endereco = '') => ({
  latitude,
  longitude,
  endereco,
})

describe('rotasNoMaps', () => {
  it('sem pedidos não gera rota', () => {
    expect(rotasNoMaps([])).toEqual([])
  })

  it('um pedido vira destino direto, sem paradas', () => {
    const [rota] = rotasNoMaps([ponto('-5.091900', '-42.803400')])
    const url = new URL(rota)
    expect(url.searchParams.get('destination')).toBe('-5.091900,-42.803400')
    expect(url.searchParams.has('waypoints')).toBe(false)
  })

  it('usa o endereço escrito quando não há GPS e pula quem não tem nenhum', () => {
    const [rota] = rotasNoMaps([
      ponto('-5.1', '-42.8'),
      ponto(null, null, ''),
      ponto(null, null, 'Rua A, 10, Centro'),
    ])
    const url = new URL(rota)
    expect(url.searchParams.get('waypoints')).toBe('-5.1,-42.8')
    expect(url.searchParams.get('destination')).toBe('Rua A, 10, Centro')
  })

  it('divide em blocos que o Google Maps aceita', () => {
    const muitos = Array.from({ length: PARADAS_POR_ROTA + 3 }, (_, i) => ponto(`-5.${i}`, '-42.8'))
    const rotas = rotasNoMaps(muitos)
    expect(rotas).toHaveLength(2)
    const primeira = new URL(rotas[0])
    expect(primeira.searchParams.get('waypoints')?.split('|')).toHaveLength(PARADAS_POR_ROTA - 1)
  })
})

describe('indiceEtapa', () => {
  it('entrega passa por "saiu para entrega"', () => {
    expect(indiceEtapa('saiu_entrega', 'entrega')).toBe(3)
    expect(indiceEtapa('pronto_retirada', 'entrega')).toBe(-1)
  })

  it('retirada passa por "pronto para retirada"', () => {
    expect(indiceEtapa('pronto_retirada', 'retirada')).toBe(3)
  })

  it('cancelado fica fora da linha do tempo', () => {
    expect(indiceEtapa('cancelado', 'entrega')).toBe(-1)
  })
})
