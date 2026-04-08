"""Railway entrypoint — runs migrations then starts uvicorn."""
import os
import sys
import traceback
import uvicorn

print("=== Prism Plan Entrypoint ===")
print("PORT=%s" % os.environ.get("PORT", "not set"))
print("DATABASE_URL set: %s" % bool(os.environ.get("DATABASE_URL")))
print("JWT_SECRET set: %s" % bool(os.environ.get("JWT_SECRET")))

# Run migrations
print("Running migrations...")
try:
    import asyncio
    from api.database import connect, disconnect, init_db
    asyncio.run(connect())
    asyncio.run(init_db())
    asyncio.run(disconnect())
    print("Migrations complete.")
except Exception:
    print("Migration failed:")
    traceback.print_exc()
    sys.exit(1)

# Start uvicorn
port = int(os.environ.get("PORT", "8000"))
print("Starting uvicorn on port %d..." % port)
try:
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, log_level="info")
except Exception:
    print("Uvicorn failed:")
    traceback.print_exc()
    sys.exit(1)
