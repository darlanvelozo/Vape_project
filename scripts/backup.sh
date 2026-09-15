#!/usr/bin/env bash
#
# Backup diário do banco de produção.
#
# Guarda dumps comprimidos por 14 dias. O dump é feito com --clean, para que a
# restauração recrie os objetos sem exigir banco vazio.
#
# Uso: ./backup.sh            (backup)
#      ./backup.sh --listar   (lista os backups existentes)
set -euo pipefail

DESTINO="/opt/vape-backups"
DIAS_RETENCAO=14
ENV_PROD="/opt/vape-project/deploy/env/producao.env"

if [[ "${1:-}" == "--listar" ]]; then
  ls -lh "$DESTINO" 2>/dev/null || echo "Nenhum backup ainda."
  exit 0
fi

# shellcheck disable=SC1090
set -a; source "$ENV_PROD"; set +a

mkdir -p "$DESTINO"
chmod 700 "$DESTINO"

ARQUIVO="$DESTINO/vape_prod_$(date +%Y%m%d_%H%M%S).sql.gz"

# A senha vem do DATABASE_URL, que já está no ambiente; pg_dump aceita a URL
# inteira, o que evita espalhar a senha por variáveis soltas.
pg_dump --clean --if-exists --no-owner --no-privileges "$DATABASE_URL" | gzip -9 > "$ARQUIVO"

TAMANHO=$(du -h "$ARQUIVO" | cut -f1)
echo "Backup concluído: $ARQUIVO ($TAMANHO)"

# Backup vazio é pior que nenhum: falha ruidosamente.
if [[ $(stat -c%s "$ARQUIVO") -lt 10240 ]]; then
  echo "ERRO: o dump saiu pequeno demais ($TAMANHO). Verifique o banco." >&2
  exit 1
fi

REMOVIDOS=$(find "$DESTINO" -name 'vape_prod_*.sql.gz' -mtime +$DIAS_RETENCAO -print -delete | wc -l)
[[ "$REMOVIDOS" -gt 0 ]] && echo "$REMOVIDOS backup(s) antigo(s) removido(s)."

echo "Backups guardados: $(find "$DESTINO" -name 'vape_prod_*.sql.gz' | wc -l)"
