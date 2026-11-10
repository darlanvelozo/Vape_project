#!/usr/bin/env bash
#
# Publica a versão atual do código em produção.
#
# Ordem importa: migrar antes de trocar o frontend evita que a SPA nova chame
# um endpoint que ainda não existe.
set -euo pipefail

RAIZ="/opt/vape-project"
ENV_PROD="$RAIZ/deploy/env/producao.env"

cd "$RAIZ"

echo "==> 1/6 Backup preventivo"
"$RAIZ/scripts/backup.sh"

echo "==> 2/6 Dependências do backend"
"$RAIZ/backend/.venv/bin/pip" install -q -r "$RAIZ/backend/requirements.txt"

echo "==> 3/6 Testes"
( cd "$RAIZ/backend" && .venv/bin/python -m pytest tests/ -q -p no:warnings )

echo "==> 4/6 Migrações e estáticos"
cd "$RAIZ/backend"
set -a; source "$ENV_PROD"; set +a
export DJANGO_SETTINGS_MODULE=config.settings.prod
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy

# Pastas onde o serviço (usuário vape) grava arquivo enviado. O deploy roda
# como root: sem isto, pasta nova nasce de root e o upload dá erro 500.
install -d -o vape -g vape -m 755 "$RAIZ/backend/media"
install -d -o vape -g vape -m 750 "$RAIZ/backend/privado"

echo "==> 5/6 Frontend"
cd "$RAIZ/frontend"
npm ci --silent
npm run build
chown -R vape:vape "$RAIZ/frontend/dist"

echo "==> 6/6 Reiniciando serviços"
systemctl restart vape-backend
nginx -t && systemctl reload nginx

sleep 3
if systemctl is-active --quiet vape-backend; then
  echo "Deploy concluído. Backend ativo."
else
  echo "ERRO: o backend não subiu. Veja: journalctl -u vape-backend -n 50" >&2
  exit 1
fi
