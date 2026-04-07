"""Entrypoint script for Railway deployment."""
import os
import sys
import subprocess
import traceback

print("=== Starting Prism Plan ===", flush=True)

# Run migrations
print("Running migrations...", flush=True)
try:
    subprocess.run([sys.executable, "scripts/migrate.py"], check=True)
    print("Migrations complete.", flush=True)
except Exception as e:
    print("Migration failed: %s" % e, flush=True)
    traceback.print_exc()
    sys.exit(1)

# Test import
print("Testing imports...", flush=True)
try:
    import api.main
    print("Imports OK.", flush=True)
except Exception as e:
    print("Import failed: %s" % e, flush=True)
    traceback.print_exc()
    sys.exit(1)

# Start uvicorn
port = os.environ.get("PORT", "8000")
print("Starting uvicorn on port %s..." % port, flush=True)
os.execvp(sys.executable, [
    sys.executable, "-m", "uvicorn",
    "api.main:app",
    "--host", "0.0.0.0",
    "--port", port,
])
