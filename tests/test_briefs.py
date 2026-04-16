"""Tests for brief persistence and team library."""
import asyncio
import json
import sys
import os

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient
from api import database as db_module
from api.database import save_brief, create_user
from api.main import app


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def _fresh_db(db_url):
    yield


def _make_user(email="test@example.com", name="Test User"):
    return _run(create_user(email, name, "hashedpw"))


def test_save_brief_stores_and_returns_brief():
    user = _make_user()
    result_json = json.dumps({"content": "Test brief content", "sources": []})

    brief = _run(save_brief(
        user_id=user["id"],
        topic="Travel",
        advertiser="Airwaves",
        kpi="Brand Awareness",
        client_brief="",
        result_json=result_json,
    ))

    assert brief["id"] is not None
    assert brief["user_id"] == user["id"]
    assert brief["topic"] == "Travel"
    assert brief["advertiser"] == "Airwaves"
    assert brief["kpi"] == "Brand Awareness"
    assert brief["created_at"] is not None


@patch("api.main.generate_insights")
def test_insights_endpoint_auto_saves_brief(mock_gen):
    mock_gen.return_value = {"content": "Test output", "sources": []}

    client = TestClient(app)
    client.post("/api/auth/signup", json={
        "email": "autosave@test.com",
        "name": "Auto Save",
        "password": "testpass123",
    })
    response = client.post("/api/insights", json={
        "topic": "Sustainability",
        "advertiser": "Unilever",
        "kpi": "Reach",
    })
    assert response.status_code == 200

    # Check the brief was saved by querying the database directly
    me = client.get("/api/me").json()
    rows = _run(db_module.database.fetch_all(
        "SELECT topic, advertiser FROM briefs WHERE user_id = :uid",
        {"uid": me["id"]},
    ))
    assert len(rows) == 1
    assert rows[0]._mapping["advertiser"] == "Unilever"
    assert rows[0]._mapping["topic"] == "Sustainability"
