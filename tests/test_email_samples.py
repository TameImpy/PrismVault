"""
Tests for email samples CRUD — database functions and API endpoints.

Uses a real SQLite database per test. No mocks.
"""
import sys
import os
import asyncio

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from api.database import create_user, create_email_sample, get_email_samples, delete_email_sample


def run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_user(email="alice@immediate.co.uk"):
    """Helper to create a user and return the user dict."""
    return run(create_user(email, "Alice", "hashed_pw"))


# ---------------------------------------------------------------------------
# Database: create and retrieve
# ---------------------------------------------------------------------------


def test_create_sample_and_retrieve(db_url):
    """A created email sample can be retrieved for that user."""
    user = _make_user()
    sample = run(create_email_sample(user["id"], "Hi, I wanted to reach out about..."))
    assert sample["content"] == "Hi, I wanted to reach out about..."
    assert sample["user_id"] == user["id"]
    assert "id" in sample
    assert "created_at" in sample

    samples = run(get_email_samples(user["id"]))
    assert len(samples) == 1
    assert samples[0]["content"] == "Hi, I wanted to reach out about..."


def test_samples_isolated_per_user(db_url):
    """Each user can only see their own samples."""
    alice = _make_user("alice@immediate.co.uk")
    bob = _make_user("bob@immediate.co.uk")
    run(create_email_sample(alice["id"], "Alice's email"))
    run(create_email_sample(bob["id"], "Bob's email"))

    alice_samples = run(get_email_samples(alice["id"]))
    bob_samples = run(get_email_samples(bob["id"]))
    assert len(alice_samples) == 1
    assert alice_samples[0]["content"] == "Alice's email"
    assert len(bob_samples) == 1
    assert bob_samples[0]["content"] == "Bob's email"


def test_max_5_samples_enforced(db_url):
    """Creating a 6th sample raises ValueError."""
    user = _make_user()
    for i in range(5):
        run(create_email_sample(user["id"], "Sample %d" % i))
    with pytest.raises(ValueError, match="Maximum"):
        run(create_email_sample(user["id"], "One too many"))


def test_delete_own_sample(db_url):
    """A user can delete their own sample."""
    user = _make_user()
    sample = run(create_email_sample(user["id"], "Delete me"))
    deleted = run(delete_email_sample(sample["id"], user["id"]))
    assert deleted is True
    assert len(run(get_email_samples(user["id"]))) == 0


def test_cannot_delete_other_users_sample(db_url):
    """Deleting another user's sample returns False and leaves it intact."""
    alice = _make_user("alice@immediate.co.uk")
    bob = _make_user("bob@immediate.co.uk")
    sample = run(create_email_sample(alice["id"], "Alice's email"))

    deleted = run(delete_email_sample(sample["id"], bob["id"]))
    assert deleted is False
    assert len(run(get_email_samples(alice["id"]))) == 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture()
def api_client(db_url):
    """TestClient backed by the db_url fixture for test isolation."""
    yield TestClient(app)


def _signup(client, email="test@immediate.co.uk"):
    """Helper to sign up a user. Returns the client (cookies persist)."""
    client.post(
        "/api/auth/signup",
        json={"email": email, "name": "Test User", "password": "password123"},
    )
    return client


def test_api_get_samples_returns_401_without_auth(api_client):
    """GET /api/email-samples without auth returns 401."""
    resp = TestClient(app, cookies={}).get("/api/email-samples")
    assert resp.status_code == 401


def test_api_full_crud_lifecycle(api_client):
    """Create, list, and delete a sample through the API."""
    _signup(api_client)

    # Create
    resp = api_client.post("/api/email-samples", json={"content": "Hello, I'd love to discuss..."})
    assert resp.status_code == 201
    sample = resp.json()
    assert sample["content"] == "Hello, I'd love to discuss..."
    sample_id = sample["id"]

    # List
    resp = api_client.get("/api/email-samples")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Delete
    resp = api_client.delete("/api/email-samples/%d" % sample_id)
    assert resp.status_code == 200

    # Verify empty
    resp = api_client.get("/api/email-samples")
    assert len(resp.json()) == 0


def test_api_post_rejects_empty_content(api_client):
    """POST /api/email-samples with empty content returns 422."""
    _signup(api_client)
    resp = api_client.post("/api/email-samples", json={"content": "   "})
    assert resp.status_code == 422


def test_api_post_rejects_at_max_capacity(api_client):
    """POST /api/email-samples returns 409 when user already has 5 samples."""
    _signup(api_client)
    for i in range(5):
        resp = api_client.post("/api/email-samples", json={"content": "Sample %d" % i})
        assert resp.status_code == 201
    resp = api_client.post("/api/email-samples", json={"content": "Sixth"})
    assert resp.status_code == 409


def test_api_delete_returns_404_for_other_users_sample(api_client):
    """DELETE /api/email-samples/{id} returns 404 for another user's sample."""
    # User A creates a sample
    _signup(api_client, "alice@immediate.co.uk")
    resp = api_client.post("/api/email-samples", json={"content": "Alice's email"})
    alice_sample_id = resp.json()["id"]

    # Sign up as User B (new cookies)
    api_client.post(
        "/api/auth/signup",
        json={"email": "bob@immediate.co.uk", "name": "Bob", "password": "password123"},
    )
    # Try to delete Alice's sample as Bob
    resp = api_client.delete("/api/email-samples/%d" % alice_sample_id)
    assert resp.status_code == 404
