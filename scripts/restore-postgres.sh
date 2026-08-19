#!/bin/sh
# Restore a plain-text pg_dump into the production Compose Postgres.
# Stop the API first so nothing writes during restore.
# Usage:
#   docker compose -f docker-compose.prod.yml stop backend
#   ./scripts/restore-postgres.sh pacelab-YYYYMMDD.sql
#   docker compose -f docker-compose.prod.yml start backend
set -eu

if [ "${1:-}" = "" ]; then
  echo "usage: $0 <dump.sql>" >&2
  exit 1
fi

DUMP_FILE=$1
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
POSTGRES_USER="${POSTGRES_USER:-pacelab}"
POSTGRES_DB="${POSTGRES_DB:-pacelab}"

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" \
  -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};" \
  -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};"

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 < "$DUMP_FILE"
