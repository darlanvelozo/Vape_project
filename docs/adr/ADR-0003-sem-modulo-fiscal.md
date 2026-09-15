# ADR-0003 — Sem módulo fiscal e sem gateway de pagamento na v1

- Data: 2026-09-15
- Status: aceita

## Contexto

CONTEXT.md §5.4 apontava a necessidade de decidir sobre emissão fiscal. No
Brasil, a **RDC 855/2024 da ANVISA** proíbe a comercialização, importação e
propaganda de dispositivos eletrônicos para fumar. Na prática isso significa
que não há caminho regular para emitir NFC-e desses itens, e que gateways de
pagamento e marketplaces costumam vedar o ramo em seus termos de uso.

## Decisão

A v1 **não** emite documento fiscal e **não** integra gateway de pagamento.

- As formas de pagamento (dinheiro, Pix, débito, crédito, fiado) são apenas
  **registradas** na venda, para efeito de conferência de caixa e financeiro.
  O sistema não movimenta dinheiro nem confirma recebimento com terceiros.
- O comprovante da venda é um **recibo interno não fiscal**, impresso com essa
  ressalva explícita no rodapé.
- `Cliente.data_nascimento` é obrigatório e o sistema bloqueia venda para menor
  de 18 anos identificado, registrando a conferência de idade.

## Consequências

- **Positivo:** nenhuma dependência de certificado digital, SEFAZ, contrato com
  adquirente ou credenciais de gateway. O deploy não guarda segredo de terceiro.
- **Positivo:** o sistema é ferramenta de gestão interna — não declara ao fisco
  nem processa pagamento, o que reduz a superfície regulatória.
- **Negativo:** conciliação com a maquininha de cartão e com o extrato Pix é
  manual, feita no fechamento de caixa.
- **Revisão:** se a operação for para outra jurisdição, ou se a RDC mudar, este
  ADR deve ser substituído por outro que defina emissor e regime.
