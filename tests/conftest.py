"""
Shared test fixtures for database-dependent tests.

Sets config.DATABASE_URL to a temp SQLite file, then calls connect()
which creates the database instance. Restores after.
"""
import asyncio
import os
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def db_url(tmp_path):
    """Provide a fresh SQLite database URL and swap the database module to use it."""
    import config
    import api.database as db_module

    db_path = str(tmp_path / "test.db")
    url = "sqlite+aiosqlite:///%s" % db_path

    old_url = config.DATABASE_URL
    old_db = db_module.database

    # Set URL before connect() — connect() reads config.DATABASE_URL
    config.DATABASE_URL = url
    _run(db_module.connect())
    _run(db_module.init_db())

    yield url

    try:
        _run(db_module.disconnect())
    except Exception:
        pass
    config.DATABASE_URL = old_url
    db_module.database = old_db
