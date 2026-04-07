"""
Tests for the auth endpoints at api/auth.py.

Uses FastAPI TestClient with a real SQLite database via the databases library.
"""
import sys
import os

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture()
def client(db_url):
    """Create a TestClient with the database already connected."""
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


def test_signup_returns_200_and_sets_cookie(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "alice@example.com", "name": "Alice", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
    assert response.json()["name"] == "Alice"
    assert "id" in response.json()
    assert "access_token" in response.cookies


def test_signup_duplicate_email_returns_409(client):
    client.post(
        "/api/auth/signup",
        json={"email": "dup@example.com", "name": "First", "password": "password123"},
    )
    response = client.post(
        "/api/auth/signup",
        json={"email": "dup@example.com", "name": "Second", "password": "password456"},
    )
    assert response.status_code == 409


def test_signup_short_password_returns_422(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "short@example.com", "name": "Short", "password": "abc"},
    )
    assert response.status_code == 422


def test_signup_missing_fields_returns_422(client):
    response = client.post("/api/auth/signup", json={"email": "only@example.com"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def _create_test_user(client):
    return client.post(
        "/api/auth/signup",
        json={"email": "login@example.com", "name": "Login User", "password": "password123"},
    )


def test_login_returns_200_and_sets_cookie(client):
    _create_test_user(client)
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "login@example.com"
    assert "access_token" in response.cookies


def test_login_wrong_password_returns_401(client):
    _create_test_user(client)
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_email_returns_401(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------


def test_me_with_valid_cookie_returns_user(client):
    client.post(
        "/api/auth/signup",
        json={"email": "me@example.com", "name": "Me User", "password": "password123"},
    )
    response = client.get("/api/me")
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
    assert response.json()["name"] == "Me User"


def test_me_without_cookie_returns_401(db_url):
    client = TestClient(app, cookies={})
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_with_invalid_token_returns_401(db_url):
    client = TestClient(app, cookies={"access_token": "invalid.token.here"})
    response = client.get("/api/me")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


def test_logout_clears_cookie(client):
    client.post(
        "/api/auth/signup",
        json={"email": "logout@example.com", "name": "Logout", "password": "password123"},
    )
    assert client.get("/api/me").status_code == 200
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert client.get("/api/me").status_code == 401
