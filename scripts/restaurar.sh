#!/usr/bin/env bash
#
# Restaura um backup no banco de produção.
#
# DESTRUTIVO: sobrescreve os dados atuais. Exige confirmação explícita.
#
# Uso: ./restaurar.sh /opt/vape-backups/vape_prod_20260915_030000.sql.gz
set -euo pipefail

ARQUIVO="${1:-}"
ENV_PROD="/opt/vape-project/deploy/env/producao.env"

if [[ -z "$ARQUIVO" || ! -f "$ARQUIVO" ]]; then
  echo "Uso: $0 <arquivo.sql.gz>" >&2
  echo "Backups disponíveis:" >&2
  ls -1 /opt/vape-backups/*.sql.gz 2>/dev/null >&2 || echo "  (nenhum)" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a; source "$ENV_PROD"; set +a

echo "ATENÇÃO: isto substitui TODOS os dados de produção pelo conteúdo de:"
echo "  $ARQUIVO"
read -rp "Digite RESTAURAR para confirmar: " confirmacao
[[ "$confirmacao" == "RESTAURAR" ]] || { echo "Cancelado."; exit 1; }

echo "Parando o backend para evitar escrita durante a restauração…"
systemctl stop vape-backend

gunzip -c "$ARQUIVO" | psql "$DATABASE_URL"

echo "Subindo o backend…"
systemctl start vape-backend
echo "Restauração concluída."
