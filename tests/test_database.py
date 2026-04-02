"""
Tests for the user database module at api/database.py.

Uses a real in-memory SQLite database — no mocks. Each test gets a fresh
database via init_db() so tests are isolated.
"""
import sys
import os
import asyncio

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from api.database import init_db, create_user, get_user_by_email, get_user_by_id


def run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Initialise a fresh in-memory database for each test."""
    db_path = str(tmp_path / "test_users.db")
    run(init_db(db_path))
    yield db_path


def test_created_user_is_retrievable_by_email(fresh_db):
    """A user created with create_user can be retrieved by email."""
    run(create_user("alice@example.com", "Alice Smith", "hashed_pw_123", fresh_db))
    user = run(get_user_by_email("alice@example.com", fresh_db))
    assert user is not None
    assert user["email"] == "alice@example.com"
    assert user["name"] == "Alice Smith"


def test_created_user_is_retrievable_by_id(fresh_db):
    """A user created with create_user can be retrieved by ID."""
    created = run(create_user("bob@example.com", "Bob Jones", "hashed_pw_456", fresh_db))
    user = run(get_user_by_id(created["id"], fresh_db))
    assert user is not None
    assert user["email"] == "bob@example.com"
    assert user["name"] == "Bob Jones"


def test_created_user_has_id_and_created_at(fresh_db):
    """create_user returns a dict with an auto-assigned id and created_at."""
    created = run(create_user("carol@example.com", "Carol", "hashed_pw_789", fresh_db))
    assert isinstance(created["id"], int)
    assert created["id"] > 0
    assert created["created_at"] is not None


def test_duplicate_email_raises_error(fresh_db):
    """Creating two users with the same email raises an error."""
    run(create_user("dup@example.com", "First", "hashed_1", fresh_db))
    with pytest.raises(Exception):
        run(create_user("dup@example.com", "Second", "hashed_2", fresh_db))


def test_get_user_by_email_returns_none_for_nonexistent(fresh_db):
    """get_user_by_email returns None when the email does not exist."""
    user = run(get_user_by_email("nobody@example.com", fresh_db))
    assert user is None


def test_get_user_by_id_returns_none_for_nonexistent(fresh_db):
    """get_user_by_id returns None when the ID does not exist."""
    user = run(get_user_by_id(9999, fresh_db))
    assert user is None
