# CONTEXT.md — Contexto Global do Vape Project

> **Documento mestre.** Toda implementação deve começar pela leitura deste
> arquivo. Para Claude Code, ler também [CLAUDE.md](CLAUDE.md).
>
> Última atualização: **2026-09-15** · Versão atual: **1.5.0** ·
> **Em produção, com operação real.**

---

## 1. O que é

Sistema de **gestão e vendas para loja de vapes**. Objetivo: substituir
controle manual (planilha/caderno) por um sistema com cadastro de produtos,
estoque confiável, venda rápida no balcão e visão financeira.

Opera como **SaaS**: várias lojas, de donos diferentes, na mesma instalação.
Cada loja se cadastra sozinha e enxerga apenas os próprios dados.

## 2. Estado atual

| Item | Situação |
|---|---|
| Versão | 1.5.0, em produção desde 15/09/2026 |
| Endereço | https://vape.2-24-122-160.sslip.io |
| Backend | Django 5.1 + DRF, gunicorn em `127.0.0.1:8002` via systemd |
| Frontend | React 18 + Vite, compilado em `frontend/dist`, servido pelo Nginx |
| Banco | PostgreSQL 16 local, base `vape_prod` |
| Testes | 197 testes (pytest) + 13 (vitest), CI no GitHub Actions |
| Backup | Diário às 03h15, retenção de 14 dias, restauração testada |
| Lojas | `luxury_vapes` (operação real, desde 15/09/2026) e uma loja de demonstração |

## 3. Domínio implementado

| Módulo | Conteúdo |
|---|---|
| **Produtos** | Produto, categoria, marca, **variações** (sabor, mg de nicotina, puffs, volume), SKU, código de barras, preço de custo e venda, margem |
| **Estoque** | Entrada, saída, perda, devolução, estorno, inventário por contagem; saldo por variação; custo médio ponderado; extrato auditável |
| **Vendas (PDV)** | Venda de balcão, desconto, pagamento dividido (dinheiro, Pix, débito, crédito, fiado), troco, recibo não fiscal, cancelamento com estorno |
| **Caixa** | Abertura com fundo de troco, sangria, suprimento, conferência por forma de pagamento, fechamento com apuração de diferença |
| **Clientes** | Cadastro, histórico, limite de crédito (fiado), verificação de idade mínima |
| **Fornecedores** | Cadastro e compras: rascunho → recebimento (entrada no estoque + conta a pagar) → cancelamento com estorno |
| **Financeiro** | Visão de gestão (resultado, caixa e pendências separados), contas a pagar/receber, baixa e estorno, fluxo diário |
| **Relatórios** | Mais vendidos, margem, curva ABC, giro de estoque, formas de pagamento, desempenho da equipe |
| **Usuários** | Papéis dono, gerente e vendedor, com permissões distintas |
| **Vitrine** | Página pública com foto, carrinho e pedido de reserva pelo WhatsApp; sem custo, margem ou quantidade exata |
| **Guia de uso** | Página `/guia` com 14 seções explicando cada tela e as regras do sistema |

## 4. Arquitetura

- **Backend:** Django 5.1 + DRF + PostgreSQL 16, JWT (simplejwt), OpenAPI
  (drf-spectacular), auditoria (simple-history) em produtos e variações.
- **Frontend:** React 18 + Vite + TypeScript + Tailwind + Radix, TanStack Query;
  rotas carregadas sob demanda (pacote inicial ~94 kB gzip).
- **Infra:** Nginx + gunicorn + systemd na VPS; Redis (banco 3) para cache;
  backup diário do Postgres; HTTPS via Let's Encrypt.
- **Multi-loja:** `loja_id` em todo modelo de domínio, filtrado num único
  ponto (`core.views.LojaViewSet`) e coberto por teste dedicado.

## 5. Decisões fechadas

| # | Decisão | Onde |
|---|---|---|
| 1 | **Escopo da v1:** completo — cadastros, estoque, PDV, clientes, fornecedores, financeiro e relatórios | §3 |
| 2 | **Multi-loja:** SaaS multi-tenant, isolamento por linha (`loja_id`) | [ADR-0001](docs/adr/ADR-0001-multi-tenant-por-linha.md) |
| 3 | **Interface:** SPA responsiva — desktop no balcão, funcional em tablet e celular | §4 |
| 4 | **Fiscal:** sem módulo fiscal. No Brasil a RDC 855/2024 da ANVISA inviabiliza NFC-e para o ramo | [ADR-0003](docs/adr/ADR-0003-sem-modulo-fiscal.md) |
| 5 | **Pagamentos:** sem gateway; formas de pagamento apenas registradas | [ADR-0003](docs/adr/ADR-0003-sem-modulo-fiscal.md) |
| 6 | **Dinheiro:** `Decimal` no banco, centavos inteiros na API | [ADR-0002](docs/adr/ADR-0002-dinheiro-decimal-e-centavos.md) |
| 7 | **Domínio:** provisoriamente `vape.2-24-122-160.sslip.io` (sslip.io) | [docs/OPERACAO.md §5](docs/OPERACAO.md) |

## 6. Decisões ainda em aberto

1. **Domínio próprio** — quando houver, a migração está descrita em
   [docs/OPERACAO.md §5](docs/OPERACAO.md); leva minutos.
2. **Importação de dados existentes** — resolvido para o histórico de
   compras e vendas pelo comando `importar_operacao` (formato em
   `dados/EXEMPLO.json`). Falta um importador de planilha para catálogos
   grandes, se houver.
3. **Cobrança do SaaS** — hoje `Loja.plano` e os limites existem no modelo,
   mas não há faturamento. Definir se e como cobrar.

## 7. Histórico de decisões

| Data | Decisão | Referência |
|---|---|---|
| 2026-09-15 | Estrutura inicial criada seguindo padrão Arminda/Cobrança | — |
| 2026-09-15 | Multi-tenancy SaaS por linha (`loja_id`) | ADR-0001 |
| 2026-09-15 | Dinheiro em `Decimal` no banco e centavos na API | ADR-0002 |
| 2026-09-15 | Sem módulo fiscal e sem gateway de pagamento | ADR-0003 |
| 2026-09-15 | v1.0.0 publicada em produção com HTTPS via sslip.io | CHANGELOG |
