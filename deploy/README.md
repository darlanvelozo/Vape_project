# Deploy

Produção prevista na mesma VPS dos demais projetos: Nginx (reverse proxy +
estáticos do frontend), gunicorn via systemd, PostgreSQL 16 e Redis locais.

- `nginx/` — site config (a criar no Bloco 6)
- `systemd/` — unit do backend (a criar no Bloco 6)
- `env.production.example` — variáveis de produção (a criar no Bloco 6)
