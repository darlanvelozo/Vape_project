# ADR-0001 — Multi-tenancy SaaS por linha (shared database, shared schema)

- Data: 2026-09-15
- Status: aceita

## Contexto

A v1 será um SaaS: várias lojas, de donos diferentes, no mesmo sistema
(decisão do CONTEXT.md §5.2). Existem três estratégias usuais de isolamento
em Django + PostgreSQL:

1. **Banco por tenant** — isolamento máximo, mas exige N conexões, N migrações
   e N backups. Inviável numa VPS de 1 vCPU / 3,8 GB compartilhada com outros
   três sistemas.
2. **Schema por tenant** (`django-tenants`) — isolamento bom, mas cada
   migração roda em todos os schemas e o pool de conexões cresce com o número
   de lojas. Também amarra o projeto a um pacote de terceiros pesado.
3. **Linha por tenant** — uma coluna `loja_id` em toda tabela de domínio,
   filtrada na borda da aplicação.

## Decisão

Adotamos **linha por tenant (opção 3)**.

- `lojas.Loja` é o tenant. Todo modelo de domínio herda de
  `core.models.LojaModel`, que declara `loja = FK(Loja, PROTECT)` e o
  índice correspondente.
- O isolamento é aplicado em **um único ponto**: `core.views.LojaViewSet`
  filtra `get_queryset()` por `request.loja` e injeta a loja no `perform_create`.
  Nenhuma view de domínio consulta o ORM sem passar por essa base.
- `core.middleware.LojaAtualMiddleware` resolve a loja a partir do usuário
  autenticado e a publica num `ContextVar`, de onde os serviços de domínio
  (estoque, caixa, financeiro) a leem sem precisar recebê-la por parâmetro.
- Unicidade é sempre **por loja** (`UniqueConstraint` com `loja` na composição),
  nunca global: duas lojas podem ter o mesmo SKU ou o mesmo nome de categoria.
- Superusuário (suporte) tem `loja = NULL` e enxerga o Django Admin, não a API
  de domínio.

## Consequências

- **Positivo:** uma migração, um backup, um pool de conexões. Custo de
  infraestrutura constante no número de lojas.
- **Positivo:** o ponto de vazamento é único e testável — `backend/tests/test_isolamento_tenant.py`
  cobre cada endpoint de domínio verificando que a loja A não lê nem escreve
  dados da loja B.
- **Negativo:** um `get_queryset()` esquecido vaza dados entre lojas. Mitigado
  pela ViewSet base obrigatória e pelos testes de isolamento, que devem ser
  estendidos a todo endpoint novo.
- **Negativo:** não há isolamento físico. Se um cliente exigir banco próprio
  por contrato, será necessário migrar aquele tenant — o `loja_id` em todas as
  tabelas torna essa extração viável (dump filtrado), mas não trivial.
