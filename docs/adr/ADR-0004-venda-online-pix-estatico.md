# ADR-0004 — Venda pela vitrine com Pix estático e conferência humana

- Data: 2026-11-09
- Status: aceita (complementa o ADR-0003, não o substitui)

## Contexto

A vitrine pública nasceu como catálogo: o cliente montava o pedido e o
mandava por WhatsApp, e o atendente fazia o resto na conversa (chave Pix,
endereço, confirmação). Em produção isso virou o gargalo:

- toda venda da Vaporize até aqui foi em Pix, e cada uma exigiu troca
  manual de chave, valor e comprovante;
- o cliente pediu explicitamente o QR Code e a opção de retirada;
- nada ficava registrado no sistema até o atendente lançar a venda no PDV,
  então dois clientes podiam reservar a mesma última unidade.

O ADR-0003 continua valendo: a RDC 855/2024 proíbe a comercialização desses
produtos e os gateways de pagamento vedam o ramo. **Integrar um gateway não
é opção** — além do risco regulatório, a conta seria bloqueada.

## Decisão

A vitrine passa a aceitar **pedido com pagamento Pix**, sem gateway:

1. **Pix estático gerado pelo próprio sistema.** O BR Code (padrão EMV do
   Banco Central) é montado com a chave Pix da própria loja, o valor exato do
   pedido e o código do pedido como identificador. Nenhum terceiro participa;
   nenhuma credencial é guardada.
2. **Confirmação humana.** O sistema não sabe se o dinheiro caiu — continua
   valendo "não confirma recebimento com terceiros". O cliente pode anexar o
   comprovante; o atendente confere no app do banco e aprova no painel. Só a
   aprovação cria a `Venda`, baixa o estoque e lança o financeiro.
3. **Reserva com prazo.** Enquanto aguarda pagamento, o pedido segura as
   unidades por um prazo configurável (padrão 30 min). A reserva **não**
   escreve em `Variacao.saldo`: o disponível da vitrine é `saldo − reservas
   ativas`, calculado com as linhas de variação travadas. Pedido vencido
   simplesmente deixa de contar — sem worker nem cron.
4. **Identificação mínima.** O cliente informa telefone e um codinome. Como
   não há data de nascimento, o bloqueio por idade do PDV não atua; o pedido
   exige e registra a **declaração de maioridade**.
5. **Entrega ou retirada.** Para entrega, a localização vem do GPS do
   celular (com consentimento do navegador) mais um ponto de referência. O
   painel monta a rota no Google Maps por link — sem API paga.
6. **Comprovante de compra.** Após a aprovação, a página do pedido vira o
   comprovante (número da venda, itens, total, selo "pago"). Continua sendo
   documento **sem valor fiscal**.

A funcionalidade nasce **desligada** por loja (`venda_online`), como a
própria vitrine.

## Consequências

- **Positivo:** o cliente compra sozinho, a qualquer hora; o atendente só
  confere e entrega. Acaba a venda dupla da última unidade.
- **Positivo:** continua sem segredo de terceiro no deploy e sem dependência
  de contrato com adquirente.
- **Negativo:** a conferência do Pix segue manual. Pagamento sem aprovação
  vence e devolve a reserva; se o cliente pagar depois disso, o atendente
  resolve na conversa.
- **Negativo:** localização e comprovante são dados pessoais. O comprovante
  fica **fora** de `/media/` (que é público) e só é servido ao painel
  autenticado da própria loja.
- **Risco regulatório:** vender pela internet não muda o enquadramento da
  RDC 855/2024 — a decisão de operar é do lojista. O sistema não anuncia em
  buscador (vitrine continua `noindex`) e exige declaração de maioridade.
