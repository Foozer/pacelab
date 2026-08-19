#!/bin/sh
set -eu

# node_modules is a named volume, so it survives image rebuilds and goes stale
# whenever package.json changes. Reconcile it before starting Vite.
echo "Syncing node_modules with package.json..."
if ! npm install --no-audit --no-fund; then
    echo "WARNING: npm install failed. Continuing with the existing node_modules." >&2
fi

exec "$@"
