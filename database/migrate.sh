#!/usr/bin/env bash
set -euo pipefail

# Resolve the directory this script lives in
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Database connection - defaults match docker-compose.yml
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-cys}"
DB_USER="${POSTGRES_USER:-cys}"

export PGPASSWORD="${POSTGRES_PASSWORD:-cys_dev}"

PSQL="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -v ON_ERROR_STOP=1"

# Migration tracking table
$PSQL -q <<'SQL'
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SQL

# Run each migration in order, skipping already-applied ones
for file in "$SCRIPT_DIR"/migrations/*.sql; do
    filename="$(basename "$file")"
    already_applied=$($PSQL -t -A -c "SELECT COUNT(*) FROM schema_migrations WHERE filename = '$filename'")
    if [ "$already_applied" -eq 0 ]; then
        echo "Applying $filename..."
        $PSQL -q -f "$file"
        $PSQL -q -c "INSERT INTO schema_migrations (filename) VALUES ('$filename')"
    else
        echo "Skipping $filename (already applied)"
    fi
done

echo "Migrations complete."
