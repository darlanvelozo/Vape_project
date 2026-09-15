# CLAUDE.md — Instruções para Claude Code

> Este arquivo é lido automaticamente pelo Claude Code ao abrir o repo.
> Mantém o próximo Claude alinhado sem precisar reconstruir contexto do zero.
>
> **Mensagens, commits, comentários, docs, UI: tudo em português.**
> Apenas identificadores de código (variáveis/funções/classes) ficam em
> inglês — exceto domínio brasileiro intraduzível (`cpf`, `cnpj`, `nfce`).

---

## 1. Estado atual do projeto

**Vape Project** é um sistema **SaaS de gestão e vendas para loja de vapes**
(produtos com variações de sabor/nicotina, estoque, PDV com caixa, clientes,
fornecedores, financeiro e relatórios). Várias lojas, de donos diferentes,
na mesma instalação.

- **Versão atual:** **1.0.0, em produção** desde 15/09/2026
- **Endereço:** https://vape.2-24-122-160.sslip.io (sslip.io — ainda sem
  domínio próprio)
- **Bloco corrente:** Blocos 0 a 6 concluídos. O Bloco 7 (extras) está aberto
  e nada nele foi contratado — ver [docs/ROADMAP.md](docs/ROADMAP.md).
- **Repositório:** https://github.com/darlanvelozo/Vape_project (público —
  **nunca commitar secrets**; `.env` e `deploy/env/` estão no `.gitignore`)
- **Operação:** [docs/OPERACAO.md](docs/OPERACAO.md) — deploy, backup,
  restauração, logs e migração para domínio próprio.

## 2. Antes de qualquer implementação

1. Ler [CONTEXT.md](CONTEXT.md) inteiro. As decisões de escopo estão fechadas
   na seção 5; se algo da seção 6 (ainda em aberto) afetar a tarefa,
   perguntar antes de codar.
2. Ler o ADR relevante em `docs/adr/` antes de mudar arquitetura. Os três
   existentes (multi-tenancy, dinheiro, fiscal) sustentam o sistema inteiro.
3. Ao concluir uma onda: atualizar CHANGELOG.md, CONTEXT.md (estado) e este
   arquivo (seção 1).

**O sistema está em produção com dados reais.** Mudança em estoque, caixa ou
financeiro exige teste antes e `scripts/deploy.sh` para publicar (ele faz
backup e roda a suíte antes de reiniciar).

## 3. Convenções

- **Backend:** Django 5 + DRF, apps em `backend/apps/<dominio>/`, testes
  com pytest em `backend/tests/`, settings via `django-environ`.
- **Frontend:** React 18 + Vite + TypeScript, componentes em
  `frontend/src/components/`, páginas em `frontend/src/pages/`, tipos da
  API gerados do OpenAPI (`npm run gen:types`).
- **Commits:** português, imperativo, prefixo por área
  (`backend:`, `frontend:`, `docs:`, `deploy:`).
- **Testes:** toda regra de negócio (preço, estoque, caixa) nasce com teste.
- **Dinheiro:** `Decimal` no backend, centavos inteiros na API, nunca float.

## 4. O que NÃO fazer

- Não commitar `.env`, `deploy/env/`, dumps de banco ou dados de clientes.
- Não introduzir outra stack sem ADR.
- **Não escrever `Variacao.saldo` fora de `apps.estoque.servicos`.** É o único
  lugar que trava a linha antes de ler o saldo; escrever direto perde venda
  concorrente.
- **Não criar ViewSet de domínio sem herdar de `core.views.LojaViewSet`.** É
  o único ponto que aplica o recorte por loja — e todo endpoint novo precisa
  de um caso em `backend/tests/test_isolamento_tenant.py`.
- Não expor `DecimalField` de dinheiro direto no serializer: usar
  `core.serializers.CentavosField` (ADR-0002).
