"""
Shared test fixtures for database-dependent tests.

Swaps the database module's shared `database` instance to point at a
temporary SQLite file before each test, then restores it after.
"""
import asyncio
import os
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from databases import Database


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def db_url(tmp_path):
    """Provide a fresh SQLite database URL and swap the database module to use it.

    Usage: add `db_url` to any test or fixture that needs a clean database.
    The api.database module is patched for the duration of the test.
    """
    import config
    import api.database as db_module

    db_path = str(tmp_path / "test.db")
    url = "sqlite+aiosqlite:///%s" % db_path

    old_url = config.DATABASE_URL
    old_db = db_module.database
    config.DATABASE_URL = url
    db_module.database = Database(url)

    _run(db_module.connect())
    _run(db_module.init_db())

    yield url

    _run(db_module.disconnect())
    config.DATABASE_URL = old_url
    db_module.database = old_db
