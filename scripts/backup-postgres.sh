#!/bin/sh
# Dump Postgres from the production Compose stack to stdout (gzip on the caller).
# Usage, from the repo root on the VPS:
#   ./scripts/backup-postgres.sh > "pacelab-$(date -u +%Y%m%dT%H%M%SZ).sql"
# Then copy the file off the box.
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
POSTGRES_USER="${POSTGRES_USER:-pacelab}"
POSTGRES_DB="${POSTGRES_DB:-pacelab}"

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" --no-owner --format=plain "$POSTGRES_DB"
