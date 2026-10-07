# Changelog

Todas as mudanças relevantes deste projeto são registradas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [1.5.2] — 2026-10-07

Segunda rodada do celular: operações percorridas como o lojista (venda no PDV,
estoque, produto, caixa, cliente, financeiro) e a vitrine como o cliente.

### Melhorado
- **Janelas viram folha que sobe de baixo no celular**, na largura toda; no
  desktop seguem centradas. Em "Novo produto", "Editar produto" e "Novo
  cliente" o **Salvar ficava abaixo da tela** — agora os botões de ação ficam
  presos no rodapé enquanto o formulário rola. O "X" de fechar passou de
  ~26 px para 44 px.
- PDV: a faixa do carrinho no celular diz "3 itens no carrinho · Ver ›".
- Vitrine: botões Adicionar, mais/menos e fechar pedido com 44 px (eram 36–40).

### Corrigido
- **Link do WhatsApp da vitrine com 55 duplicado** quando o lojista salvava o
  número com o código do país (wa.me/5555…): o pedido do cliente não chegava.
  Regra em `numeroWhatsApp` (`lib/formato.ts`), com teste.

## [1.5.1] — 2026-10-07

Inspeção do sistema inteiro no celular (iPhone 390 px e Android 360 px), tela
a tela e navegando pelas operações — a loja passa a ser gerida principalmente
pelo telefone.

### Melhorado
- **Tabelas viram cartões no celular.** Vendas, Estoque, Clientes,
  Fornecedores, Caixa e Relatórios tinham tabelas de 475 a 745 px numa tela de
  360–390 px: cortadas à direita, com o nome do produto quebrado em 5 linhas.
  Abaixo de 640 px cada linha vira um cartão "rótulo: valor" (a primeira coluna
  é o título, as ações vão para o rodapé). Feito uma vez em `TabelaEnvolvida`
  + CSS; no desktop nada muda.
- **PDV:** o sabor em destaque (é o que o cliente pede), o modelo em cima e
  menor, dois itens por linha no celular, item sem estoque apagado, busca com
  texto que cabe.
- **Caixa e Estoque:** números dois por linha e botões de ação dividindo a
  linha por igual, em vez de quatro cartões empilhados e botão órfão.
- **Relatórios:** as seis abas numa faixa que rola de lado, em vez de três
  linhas de botões; datas lado a lado (também em Vendas).

### Corrigido
- Campos com 14 px no celular (o iPhone dava zoom ao tocar): a regra de 16 px
  existia, mas a classe `.campo` a anulava. Afetava todas as telas.
- Abas com 40 px de altura (Estoque, Financeiro, Relatórios), abaixo do mínimo
  de 44 px; botões de quantidade do carrinho com 40 px de largura.
- Links do Guia com 16 px de altura de toque.

## [1.5.0] — 2026-09-15

### Adicionado
- **Foto por modelo no catálogo.** Upload em Produtos, exibida na vitrine e na
  listagem. A imagem é reduzida e recomprimida no envio — foto de celular chega
  com 3 a 8 MB e sairia assim para quem abre a vitrine no 4G. Orientação da
  câmera é respeitada, transparência ganha fundo branco e tudo vira JPEG de no
  máximo 900 px.
- **Pedido de reserva na vitrine.** O cliente monta o carrinho e o botão abre o
  WhatsApp da loja com a lista pronta: itens, quantidades e total. O carrinho
  sobrevive a fechar a aba.
- A quantidade que o cliente pode pedir respeita a faixa de estoque — "última
  unidade" não deixa somar mais de uma —, sem revelar o saldo exato.

### Segurança
- O upload valida que o arquivo é mesmo uma imagem (não basta a extensão), com
  limite de 10 MB e nome gerado por UUID: nome enviado pelo usuário nunca chega
  ao disco.
- `/media/` passa a declarar explicitamente os tipos servidos e os cabeçalhos
  de segurança, por ser o único diretório alimentado por upload.

## [1.4.0] — 2026-09-15

### Adicionado
- **Guia de uso** (`/guia`), no menu do sistema: 14 seções explicando cada
  tela, como operar e por que cada regra existe — escrito para o lojista e a
  equipe do balcão, não para quem desenvolve. Inclui as dúvidas que aparecem
  no primeiro mês ("não consigo vender", "o caixa não bate", "lucro positivo
  com caixa negativo").
- O importador aceita uma seção `equipe`, para que os acessos dos sócios e
  vendedores vivam no arquivo e sobrevivam a um `--recriar`.

## [1.3.0] — 2026-09-15

### Adicionado
- **Visão de gestão no financeiro** (`/api/relatorios/resultado/`), separando
  três contas que costumam ser confundidas:
  - **Resultado** — faturamento menos o custo da mercadoria vendida e as
    despesas da loja. É o que o negócio ganhou.
  - **Caixa** — o dinheiro que entrou e saiu no período, onde a compra pesa
    integralmente no mês em que foi feita.
  - **Pendências** — a receber e a pagar, com o vencido destacado.
  A tela explica a diferença entre lucro e caixa apontando quanto virou
  estoque, que é a dúvida mais cara de uma loja pequena.
- Estoque exibido como patrimônio: quanto custou, quanto vale a preço de
  venda e quanto ainda há de lucro para realizar.

### Corrigido
- **Compra à vista não entrava no financeiro.** Só compra com vencimento
  gerava lançamento, então o dinheiro gasto com mercadoria sumia do
  relatório: a loja aparecia com R$ 1.160 de receita e nenhuma despesa, como
  se tudo fosse lucro. Agora toda compra recebida vira despesa — pendente se
  a prazo, já baixada se à vista.
- Cancelar compra à vista devolvia o estoque mas deixava a saída no
  financeiro.
- **Venda gravava custo desatualizado** quando quem chamava o serviço tinha
  em mãos uma instância carregada antes da última compra. Como o custo fica
  congelado no item, a margem daquela venda ficaria errada para sempre —
  `criar_venda` passa a ler o custo do banco.
- Despesa zerada aparecia como "−R$ 0,00": em JavaScript `-0 < 0` é falso,
  mas o formatador escreve o sinal.

## [1.2.0] — 2026-09-15

### Adicionado
- **Vitrine pública**: página sem senha (`/vitrine/<slug>`) com o que está
  disponível em estoque, para a loja mandar aos clientes. Nasce desligada e
  é ativada em Configurações → Vitrine pública, onde também fica o link para
  copiar. Expõe o mínimo: só itens com saldo, sem custo, sem margem e sem
  quantidade exata — a disponibilidade aparece em faixas ("última unidade",
  "poucas unidades", "disponível"). Traz aviso de idade mínima, tem limite de
  requisições por IP e não é indexada por buscadores.
- `noindex` em todo o site (cabeçalho `X-Robots-Tag` e `robots.txt`): nem o
  sistema nem a vitrine pertencem a buscador.
- Teste de arquitetura que recusa view de domínio sem resolução de loja.

### Corrigido
- **`/api/loja/` e `/api/loja/configuracao/` não enxergavam a loja.**
  `request.loja` vem do middleware, que roda antes de o DRF autenticar o JWT
  — naquele instante o usuário ainda é anônimo. A tela "Dados da loja" abria
  com os campos vazios, a de "Operação" respondia HTTP 409, e salvar criava
  uma **loja nova e vazia** em vez de atualizar a existente. As views passam a
  herdar de `core.views.LojaAPIView`, que resolve a loja depois da
  autenticação.

### Usabilidade em celular
- Painel rolava de lado no iPhone SE: o cartão do gráfico é item de grid e,
  sem `min-width: 0`, não encolhia abaixo do conteúdo.
- Campos com fonte menor que 16px faziam o Safari dar zoom ao focar,
  desalinhando a tela no meio da venda.
- Alvos de toque abaixo de 44px (menu, abas, ícones de ação em tabela,
  interruptores, links de rodapé de cartão) foram ajustados ao mínimo
  recomendado por Apple HIG, Material e WCAG 2.5.5.
- Barras fixas do PDV e da vitrine respeitam a faixa do gesto de início nos
  aparelhos sem botão físico.
- `touch-action: manipulation` elimina o atraso de 300ms e o zoom por
  duplo-toque, que no balcão faziam o clique parecer não ter pego.
- Componente `BotaoIcone` padroniza a área de toque das colunas de ação.

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
