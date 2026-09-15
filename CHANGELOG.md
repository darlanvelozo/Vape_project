# Changelog

Todas as mudanças relevantes deste projeto são registradas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [1.1.0] — 2026-09-15

### Adicionado
- Comando `importar_operacao`: traz para o sistema o catálogo, as compras e as
  vendas que a loja já tinha antes de começar a usá-lo. Processa os eventos em
  ordem cronológica pelos serviços de domínio, abre e fecha um caixa por dia de
  venda, e confere os totais informados antes de gravar. O arquivo de dados
  fica fora do repositório (`dados/`), com o formato em `dados/EXEMPLO.json`.
- Prazo de vencimento configurável para a venda fiada
  (`ConfiguracaoLoja.prazo_fiado_dias`, padrão 30 dias).
- Testes de frontend com vitest, cobrindo formatação de dinheiro e de datas.
- Paginação em todas as listagens — antes só os primeiros 50 registros eram
  alcançáveis pela tela.

### Corrigido
- **Datas apareciam um dia antes.** `new Date('2026-09-08')` é interpretado
  como meia-noite UTC, que no horário de Brasília cai no dia 07 — todo
  vencimento, data de compra e rótulo de gráfico exibia o dia anterior.
  `dataISO` tinha o problema espelhado: à noite, gerava o filtro do dia
  seguinte.
- **Cabeçalhos de segurança ausentes na página do sistema.** No Nginx, um
  `add_header` em nível de `location` descarta os herdados do `server`; como a
  SPA é servida por um location que define Cache-Control, ela ia sem HSTS nem
  X-Frame-Options. Só a API vinha protegida.
- Venda fiada nascia com vencimento no mesmo dia, marcando toda venda a prazo
  como atrasada já no dia seguinte.
- PDV no celular mostrava o carrinho acima da busca, empurrando o campo para
  fora da tela; o carrinho virou barra fixa no rodapé.
- Eixo dos gráficos truncava valores acima de cinco dígitos.

## [1.0.0] — 2026-09-15

Primeira versão em produção: https://vape.2-24-122-160.sslip.io

### Adicionado

**Fundação**
- Backend Django 5.1 + DRF com apps `core`, `lojas`, `usuarios`, `produtos`,
  `estoque`, `clientes`, `fornecedores`, `vendas`, `financeiro`, `relatorios`.
- Frontend React 18 + Vite + TypeScript + Tailwind, com carregamento das rotas
  sob demanda (o pacote inicial fica em ~94 kB gzip).
- Multi-tenancy SaaS por linha, com cadastro público de loja (ADR-0001).
- Autenticação JWT com renovação automática; papéis dono, gerente e vendedor.

**Domínio**
- Catálogo com variações (sabor, nicotina, puffs, volume), SKU e código de
  barras, preço de custo e venda, margem e estoque mínimo.
- Estoque com entrada, saída, perda, devolução, estorno e inventário por
  contagem; saldo travado com `select_for_update` e extrato auditável
  (`saldo_apos` em cada movimento); custo médio ponderado.
- PDV com busca por nome/sabor/SKU/código de barras, leitor de código de
  barras, desconto, pagamento dividido, troco e atalho F2.
- Caixa com fundo de troco, sangria, suprimento, conferência por forma de
  pagamento e fechamento com apuração da diferença.
- Clientes com histórico, limite de crédito (fiado) e bloqueio de venda a
  menor de idade.
- Fornecedores e compras: rascunho, recebimento que dá entrada no estoque e
  gera conta a pagar, cancelamento com estorno.
- Financeiro com contas a pagar e receber, baixa, estorno e fluxo de caixa
  realizado por dia; venda fiada vence conforme o prazo configurado na loja.
- Relatórios: mais vendidos, margem, curva ABC, giro de estoque, formas de
  pagamento e desempenho da equipe.

**Qualidade**
- 114 testes com pytest, cobrindo dinheiro, estoque, caixa, venda, fiado,
  cancelamento e isolamento entre lojas.
- CI no GitHub Actions: ruff, checagem de migrações pendentes, testes,
  `check --deploy` e build do frontend.
- Documentação da API em OpenAPI (`/api/docs/`).

**Produção**
- Nginx + gunicorn + systemd com hardening; HTTPS via Let's Encrypt.
- Backup diário do Postgres com retenção de 14 dias e script de restauração.
- `scripts/deploy.sh` com backup, testes, migrações e build antes do restart.
- Comando `criar_dados_demo` para popular uma loja de demonstração.

### Decisões
- [ADR-0001](docs/adr/ADR-0001-multi-tenant-por-linha.md) — multi-tenancy por linha.
- [ADR-0002](docs/adr/ADR-0002-dinheiro-decimal-e-centavos.md) — `Decimal` no banco, centavos na API.
- [ADR-0003](docs/adr/ADR-0003-sem-modulo-fiscal.md) — sem módulo fiscal e sem gateway.

## [0.0.1] — 2026-09-15 (não lançado)

### Adicionado
- Estrutura inicial do repositório: README, CLAUDE.md, CONTEXT.md,
  docs/ROADMAP.md, docker-compose (Postgres 16 + Redis 7), `.env.example`.
