#!/usr/bin/env bash
#
# Prepara uma máquina de desenvolvimento do zero.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

echo "==> Variáveis de ambiente"
if [[ ! -f .env ]]; then
  cp .env.example .env
  CHAVE=$(python3 -c "import secrets;print(secrets.token_urlsafe(50))")
  sed -i "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$CHAVE|" .env
  echo "  .env criado com chave nova."
else
  echo "  .env já existe, mantido."
fi

echo "==> Banco e Redis (docker compose)"
docker compose up -d
echo "  aguardando o Postgres aceitar conexões…"
for _ in $(seq 1 30); do
  docker compose exec -T db pg_isready -U vape >/dev/null 2>&1 && break
  sleep 1
done

echo "==> Backend"
cd backend
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python manage.py migrate
echo "  criando dados de demonstração…"
.venv/bin/python manage.py criar_dados_demo --recriar --dias 45 || true

echo "==> Frontend"
cd ../frontend
npm install

cat <<'FIM'

Pronto. Para rodar:

  Terminal 1:  cd backend && .venv/bin/python manage.py runserver
  Terminal 2:  cd frontend && npm run dev

  Sistema ....: http://localhost:5173
  API docs ...: http://localhost:8000/api/docs/
  Login demo .: demo@vapeproject.app / Demo@2026
FIM
