"""Railway entrypoint — runs migrations then starts uvicorn."""
import os
import sys
import asyncio
import traceback
import uvicorn

print("=== Prism Plan Entrypoint ===")
print("PORT=%s" % os.environ.get("PORT", "not set"))
print("DATABASE_URL set: %s" % bool(os.environ.get("DATABASE_URL")))
print("JWT_SECRET set: %s" % bool(os.environ.get("JWT_SECRET")))

# Run migrations in a single async context
print("Running migrations...")
try:
    async def migrate():
        from api.database import connect, disconnect, init_db
        await connect()
        await init_db()
        await disconnect()
    asyncio.run(migrate())
    print("Migrations complete.")
except Exception:
    print("Migration failed:")
    traceback.print_exc()
    sys.exit(1)

# Start uvicorn — it manages its own event loop and calls
# connect()/init_db() again via the FastAPI lifespan handler
port = int(os.environ.get("PORT", "8000"))
print("Starting uvicorn on port %d..." % port)
uvicorn.run("api.main:app", host="0.0.0.0", port=port, log_level="info")
