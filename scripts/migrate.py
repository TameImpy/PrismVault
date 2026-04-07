"""
Standalone migration script. Creates all database tables.
Run before starting the app: python scripts/migrate.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.database import connect, disconnect, init_db


async def main():
    print("Connecting to database...")
    await connect()
    print("Creating tables...")
    await init_db()
    print("Done.")
    await disconnect()


if __name__ == "__main__":
    asyncio.run(main())
