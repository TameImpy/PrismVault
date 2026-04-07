#!/bin/sh
set -e

echo "=== Environment ==="
echo "PORT=${PORT:-not set}"
echo "DATABASE_URL is set: $([ -n "$DATABASE_URL" ] && echo yes || echo no)"

echo "=== Running migrations ==="
python scripts/migrate.py

echo "=== Starting uvicorn on port ${PORT:-8000} ==="
exec python -m uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level info
