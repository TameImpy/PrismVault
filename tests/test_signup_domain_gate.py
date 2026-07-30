"""
Tests for the signup email-domain allowlist at api/auth.py.

Signup is restricted to config.ALLOWED_EMAIL_DOMAINS so that only colleagues
can create accounts. The allowlist is read at call time, so these tests set it
explicitly rather than relying on the deployed default.
"""
import sys
import os

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from fastapi.testclient import TestClient

import config
from api.main import app
from api.database import get_user_by_email


@pytest.fixture()
def client(db_url):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def gated(monkeypatch):
    """Restrict signup to a single domain."""
    monkeypatch.setattr(config, "ALLOWED_EMAIL_DOMAINS", ["immediate.co.uk"])


def _signup(client, email):
    return client.post(
        "/api/auth/signup",
        json={"email": email, "name": "QA User", "password": "password123"},
    )


# ---------------------------------------------------------------------------
# Allowed
# ---------------------------------------------------------------------------


def test_allowed_domain_can_sign_up(client, gated):
    response = _signup(client, "colleague@immediate.co.uk")
    assert response.status_code == 200
    assert "access_token" in response.cookies


def test_allowed_domain_is_case_insensitive(client, gated):
    response = _signup(client, "Colleague@Immediate.CO.UK")
    assert response.status_code == 200


def test_empty_allowlist_permits_any_domain(client, monkeypatch):
    monkeypatch.setattr(config, "ALLOWED_EMAIL_DOMAINS", [])
    assert _signup(client, "anyone@gmail.com").status_code == 200


def test_multiple_allowed_domains_are_all_accepted(client, monkeypatch):
    monkeypatch.setattr(
        config, "ALLOWED_EMAIL_DOMAINS", ["immediate.co.uk", "radiotimes.com"]
    )
    assert _signup(client, "a@immediate.co.uk").status_code == 200
    assert _signup(client, "b@radiotimes.com").status_code == 200


# ---------------------------------------------------------------------------
# Blocked
# ---------------------------------------------------------------------------


def test_outside_domain_is_rejected_with_403(client, gated):
    response = _signup(client, "stranger@gmail.com")
    assert response.status_code == 403
    assert "@immediate.co.uk" in response.json()["detail"]


def test_lookalike_domain_is_rejected(client, gated):
    """A domain that merely ends with the allowed one must not pass."""
    assert _signup(client, "attacker@not-immediate.co.uk").status_code == 403


def test_subdomain_suffix_trick_is_rejected(client, gated):
    """immediate.co.uk appearing left of the real domain must not pass."""
    assert _signup(client, "attacker@immediate.co.uk.evil.com").status_code == 403


def test_domain_in_local_part_is_rejected(client, gated):
    """The check must use the domain, not a substring of the whole address."""
    assert _signup(client, "immediate.co.uk@gmail.com").status_code == 403


def test_rejected_signup_creates_no_user(client, gated, db_url):
    import asyncio

    _signup(client, "stranger@gmail.com")
    user = asyncio.get_event_loop().run_until_complete(
        get_user_by_email("stranger@gmail.com")
    )
    assert user is None


def test_rejected_signup_sets_no_cookie(client, gated):
    response = _signup(client, "stranger@gmail.com")
    assert "access_token" not in response.cookies


def test_multiple_domain_message_lists_all(client, monkeypatch):
    monkeypatch.setattr(
        config, "ALLOWED_EMAIL_DOMAINS", ["immediate.co.uk", "radiotimes.com"]
    )
    detail = _signup(client, "stranger@gmail.com").json()["detail"]
    assert "@immediate.co.uk" in detail
    assert "@radiotimes.com" in detail


# ---------------------------------------------------------------------------
# Scope of the gate
# ---------------------------------------------------------------------------


def test_login_is_not_gated_for_existing_accounts(client, monkeypatch):
    """The allowlist guards account creation only. An account that already
    exists keeps working if the allowlist later changes — deliberate, so that
    tightening the list cannot lock out established users silently."""
    monkeypatch.setattr(config, "ALLOWED_EMAIL_DOMAINS", [])
    assert _signup(client, "legacy@gmail.com").status_code == 200
    client.post("/api/auth/logout")

    monkeypatch.setattr(config, "ALLOWED_EMAIL_DOMAINS", ["immediate.co.uk"])
    response = client.post(
        "/api/auth/login",
        json={"email": "legacy@gmail.com", "password": "password123"},
    )
    assert response.status_code == 200
