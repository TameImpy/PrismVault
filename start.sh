#!/bin/sh

echo "=== PORT is: ${PORT:-not set} ==="
echo "=== Running migrations ==="
python scripts/migrate.py
echo "=== Migration done, testing import ==="
python -c "
import traceback
try:
    import api.main
    print('Import OK')
except Exception:
    traceback.print_exc()
    exit(1)
"
echo "=== Starting uvicorn ==="
python -m uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level info
