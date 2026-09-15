# Vape Project

Sistema de **gestão e vendas para loja de vapes**: catálogo com variações
(sabor, nicotina, puffs), controle de estoque, PDV com caixa, clientes,
fornecedores, financeiro e relatórios.

Multi-loja (SaaS): cada loja se cadastra sozinha e enxerga apenas os próprios
dados.

---

## Status

🟢 **v1.0.0 — em produção.**

| | |
|---|---|
| **Sistema** | https://vape.2-24-122-160.sslip.io |
| **API (docs)** | https://vape.2-24-122-160.sslip.io/api/docs/ |
| **Lojas ativas** | `luxury_vapes` (operação real) e uma loja de demonstração |
| **Vitrine da loja** | https://vape.2-24-122-160.sslip.io/vitrine/luxury_vapes |

> O endereço usa [sslip.io](https://sslip.io) porque ainda não há domínio
> próprio (CONTEXT.md §5.7). Trocar por um domínio é mudar o `server_name` no
> Nginx e reemitir o certificado — nada mais muda.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 · Django 5.1 · DRF · PostgreSQL 16 |
| Frontend | React 18 · Vite · TypeScript · Tailwind · TanStack Query |
| Infra | Nginx · gunicorn · systemd · Redis · Let's Encrypt |

## Módulos

- **Produtos** — categorias, marcas e variações (sabor, mg de nicotina, puffs,
  volume), SKU e código de barras, preço de custo e de venda, margem.
- **Estoque** — entradas, saídas, perdas, devoluções e inventário por
  contagem; saldo por variação com extrato auditável e custo médio ponderado.
- **PDV** — busca por nome/sabor/SKU/código de barras, leitor de código de
  barras, desconto, pagamento dividido, troco, recibo e atalho F2.
- **Caixa** — abertura com fundo de troco, sangria, suprimento, conferência
  por forma de pagamento e fechamento com apuração da diferença.
- **Clientes** — cadastro, histórico de compras, limite de crédito (fiado) e
  verificação de idade mínima.
- **Fornecedores e compras** — pedido em rascunho, recebimento que dá entrada
  no estoque e gera a conta a pagar, cancelamento com estorno.
- **Financeiro** — visão de gestão separando resultado (o que a loja ganhou),
  caixa (o que entrou e saiu) e pendências; contas a pagar e a receber, baixa
  e estorno, fluxo diário.
- **Relatórios** — mais vendidos, margem por produto, curva ABC, giro de
  estoque, formas de pagamento e desempenho da equipe.
- **Equipe** — papéis de dono, gerente e vendedor, com permissões distintas.
- **Vitrine pública** — página sem senha com o que há disponível, para enviar
  aos clientes. Desligada por padrão; ativa em Configurações → Vitrine
  pública. Não mostra custo, margem nem quantidade exata.

## Desenvolvimento local

```bash
./scripts/setup-dev.sh          # .env, Postgres/Redis, deps, dados de demo

cd backend && .venv/bin/python manage.py runserver   # terminal 1
cd frontend && npm run dev                           # terminal 2
```

- Sistema: http://localhost:5173
- API: http://localhost:8000/api/docs/

```bash
cd backend && .venv/bin/python -m pytest tests/ -q   # testes do backend
cd backend && .venv/bin/ruff check .                 # lint
cd frontend && npx tsc -b                            # tipos
cd frontend && npm test                              # testes do frontend
```

## Produção

Documentação completa em [docs/OPERACAO.md](docs/OPERACAO.md).

```bash
./scripts/deploy.sh        # publica (backup → testes → migrações → build → restart)
./scripts/backup.sh        # backup manual (o diário roda às 03h15 por cron)
./scripts/restaurar.sh <arquivo.sql.gz>
```

### Importar a operação de uma loja

Para colocar no sistema o que a loja já tinha antes (catálogo, compras e
vendas passadas), há um importador que aplica tudo pelos serviços de domínio
— saldo, custo médio, caixa e financeiro saem consistentes:

```bash
cd backend
.venv/bin/python manage.py importar_operacao ../dados/minha-loja.json --conferir  # só valida
.venv/bin/python manage.py importar_operacao ../dados/minha-loja.json
```

O formato está em [dados/EXEMPLO.json](dados/EXEMPLO.json). Arquivos dessa
pasta **não são versionados** — contêm dados comerciais da loja.

## Estrutura

```
vape-project/
├── backend/          API Django/DRF
│   ├── apps/         core, lojas, usuarios, produtos, estoque,
│   │                 clientes, fornecedores, vendas, financeiro, relatorios
│   ├── config/       settings (base/dev/test/prod), urls, wsgi
│   └── tests/        pytest — regras de negócio e isolamento multi-loja
├── frontend/         SPA React/Vite
│   └── src/          lib (api, auth, formato), componentes, paginas
├── deploy/           nginx, systemd, env de produção (fora do git)
├── docs/             roadmap, operação e ADRs
├── dados/            arquivos de importação (fora do git, exceto o exemplo)
├── scripts/          setup-dev, deploy, backup, restaurar
├── CLAUDE.md         instruções para o Claude Code
├── CONTEXT.md        documento mestre do projeto
└── CHANGELOG.md      histórico de versões
```

## Decisões de arquitetura

| ADR | Assunto |
|---|---|
| [0001](docs/adr/ADR-0001-multi-tenant-por-linha.md) | Multi-tenancy por linha (`loja_id` em tudo) |
| [0002](docs/adr/ADR-0002-dinheiro-decimal-e-centavos.md) | Dinheiro: `Decimal` no banco, centavos na API |
| [0003](docs/adr/ADR-0003-sem-modulo-fiscal.md) | Sem módulo fiscal e sem gateway de pagamento |

## Repositório

https://github.com/darlanvelozo/Vape_project
