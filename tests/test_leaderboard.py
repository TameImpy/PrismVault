"""
Tests for the leaderboard API endpoints at /api/leaderboard.

Uses FastAPI's TestClient. Each test gets a fresh SQLite database via the
db_url fixture to ensure isolation.
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
    """Return a TestClient backed by a fresh database."""
    return TestClient(app)


def _post_score(client, name="Alice", score=5000, lines=40, level=4):
    return client.post(
        "/api/leaderboard",
        json={"player_name": name, "score": score, "lines": lines, "level": level},
    )


# ---------------------------------------------------------------------------
# POST /api/leaderboard — create a score
# ---------------------------------------------------------------------------


def test_post_leaderboard_returns_201(client):
    """POST /api/leaderboard returns 201 when a valid score is submitted."""
    response = _post_score(client)
    assert response.status_code == 201


def test_post_leaderboard_returns_entry_with_rank(client):
    """POST /api/leaderboard response includes the submitted fields and a rank."""
    data = _post_score(client, "Bob", 3000, 25, 2).json()
    assert data["player_name"] == "Bob"
    assert data["score"] == 3000
    assert data["lines"] == 25
    assert data["level"] == 2
    assert data["rank"] == 1


# ---------------------------------------------------------------------------
# GET /api/leaderboard — retrieve scores
# ---------------------------------------------------------------------------


def test_get_leaderboard_returns_top_10_sorted_by_score(client):
    """GET /api/leaderboard returns entries sorted by score descending."""
    _post_score(client, "Low", 1000, 10, 1)
    _post_score(client, "High", 9000, 80, 9)
    _post_score(client, "Mid", 5000, 40, 4)
    data = client.get("/api/leaderboard").json()
    names = [e["player_name"] for e in data["top_10"]]
    assert names == ["High", "Mid", "Low"]


def test_get_leaderboard_limits_to_10_entries(client):
    """GET /api/leaderboard returns at most 10 entries even when more exist."""
    for i in range(15):
        _post_score(client, "Player%d" % i, i * 100, i, 1)
    data = client.get("/api/leaderboard").json()
    assert len(data["top_10"]) == 10


def test_get_leaderboard_returns_empty_when_no_scores(client):
    """GET /api/leaderboard returns empty top_10 when no scores exist."""
    data = client.get("/api/leaderboard").json()
    assert data["top_10"] == []
    assert data["total_players"] == 0


def test_get_leaderboard_includes_player_rank_outside_top_10(client):
    """GET /api/leaderboard?player_name=X shows rank when player is outside top 10."""
    # Create 11 players, "Last" has the lowest score
    for i in range(11):
        _post_score(client, "Top%d" % i, (i + 2) * 1000, 10, 1)
    _post_score(client, "Last", 500, 5, 1)
    data = client.get("/api/leaderboard", params={"player_name": "Last"}).json()
    assert len(data["top_10"]) == 10
    assert data["player_rank"] == 12


def test_get_leaderboard_player_rank_null_when_not_provided(client):
    """GET /api/leaderboard without player_name returns null for player_rank."""
    _post_score(client, "Alice", 5000, 40, 4)
    data = client.get("/api/leaderboard").json()
    assert data["player_rank"] is None


def test_get_leaderboard_handles_ties(client):
    """Players with the same score get the same rank."""
    _post_score(client, "A", 5000, 40, 4)
    _post_score(client, "B", 5000, 40, 4)
    _post_score(client, "C", 3000, 20, 2)
    data = client.get("/api/leaderboard").json()
    ranks = {e["player_name"]: e["rank"] for e in data["top_10"]}
    assert ranks["A"] == 1
    assert ranks["B"] == 1
    assert ranks["C"] == 3


# ---------------------------------------------------------------------------
# POST /api/leaderboard — validation
# ---------------------------------------------------------------------------


def test_post_leaderboard_rejects_empty_name(client):
    """POST /api/leaderboard returns 422 when player_name is empty."""
    response = _post_score(client, name="", score=1000, lines=10, level=1)
    assert response.status_code == 422


def test_post_leaderboard_rejects_whitespace_only_name(client):
    """POST /api/leaderboard returns 422 when player_name is whitespace only."""
    response = _post_score(client, name="   ", score=1000, lines=10, level=1)
    assert response.status_code == 422


def test_post_leaderboard_rejects_negative_score(client):
    """POST /api/leaderboard returns 422 when score is negative."""
    response = _post_score(client, name="Alice", score=-100, lines=10, level=1)
    assert response.status_code == 422
