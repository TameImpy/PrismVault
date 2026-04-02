"""
Tests for the auth endpoints at api/auth.py.

Uses FastAPI TestClient with a real in-memory SQLite database.
"""
import sys
import os

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.database import init_db

# Use a temp database for each test module run.
TEST_DB = os.path.join(os.path.dirname(__file__), "test_auth_users.db")


@pytest.fixture(autouse=True)
def fresh_db():
    """Ensure a fresh database for each test."""
    import asyncio
    # Remove any leftover test DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    asyncio.get_event_loop().run_until_complete(init_db(TEST_DB))
    # Patch the auth module to use our test DB
    import api.auth as auth_module
    import api.database as db_module
    original_auth_db = getattr(auth_module, "DB_PATH", None)
    original_db_default = db_module.DEFAULT_DB_PATH
    auth_module.DB_PATH = TEST_DB
    db_module.DEFAULT_DB_PATH = TEST_DB
    yield
    auth_module.DB_PATH = original_auth_db
    db_module.DEFAULT_DB_PATH = original_db_default
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


def test_signup_returns_200_and_sets_cookie():
    """POST /api/auth/signup with valid data returns 200 and sets an auth cookie."""
    client = TestClient(app)
    response = client.post(
        "/api/auth/signup",
        json={"email": "alice@example.com", "name": "Alice", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
    assert response.json()["name"] == "Alice"
    assert "id" in response.json()
    # Check cookie was set
    assert "access_token" in response.cookies


def test_signup_duplicate_email_returns_409():
    """POST /api/auth/signup with an existing email returns 409."""
    client = TestClient(app)
    client.post(
        "/api/auth/signup",
        json={"email": "dup@example.com", "name": "First", "password": "password123"},
    )
    response = client.post(
        "/api/auth/signup",
        json={"email": "dup@example.com", "name": "Second", "password": "password456"},
    )
    assert response.status_code == 409


def test_signup_short_password_returns_422():
    """POST /api/auth/signup with password under 8 chars returns 422."""
    client = TestClient(app)
    response = client.post(
        "/api/auth/signup",
        json={"email": "short@example.com", "name": "Short", "password": "abc"},
    )
    assert response.status_code == 422


def test_signup_missing_fields_returns_422():
    """POST /api/auth/signup with missing required fields returns 422."""
    client = TestClient(app)
    response = client.post("/api/auth/signup", json={"email": "only@example.com"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def _create_test_user(client):
    """Helper to create a user and return the response."""
    return client.post(
        "/api/auth/signup",
        json={"email": "login@example.com", "name": "Login User", "password": "password123"},
    )


def test_login_returns_200_and_sets_cookie():
    """POST /api/auth/login with correct credentials returns 200 and sets a cookie."""
    client = TestClient(app)
    _create_test_user(client)
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "login@example.com"
    assert "access_token" in response.cookies


def test_login_wrong_password_returns_401():
    """POST /api/auth/login with wrong password returns 401."""
    client = TestClient(app)
    _create_test_user(client)
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_email_returns_401():
    """POST /api/auth/login with non-existent email returns 401."""
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------


def test_me_with_valid_cookie_returns_user():
    """GET /api/me with a valid auth cookie returns the user info."""
    client = TestClient(app)
    # Signup sets the cookie automatically
    signup_resp = client.post(
        "/api/auth/signup",
        json={"email": "me@example.com", "name": "Me User", "password": "password123"},
    )
    # TestClient persists cookies across requests
    response = client.get("/api/me")
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
    assert response.json()["name"] == "Me User"


def test_me_without_cookie_returns_401():
    """GET /api/me without an auth cookie returns 401."""
    client = TestClient(app, cookies={})
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_with_invalid_token_returns_401():
    """GET /api/me with a tampered/invalid token returns 401."""
    client = TestClient(app, cookies={"access_token": "invalid.token.here"})
    response = client.get("/api/me")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


def test_logout_clears_cookie():
    """POST /api/auth/logout clears the auth cookie so /api/me returns 401."""
    client = TestClient(app)
    # Sign up (sets cookie)
    client.post(
        "/api/auth/signup",
        json={"email": "logout@example.com", "name": "Logout", "password": "password123"},
    )
    # Verify logged in
    assert client.get("/api/me").status_code == 200
    # Logout
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    # Cookie should be cleared — next /api/me should fail
    assert client.get("/api/me").status_code == 401
