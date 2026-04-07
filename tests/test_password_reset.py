"""
Tests for password reset: email utility, forgot-password, and reset-password endpoints.
"""
import sys
import os
import asyncio

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import patch
from api.email_utils import send_email


def test_send_email_logs_when_smtp_not_configured(capsys):
    """When SMTP is not configured, send_email logs the email content and doesn't crash."""
    for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        os.environ.pop(key, None)

    send_email("user@example.com", "Reset your password", "<p>Click here</p>")

    captured = capsys.readouterr()
    assert "user@example.com" in captured.out
    assert "Reset your password" in captured.out


@patch("api.email_utils.smtplib")
def test_send_email_sends_when_smtp_configured(mock_smtplib):
    """When SMTP is configured, send_email connects and sends."""
    mock_server = mock_smtplib.SMTP.return_value.__enter__.return_value

    with patch.dict(os.environ, {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "user",
        "SMTP_PASSWORD": "pass",
    }):
        send_email("to@example.com", "Subject", "<p>Body</p>")

    mock_smtplib.SMTP.assert_called_once_with("smtp.example.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user", "pass")
    mock_server.sendmail.assert_called_once()


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient
from api.main import app
from api.database import get_user_by_email


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def api_client(db_url):
    """TestClient backed by the db_url fixture for test isolation."""
    # Ensure SMTP is not configured for tests
    for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        os.environ.pop(key, None)

    yield TestClient(app)


def _signup(client, email="reset@example.com", password="password123"):
    """Sign up a user and return the client."""
    client.post(
        "/api/auth/signup",
        json={"email": email, "name": "Test User", "password": password},
    )
    return client


def test_forgot_password_returns_200_for_existing_email(api_client):
    """POST /api/auth/forgot-password returns 200 for a known email."""
    _signup(api_client)
    resp = api_client.post(
        "/api/auth/forgot-password",
        json={"email": "reset@example.com"},
    )
    assert resp.status_code == 200
    assert "reset link" in resp.json()["detail"].lower()


def test_forgot_password_returns_200_for_nonexistent_email(api_client):
    """POST /api/auth/forgot-password returns 200 even for unknown email (no enumeration)."""
    resp = api_client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 200


def test_reset_password_full_roundtrip(api_client):
    """User can request a reset token and use it to change their password, then log in."""
    _signup(api_client, "roundtrip@example.com", "oldpassword1")

    # Generate a reset token directly (simulating what forgot-password does)
    from api.auth import _create_reset_token
    user = run(get_user_by_email("roundtrip@example.com"))
    token = _create_reset_token(user["id"])

    # Reset password
    resp = api_client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": "newpassword1"},
    )
    assert resp.status_code == 200

    # Log in with new password
    resp = api_client.post(
        "/api/auth/login",
        json={"email": "roundtrip@example.com", "password": "newpassword1"},
    )
    assert resp.status_code == 200

    # Old password no longer works
    resp = api_client.post(
        "/api/auth/login",
        json={"email": "roundtrip@example.com", "password": "oldpassword1"},
    )
    assert resp.status_code == 401


def test_reset_password_with_expired_token(api_client):
    """POST /api/auth/reset-password with expired token returns 400."""
    _signup(api_client)
    from jose import jwt as jose_jwt
    from datetime import datetime, timedelta
    import config

    # Create an already-expired token
    expired_token = jose_jwt.encode(
        {"sub": "1", "exp": datetime.utcnow() - timedelta(hours=1), "purpose": "password_reset"},
        config.JWT_SECRET,
        algorithm="HS256",
    )
    resp = api_client.post(
        "/api/auth/reset-password",
        json={"token": expired_token, "password": "newpassword1"},
    )
    assert resp.status_code == 400


def test_reset_password_with_wrong_purpose(api_client):
    """A regular auth JWT (no purpose claim) cannot be used as a reset token."""
    _signup(api_client)
    from api.auth import _create_token
    auth_token = _create_token(1)  # Regular auth token, no purpose claim

    resp = api_client.post(
        "/api/auth/reset-password",
        json={"token": auth_token, "password": "newpassword1"},
    )
    assert resp.status_code == 400


def test_reset_password_with_invalid_token(api_client):
    """POST /api/auth/reset-password with garbage token returns 400."""
    resp = api_client.post(
        "/api/auth/reset-password",
        json={"token": "garbage.invalid.token", "password": "newpassword1"},
    )
    assert resp.status_code == 400


def test_reset_password_with_short_password(api_client):
    """POST /api/auth/reset-password with password < 8 chars returns 422."""
    _signup(api_client)
    from api.auth import _create_reset_token
    token = _create_reset_token(1)

    resp = api_client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": "short"},
    )
    assert resp.status_code == 422
