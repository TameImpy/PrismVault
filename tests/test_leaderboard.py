"""
Tests for the leaderboard API endpoints at /api/leaderboard.

Uses FastAPI's TestClient. Each test gets a fresh in-memory SQLite database
to ensure isolation.
"""
import sys
import os
import tempfile

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app


def _make_client():
    """Return (TestClient, tmp_path) backed by a fresh temp SQLite file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    patcher = patch("api.main.LEADERBOARD_DB", tmp.name)
    patcher.start()
    client = TestClient(app)
    return client, tmp.name, patcher


def _cleanup(tmp_path, patcher):
    patcher.stop()
    os.unlink(tmp_path)


def _post_score(client, name="Alice", score=5000, lines=40, level=4):
    return client.post(
        "/api/leaderboard",
        json={"player_name": name, "score": score, "lines": lines, "level": level},
    )


# ---------------------------------------------------------------------------
# POST /api/leaderboard — create a score
# ---------------------------------------------------------------------------


def test_post_leaderboard_returns_201():
    """POST /api/leaderboard returns 201 when a valid score is submitted."""
    client, tmp, p = _make_client()
    try:
        response = _post_score(client)
        assert response.status_code == 201
    finally:
        _cleanup(tmp, p)


def test_post_leaderboard_returns_entry_with_rank():
    """POST /api/leaderboard response includes the submitted fields and a rank."""
    client, tmp, p = _make_client()
    try:
        data = _post_score(client, "Bob", 3000, 25, 2).json()
        assert data["player_name"] == "Bob"
        assert data["score"] == 3000
        assert data["lines"] == 25
        assert data["level"] == 2
        assert data["rank"] == 1
    finally:
        _cleanup(tmp, p)


# ---------------------------------------------------------------------------
# GET /api/leaderboard — retrieve scores
# ---------------------------------------------------------------------------


def test_get_leaderboard_returns_top_10_sorted_by_score():
    """GET /api/leaderboard returns entries sorted by score descending."""
    client, tmp, p = _make_client()
    try:
        _post_score(client, "Low", 1000, 10, 1)
        _post_score(client, "High", 9000, 80, 9)
        _post_score(client, "Mid", 5000, 40, 4)
        data = client.get("/api/leaderboard").json()
        names = [e["player_name"] for e in data["top_10"]]
        assert names == ["High", "Mid", "Low"]
    finally:
        _cleanup(tmp, p)


def test_get_leaderboard_limits_to_10_entries():
    """GET /api/leaderboard returns at most 10 entries even when more exist."""
    client, tmp, p = _make_client()
    try:
        for i in range(15):
            _post_score(client, "Player%d" % i, i * 100, i, 1)
        data = client.get("/api/leaderboard").json()
        assert len(data["top_10"]) == 10
    finally:
        _cleanup(tmp, p)


def test_get_leaderboard_returns_empty_when_no_scores():
    """GET /api/leaderboard returns empty top_10 when no scores exist."""
    client, tmp, p = _make_client()
    try:
        data = client.get("/api/leaderboard").json()
        assert data["top_10"] == []
        assert data["total_players"] == 0
    finally:
        _cleanup(tmp, p)


def test_get_leaderboard_includes_player_rank_outside_top_10():
    """GET /api/leaderboard?player_name=X shows rank when player is outside top 10."""
    client, tmp, p = _make_client()
    try:
        # Create 11 players, "Last" has the lowest score
        for i in range(11):
            _post_score(client, "Top%d" % i, (i + 2) * 1000, 10, 1)
        _post_score(client, "Last", 500, 5, 1)
        data = client.get("/api/leaderboard", params={"player_name": "Last"}).json()
        assert len(data["top_10"]) == 10
        assert data["player_rank"] == 12
    finally:
        _cleanup(tmp, p)


def test_get_leaderboard_player_rank_null_when_not_provided():
    """GET /api/leaderboard without player_name returns null for player_rank."""
    client, tmp, p = _make_client()
    try:
        _post_score(client, "Alice", 5000, 40, 4)
        data = client.get("/api/leaderboard").json()
        assert data["player_rank"] is None
    finally:
        _cleanup(tmp, p)


def test_get_leaderboard_handles_ties():
    """Players with the same score get the same rank."""
    client, tmp, p = _make_client()
    try:
        _post_score(client, "A", 5000, 40, 4)
        _post_score(client, "B", 5000, 40, 4)
        _post_score(client, "C", 3000, 20, 2)
        data = client.get("/api/leaderboard").json()
        ranks = {e["player_name"]: e["rank"] for e in data["top_10"]}
        assert ranks["A"] == 1
        assert ranks["B"] == 1
        assert ranks["C"] == 3
    finally:
        _cleanup(tmp, p)


# ---------------------------------------------------------------------------
# POST /api/leaderboard — validation
# ---------------------------------------------------------------------------


def test_post_leaderboard_rejects_empty_name():
    """POST /api/leaderboard returns 422 when player_name is empty."""
    client, tmp, p = _make_client()
    try:
        response = _post_score(client, name="", score=1000, lines=10, level=1)
        assert response.status_code == 422
    finally:
        _cleanup(tmp, p)


def test_post_leaderboard_rejects_whitespace_only_name():
    """POST /api/leaderboard returns 422 when player_name is whitespace only."""
    client, tmp, p = _make_client()
    try:
        response = _post_score(client, name="   ", score=1000, lines=10, level=1)
        assert response.status_code == 422
    finally:
        _cleanup(tmp, p)


def test_post_leaderboard_rejects_negative_score():
    """POST /api/leaderboard returns 422 when score is negative."""
    client, tmp, p = _make_client()
    try:
        response = _post_score(client, name="Alice", score=-100, lines=10, level=1)
        assert response.status_code == 422
    finally:
        _cleanup(tmp, p)
