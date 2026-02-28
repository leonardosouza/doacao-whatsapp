#!/bin/bash
# Conecta ao banco de produção com fuso horário de São Paulo.
# Todos os campos timestamptz são exibidos automaticamente em horário SP (UTC-3).
#
# Uso: ./scripts/psql-production.sh [args extras do psql]
# Exemplos:
#   ./scripts/psql-production.sh
#   ./scripts/psql-production.sh -c "SELECT * FROM v_messages_sp LIMIT 10;"

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env.production"

if [[ -f "$ENV_FILE" ]]; then
    DATABASE_URL=$(grep -E '^DATABASE_URL=' "$ENV_FILE" | cut -d'=' -f2-)
fi

if [[ -z "$DATABASE_URL" ]]; then
    echo "Erro: DATABASE_URL não encontrada em $ENV_FILE"
    exit 1
fi

echo "Conectando ao banco de produção (TZ: America/Sao_Paulo)..."
PGOPTIONS="-c timezone=America/Sao_Paulo" psql "$DATABASE_URL" "$@"
