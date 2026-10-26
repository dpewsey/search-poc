#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-cys}"
DB_USER="${POSTGRES_USER:-cys}"

export PGPASSWORD="${POSTGRES_PASSWORD:-cys_dev}"

echo "Seeding database..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$SCRIPT_DIR/seed.sql"
echo "Seed complete."
