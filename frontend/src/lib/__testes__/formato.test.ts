/**
 * Testes de formatação de dinheiro e data.
 *
 * Este módulo é a fronteira entre a API e a tela. Erro aqui não quebra nada
 * visivelmente — só mostra o valor ou o dia errado, que é pior.
 */

import { describe, expect, it } from 'vitest'

import {
  dataISO,
  formatarData,
  formatarDataHora,
  formatarMoeda,
  formatarTelefone,
  paraCentavos,
} from '../formato'

/**
 * O Intl separa "R$" do número com espaço não-quebrável (U+00A0), não com
 * espaço comum — sem normalizar, a comparação falha com duas strings que
 * parecem idênticas na tela.
 */
const moeda = (centavos: number | null | undefined) =>
  formatarMoeda(centavos).replace(/\u00A0/g, ' ')

describe('dinheiro', () => {
  it('formata centavos como real', () => {
    expect(moeda(12345)).toBe('R$ 123,45')
    expect(moeda(0)).toBe('R$ 0,00')
    expect(moeda(1)).toBe('R$ 0,01')
    expect(moeda(150000)).toBe('R$ 1.500,00')
  })

  it('trata ausência de valor como zero', () => {
    expect(moeda(null)).toBe('R$ 0,00')
    expect(moeda(undefined)).toBe('R$ 0,00')
  })

  it('lê o que o usuário digita, em qualquer formato usual', () => {
    expect(paraCentavos('12,34')).toBe(1234)
    expect(paraCentavos('12.34')).toBe(1234)
    expect(paraCentavos('1.234,56')).toBe(123456)
    expect(paraCentavos('R$ 99,90')).toBe(9990)
    expect(paraCentavos('150')).toBe(15000)
  })

  it('devolve zero para entrada inválida em vez de NaN', () => {
    expect(paraCentavos('')).toBe(0)
    expect(paraCentavos('abc')).toBe(0)
  })

  it('não perde centavo na ida e volta', () => {
    for (const centavos of [1, 55, 6000, 7800, 12000, 15000, 116000]) {
      expect(paraCentavos(formatarMoeda(centavos))).toBe(centavos)
    }
  })
})

describe('datas', () => {
  it('mostra data pura no dia certo', () => {
    // Regressão: `new Date('2026-09-08')` é meia-noite UTC, que em
    // Brasília (UTC−3) cai em 07/09 — a tela mostrava o dia anterior em
    // todo vencimento e rótulo de gráfico.
    expect(formatarData('2026-09-08')).toBe('08/09/2026')
    expect(formatarData('2026-01-01')).toBe('01/01/2026')
    expect(formatarData('2026-12-31')).toBe('31/12/2026')
  })

  it('mostra timestamp com fuso no instante certo', () => {
    expect(formatarDataHora('2026-09-08T14:30:00-03:00')).toContain('08/09/2026')
  })

  it('trata vazio e inválido sem quebrar a tela', () => {
    expect(formatarData(null)).toBe('—')
    expect(formatarData('')).toBe('—')
    expect(formatarData('data-invalida')).toBe('—')
    expect(formatarDataHora(undefined)).toBe('—')
  })

  it('gera o filtro de data a partir do dia local', () => {
    // 23h de 15/09 no Brasil já é 16/09 em UTC; o filtro precisa dizer 15.
    expect(dataISO(new Date(2026, 8, 15, 23, 30))).toBe('2026-09-15')
    expect(dataISO(new Date(2026, 0, 1, 0, 0))).toBe('2026-01-01')
  })

  it('fecha o ciclo: o que é gerado é lido de volta igual', () => {
    const hoje = new Date(2026, 8, 15)
    expect(formatarData(dataISO(hoje))).toBe('15/09/2026')
  })
})

describe('telefone', () => {
  it('formata celular e fixo', () => {
    expect(formatarTelefone('11999990000')).toBe('(11) 99999-0000')
    expect(formatarTelefone('1133334444')).toBe('(11) 3333-4444')
  })

  it('formata parcialmente enquanto o usuário digita', () => {
    expect(formatarTelefone('11')).toBe('11')
    expect(formatarTelefone('119999')).toBe('(11) 9999')
  })
})

describe('zero negativo', () => {
  it('não formata menos-zero com sinal', () => {
    // Uma despesa zerada, negada para exibição, vira -0 — e o Intl escreve
    // "-R$ 0,00", que sugere um valor que não existe.
    expect(moeda(Math.abs(-0))).toBe('R$ 0,00')
    expect(Object.is(-0, 0)).toBe(false)
    expect(-0 < 0).toBe(false)
  })
})
