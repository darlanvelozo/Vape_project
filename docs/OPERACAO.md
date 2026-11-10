# Operação em produção

Escrito para quem vai manter este sistema no ar — inclusive o próximo Claude.

---

## 1. Onde as coisas estão

| Item | Caminho |
|---|---|
| Código | `/opt/vape-project` |
| Ambiente de produção | `/opt/vape-project/deploy/env/producao.env` (modo 600, dono `vape`) |
| Serviço | `vape-backend.service` (gunicorn em `127.0.0.1:8002`) |
| Nginx | `/etc/nginx/sites-available/vape.conf` |
| Certificado | `/etc/letsencrypt/live/vape.2-24-122-160.sslip.io/` |
| Banco | PostgreSQL 16 local, base `vape_prod`, usuário `vape` |
| Cache | Redis local, **banco 3** (o 0 e o 1 são de outros sistemas da VPS) |
| Backups | `/opt/vape-backups`, diários às 03h15, retenção de 14 dias (só o banco) |
| Comprovantes de Pix | `/opt/vape-project/backend/privado/` — **fora** de `media/`, que o nginx serve sem login. Só saem pela API autenticada da loja (ADR-0004) |
| Frontend compilado | `/opt/vape-project/frontend/dist` |

Esta VPS hospeda outros três sistemas. As escolhas de porta (8002), banco
Redis (3) e horário de backup (03h15) existem para não colidir com eles.

## 2. Comandos do dia a dia

```bash
# Estado do serviço
systemctl status vape-backend
journalctl -u vape-backend -n 100 --no-pager      # log da aplicação
journalctl -u vape-backend -f                     # acompanhar ao vivo
tail -f /var/log/nginx/vape.error.log             # erros do Nginx

# Reiniciar
systemctl restart vape-backend
nginx -t && systemctl reload nginx                # sempre testar antes

# Publicar uma nova versão
/opt/vape-project/scripts/deploy.sh

# Backup
/opt/vape-project/scripts/backup.sh
/opt/vape-project/scripts/backup.sh --listar
/opt/vape-project/scripts/restaurar.sh /opt/vape-backups/<arquivo>.sql.gz

# Console Django em produção
cd /opt/vape-project/backend
set -a; source ../deploy/env/producao.env; set +a
DJANGO_SETTINGS_MODULE=config.settings.prod .venv/bin/python manage.py shell
```

## 3. Publicar uma nova versão

`scripts/deploy.sh` faz, em ordem: **backup → testes → migrações →
collectstatic → check --deploy → build do frontend → restart**. Ele para no
primeiro erro, então uma migração quebrada não derruba o que está no ar.

A ordem importa: migrar **antes** de trocar o frontend evita que a SPA nova
chame um endpoint que ainda não existe.

## 4. Recuperação de desastre

```bash
systemctl stop vape-backend
/opt/vape-project/scripts/restaurar.sh /opt/vape-backups/<mais-recente>.sql.gz
systemctl start vape-backend
```

O script pede confirmação digitada (`RESTAURAR`) porque sobrescreve tudo.

**Verificação de integridade** — o saldo de cada variação deve bater com o
último movimento de estoque registrado. Divergência indica escrita fora do
serviço `apps.estoque.servicos`:

```sql
SELECT v.id, v.saldo FROM produtos_variacao v
WHERE v.saldo <> COALESCE((
  SELECT m.saldo_apos FROM estoque_movimentoestoque m
  WHERE m.variacao_id = v.id ORDER BY m.criado_em DESC, m.id DESC LIMIT 1
), 0);
```

O resultado esperado é vazio.

## 5. Certificado HTTPS

O certbot renova sozinho (timer `certbot.timer`). Para conferir:

```bash
certbot certificates
certbot renew --dry-run
systemctl list-timers certbot.timer
```

**Migrar para domínio próprio:**

1. Apontar o DNS do domínio para `2.24.122.160`.
2. Trocar `server_name` nos dois blocos de `/etc/nginx/sites-available/vape.conf`.
3. `certbot certonly --webroot -w /var/www/html -d SEU.DOMINIO`
4. Atualizar os caminhos `ssl_certificate` no mesmo arquivo.
5. Ajustar `DJANGO_ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` em `producao.env`.
6. `nginx -t && systemctl reload nginx && systemctl restart vape-backend`

## 6. Contas

| Conta | Uso |
|---|---|
| `demo@vapeproject.app` | Loja de demonstração. Recriar: `manage.py criar_dados_demo --recriar` |
| `ti@megalinkinternet.com.br` | Superusuário do Django Admin (`/admin/`) — suporte |

O superusuário tem `loja = NULL` de propósito: ele administra pelo Django
Admin e **não** tem acesso à API de domínio (ver ADR-0001).

## 7. Capacidade

A VPS tem 1 vCPU e 3,8 GB de RAM, compartilhados com outros três sistemas.
O gunicorn roda 2 workers × 3 threads (~95 MB), dimensionado para espera de
I/O do Postgres, não para CPU.

Sinais de que é hora de crescer:
- `journalctl -u vape-backend | grep -i timeout` aparecendo com frequência;
- `free -h` mostrando *available* abaixo de ~300 MB de forma constante;
- latência acima de 1 s em `/api/relatorios/*` com o banco já indexado.

A primeira medida é aumentar a VPS, não os workers — mais workers nesta
máquina só disputariam memória com os vizinhos.

## 8. Segurança

- `.env` de produção fora do git, modo 600, dono `vape`.
- O serviço roda como usuário sem shell, com hardening do systemd
  (`ProtectSystem`, `NoNewPrivileges`, `ReadWritePaths` restrito).
- HTTPS obrigatório, HSTS de um ano, cookies `Secure` e `HttpOnly`.
- Limite de tentativas de login no Nginx (20/min por IP) **e** no DRF (10/min).
- O isolamento entre lojas tem teste dedicado em
  `backend/tests/test_isolamento_tenant.py`. **Todo endpoint novo entra lá.**
