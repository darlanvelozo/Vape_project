# Roadmap — Vape Project

> Atualizado em 2026-09-15, com a v1.0.0 em produção.

| Bloco | Nome | Conteúdo | Status |
|-------|------|----------|--------|
| 0 | Fundação | Estrutura, backend e frontend inicializados, auth + usuários, CI (lint + testes) | ✅ |
| 1 | Cadastros | Produtos e variações, categorias, marcas, fornecedores, clientes | ✅ |
| 2 | Estoque | Entradas, saídas, ajustes, saldo por variação, alerta de mínimo, custo médio | ✅ |
| 3 | Vendas / PDV | Venda de balcão, caixa, formas de pagamento, cancelamento, recibo | ✅ |
| 4 | Financeiro | Contas a pagar/receber, fluxo de caixa, baixa e estorno | ✅ |
| 5 | Relatórios | Mais vendidos, margem, giro, curva ABC, formas de pagamento, equipe, dashboard | ✅ |
| 6 | Produção | Deploy VPS (nginx + gunicorn + systemd), backup, HTTPS | ✅ |
| 7 | Extras | — | ⬜ |

## Bloco 7 — próximos passos possíveis

Nenhum destes está contratado; são os candidatos naturais depois da v1.

| Item | Por quê | Esforço |
|---|---|---|
| **Importador de planilha** | Loja que já existe tem catálogo e clientes em Excel; digitar tudo à mão é a maior barreira de adoção | Médio |
| **Domínio próprio** | `sslip.io` funciona, mas não passa credibilidade a cliente pagante | Baixo |
| **PWA / modo offline** | Queda de internet no balcão trava a venda; um cache de catálogo com fila de sincronização resolveria | Alto |
| **Impressão térmica** | Hoje o recibo sai pelo diálogo do navegador; impressora 58 mm exige formato próprio | Médio |
| **Cobrança do SaaS** | `Loja.plano` e limites já existem no modelo, mas não há faturamento | Alto |
| **Alertas de reposição** | Avisar por e-mail/WhatsApp quando item chega ao mínimo, em vez de depender de olhar o painel | Médio |
| **Metas e comissão** | O relatório de equipe já mede faturamento por vendedor; falta meta e cálculo de comissão | Médio |
