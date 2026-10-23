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

- **Versão atual:** **1.6.0, em produção** (22/10/2026). Lojas reais:
  `luxury_vapes` (desde 15/09) e **Vaporize** (slug `vaporize`, antes
  `temospod`; criada em 07/10, primeira venda em 22/10, dono + 2 vendedores —
  no limite de 3 usuários do plano)
- **Endereço:** https://vape.2-24-122-160.sslip.io (sslip.io — ainda sem
  domínio próprio)
- **Bloco corrente:** Blocos 0 a 6 concluídos. O Bloco 7 (extras) está aberto
  e nada nele foi contratado — ver [docs/ROADMAP.md](docs/ROADMAP.md).
- **Repositório:** https://github.com/darlanvelozo/Vape_project (público —
  **nunca commitar secrets**; `.env` e `deploy/env/` estão no `.gitignore`).
  **Em 22/10/2026 o repositório no GitHub estava vazio** (nenhuma branch): o
  código só existe nesta VPS, e os backups ficam no mesmo disco. Enviar o
  código e copiar o backup para fora é a pendência mais séria.
- **Operação:** [docs/OPERACAO.md](docs/OPERACAO.md) — deploy, backup,
  restauração, logs e migração para domínio próprio.
- **Guia do lojista:** a página `/guia` documenta o produto para quem opera.
  Funcionalidade nova que mude o dia a dia entra lá também.

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
  Frontend: `npm test` (vitest) cobre `lib/formato.ts`, onde mora a conversão
  de dinheiro e data.
- **Celular:** o sistema é usado no balcão, muitas vezes no telefone. Alvo de
  toque mínimo de 44px, campo com fonte de 16px (menos que isso faz o iOS dar
  zoom ao focar) e nenhuma página rolando na horizontal.
- **Dinheiro:** `Decimal` no backend, centavos inteiros na API, nunca float.
- **Resultado ≠ caixa.** Na apuração de lucro entra o custo da mercadoria
  *vendida* (CMV); a compra inteira entra só no fluxo de caixa. Contar a
  compra como despesa no resultado cobra o mesmo custo duas vezes, e no mês
  errado.

## 4. O que NÃO fazer

- Não commitar `.env`, `deploy/env/`, dumps de banco ou dados de clientes.
- Não introduzir outra stack sem ADR.
- **Não escrever `Variacao.saldo` fora de `apps.estoque.servicos`.** É o único
  lugar que trava a linha antes de ler o saldo; escrever direto perde venda
  concorrente.
- **Não criar view de domínio sem resolver a loja.** ViewSet herda de
  `core.views.LojaViewSet`; APIView herda de `core.views.LojaAPIView`. O
  middleware roda antes da autenticação JWT, então `request.loja` vem `None`
  em quem não usa essas bases — e o teste `TestArquitetura` recusa o commit.
  Todo endpoint novo também precisa de um caso em
  `backend/tests/test_isolamento_tenant.py`.
- **Não rodar automação de navegador contra a loja `luxury_vapes`.** São
  dados reais: uma venda de teste vira registro no financeiro. Use a loja de
  demonstração.
- Não expor `DecimalField` de dinheiro direto no serializer: usar
  `core.serializers.CentavosField` (ADR-0002).
- **Não usar `new Date('AAAA-MM-DD')` no frontend.** O construtor interpreta
  data pura como UTC e mostra o dia anterior no Brasil; usar `formatarData` e
  `dataISO` de `lib/formato.ts`.
- Não commitar `dados/*.json`: são dados comerciais da loja.
- **Imagem enviada por usuário passa por `core.imagens.processar`.** Nunca
  gravar o arquivo cru: ele pode não ser imagem, pesar 8 MB ou trazer nome
  com caminho.
