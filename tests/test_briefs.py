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
from api.database import (
    save_brief, create_user, get_user_briefs, get_all_briefs,
    get_brief_by_id, delete_brief,
)
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


def test_get_user_briefs_returns_only_own_briefs():
    user1 = _make_user("user1@test.com", "User One")
    user2 = _make_user("user2@test.com", "User Two")
    result = json.dumps({"content": "test"})

    _run(save_brief(user1["id"], "Topic A", "Brand A", "KPI A", "", result))
    _run(save_brief(user2["id"], "Topic B", "Brand B", "KPI B", "", result))
    _run(save_brief(user1["id"], "Topic C", "Brand C", "KPI C", "", result))

    briefs = _run(get_user_briefs(user1["id"]))
    assert len(briefs) == 2
    assert all(b["user_id"] == user1["id"] for b in briefs)
    # Should not include result_json (lightweight list)
    assert "result_json" not in briefs[0]
    # Most recent first
    assert briefs[0]["topic"] == "Topic C"


def test_get_brief_by_id_returns_full_brief_with_result_json():
    user = _make_user()
    result = json.dumps({"content": "Full content", "sources": [{"editor": "Sarah"}]})
    saved = _run(save_brief(user["id"], "Health", "Diageo", "CTR", "Brief text", result))

    brief = _run(get_brief_by_id(saved["id"]))
    assert brief is not None
    assert brief["topic"] == "Health"
    assert brief["result_json"] is not None
    parsed = json.loads(brief["result_json"])
    assert parsed["content"] == "Full content"
    assert brief["author_name"] == user["name"]


def test_get_all_briefs_returns_all_with_author_names():
    user1 = _make_user("all1@test.com", "Alice")
    user2 = _make_user("all2@test.com", "Bob")
    result = json.dumps({"content": "test"})

    _run(save_brief(user1["id"], "T1", "B1", "K1", "", result))
    _run(save_brief(user2["id"], "T2", "B2", "K2", "", result))

    briefs = _run(get_all_briefs())
    assert len(briefs) == 2
    names = {b["author_name"] for b in briefs}
    assert "Alice" in names
    assert "Bob" in names
    assert "result_json" not in briefs[0]


def test_delete_brief_only_deletes_if_owned():
    user1 = _make_user("del1@test.com", "Owner")
    user2 = _make_user("del2@test.com", "Other")
    result = json.dumps({"content": "test"})
    saved = _run(save_brief(user1["id"], "T", "B", "K", "", result))

    # Other user cannot delete
    assert _run(delete_brief(saved["id"], user2["id"])) is False
    # Owner can delete
    assert _run(delete_brief(saved["id"], user1["id"])) is True
    # Verify it's gone
    assert _run(get_brief_by_id(saved["id"])) is None


# --- API endpoint tests ---


def _signup_and_get_client(email="api@test.com", name="API User"):
    client = TestClient(app)
    client.post("/api/auth/signup", json={
        "email": email, "name": name, "password": "testpass123",
    })
    return client


def test_api_get_briefs_requires_auth():
    client = TestClient(app)
    assert client.get("/api/briefs").status_code == 401


@patch("api.main.generate_insights")
def test_api_get_briefs_mine_returns_own_briefs(mock_gen):
    mock_gen.return_value = {"content": "test"}
    client = _signup_and_get_client()

    # Generate a brief (auto-saved)
    client.post("/api/insights", json={
        "topic": "Food", "advertiser": "Tesco", "kpi": "Reach",
    })

    response = client.get("/api/briefs?scope=mine")
    assert response.status_code == 200
    briefs = response.json()
    assert len(briefs) == 1
    assert briefs[0]["advertiser"] == "Tesco"
    assert "result_json" not in briefs[0]


def test_api_get_brief_by_id_returns_full_brief():
    client = _signup_and_get_client("detail@test.com")
    user = _make_user("detaildb@test.com", "Detail")
    result = json.dumps({"content": "Full detail"})
    saved = _run(save_brief(user["id"], "T", "B", "K", "", result))

    response = client.get("/api/briefs/%d" % saved["id"])
    assert response.status_code == 200
    data = response.json()
    assert data["result_json"] is not None
    assert data["author_name"] is not None


@patch("api.main.generate_insights")
def test_api_get_briefs_team_returns_all_briefs(mock_gen):
    mock_gen.return_value = {"content": "test"}

    client1 = _signup_and_get_client("team1@test.com", "Alice")
    client2 = _signup_and_get_client("team2@test.com", "Bob")

    client1.post("/api/insights", json={
        "topic": "Cars", "advertiser": "BMW", "kpi": "Clicks",
    })
    client2.post("/api/insights", json={
        "topic": "Travel", "advertiser": "BA", "kpi": "Reach",
    })

    response = client1.get("/api/briefs?scope=team")
    assert response.status_code == 200
    briefs = response.json()
    assert len(briefs) == 2
    names = {b["author_name"] for b in briefs}
    assert "Alice" in names
    assert "Bob" in names


def test_api_delete_brief_only_own():
    client1 = _signup_and_get_client("delapi1@test.com", "Owner")
    client2 = _signup_and_get_client("delapi2@test.com", "Other")

    me1 = client1.get("/api/me").json()
    result = json.dumps({"content": "test"})
    saved = _run(save_brief(me1["id"], "T", "B", "K", "", result))

    # Other user gets 404
    assert client2.delete("/api/briefs/%d" % saved["id"]).status_code == 404
    # Owner succeeds
    assert client1.delete("/api/briefs/%d" % saved["id"]).status_code == 200
