# ADR-0002 — Dinheiro: Decimal no banco, centavos inteiros na API

- Data: 2026-09-15
- Status: aceita

## Contexto

Preço de custo, preço de venda, desconto, troco e lançamentos financeiros
exigem aritmética exata. Ponto flutuante é inaceitável: `0.1 + 0.2 != 0.3`
produz divergência de centavos no fechamento de caixa. Além disso, JSON não
tem tipo decimal — um `Decimal` serializado como número JavaScript volta a ser
float de 64 bits no navegador.

## Decisão

- **Banco e regras de negócio:** `DecimalField(max_digits=12, decimal_places=2)`.
  Toda conta intermediária usa `Decimal`; arredondamento sempre explícito com
  `ROUND_HALF_UP` via `core.utils.quantizar`.
- **API (JSON):** dinheiro trafega como **inteiro de centavos**, através de
  `core.serializers.CentavosField`, que converte `Decimal('12.34') ↔ 1234`.
  O nome do campo na API ganha o sufixo `_centavos`.
- **Frontend:** trabalha com centavos inteiros do começo ao fim; só formata
  para exibição (`formatarMoeda`) e converte na entrada (`parseMoeda`).
  Nenhum cálculo de dinheiro em float no TypeScript.

## Consequências

- **Positivo:** impossível perder centavo por arredondamento binário; o valor
  que sai do PDV é o mesmo que entra no caixa e no financeiro.
- **Positivo:** `Number.MAX_SAFE_INTEGER` comporta ~90 trilhões de reais em
  centavos — sem risco prático de estouro no JS.
- **Negativo:** a conversão precisa ser lembrada em todo campo monetário novo.
  Mitigado por `CentavosField` ser o único caminho: nenhum serializer expõe
  `DecimalField` de dinheiro diretamente.
