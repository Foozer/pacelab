#!/bin/sh
set -eu

echo "Running database migrations..."
alembic upgrade head

echo "Starting PaceLab API..."
exec "$@"
