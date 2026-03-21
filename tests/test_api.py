"""
Tests for the FastAPI backend at api/main.py.

Uses FastAPI's TestClient (backed by httpx/starlette) so no real server is
needed. generate_insights and config.OPENAI_API_KEY are mocked throughout so
no external services are called.
"""
import sys
import os

# Ensure the project root is on sys.path before importing api.main, mirroring
# the path manipulation inside api/main.py itself.
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import patch

from fastapi.testclient import TestClient

# Import the app *after* the sys.path fix so that `config` and `src.*` resolve.
from api.main import app


# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

MOCK_INSIGHTS_RESULT = {
    "content": "This is the synthesised brief.",
    "sources": [
        {"editor": "Jane Smith", "publication": "Vogue", "date": "2025-01-01"}
    ],
    "research_skills": [
        {
            "skill_name": "Company Overview",
            "raw_results": [],
            "processed_summary": "Brand summary here.",
            "error": None,
        }
    ],
    "audience_timing": "Peak month: March. Top segment: 25-34.",
    "google_trends": "Rising queries: organic skincare.",
}


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def test_health_returns_200():
    """GET /api/health should return HTTP 200."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_ok_body():
    """GET /api/health body should be exactly {"status": "ok"}."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Insights endpoint — happy path
# ---------------------------------------------------------------------------


def test_insights_returns_200_with_valid_payload():
    """POST /api/insights returns 200 when key is present and generate_insights succeeds."""
    client = TestClient(app)
    with patch("api.main.config") as mock_config, \
         patch("api.main.generate_insights", return_value=MOCK_INSIGHTS_RESULT) as mock_gen:
        mock_config.OPENAI_API_KEY = "sk-test-key"
        response = client.post(
            "/api/insights",
            json={
                "topic": "sustainable fashion",
                "advertiser": "EcoWear",
                "include_google_trends": True,
            },
        )
    assert response.status_code == 200


def test_insights_response_body_matches_generate_insights_return_value():
    """POST /api/insights returns the dict produced by generate_insights unchanged."""
    client = TestClient(app)
    with patch("api.main.config") as mock_config, \
         patch("api.main.generate_insights", return_value=MOCK_INSIGHTS_RESULT):
        mock_config.OPENAI_API_KEY = "sk-test-key"
        response = client.post(
            "/api/insights",
            json={
                "topic": "sustainable fashion",
                "advertiser": "EcoWear",
                "include_google_trends": True,
            },
        )
    assert response.json() == MOCK_INSIGHTS_RESULT


def test_insights_passes_correct_arguments_to_generate_insights():
    """POST /api/insights forwards topic, advertiser, and include_google_trends to generate_insights."""
    client = TestClient(app)
    with patch("api.main.config") as mock_config, \
         patch("api.main.generate_insights", return_value=MOCK_INSIGHTS_RESULT) as mock_gen:
        mock_config.OPENAI_API_KEY = "sk-test-key"
        client.post(
            "/api/insights",
            json={
                "topic": "gut health",
                "advertiser": "NutriCo",
                "include_google_trends": False,
            },
        )
    mock_gen.assert_called_once_with(
        topic="gut health",
        advertiser="NutriCo",
        include_google_trends=False,
    )


def test_insights_include_google_trends_defaults_to_true():
    """POST /api/insights uses include_google_trends=True when the field is omitted."""
    client = TestClient(app)
    with patch("api.main.config") as mock_config, \
         patch("api.main.generate_insights", return_value=MOCK_INSIGHTS_RESULT) as mock_gen:
        mock_config.OPENAI_API_KEY = "sk-test-key"
        client.post(
            "/api/insights",
            json={"topic": "travel", "advertiser": "Airwaves"},
        )
    mock_gen.assert_called_once_with(
        topic="travel",
        advertiser="Airwaves",
        include_google_trends=True,
    )


# ---------------------------------------------------------------------------
# Insights endpoint — missing API key
# ---------------------------------------------------------------------------


def test_insights_returns_500_when_api_key_is_empty_string():
    """POST /api/insights returns 500 when OPENAI_API_KEY is an empty string."""
    client = TestClient(app)
    with patch("api.main.config") as mock_config, \
         patch("api.main.generate_insights", return_value=MOCK_INSIGHTS_RESULT):
        mock_config.OPENAI_API_KEY = ""
        response = client.post(
            "/api/insights",
            json={"topic": "travel", "advertiser": "Airwaves"},
        )
    assert response.status_code == 500


def test_insights_error_detail_mentions_api_key_when_missing():
    """POST /api/insights error detail names OPENAI_API_KEY when the key is absent."""
    client = TestClient(app)
    with patch("api.main.config") as mock_config, \
         patch("api.main.generate_insights", return_value=MOCK_INSIGHTS_RESULT):
        mock_config.OPENAI_API_KEY = ""
        response = client.post(
            "/api/insights",
            json={"topic": "travel", "advertiser": "Airwaves"},
        )
    assert "OPENAI_API_KEY" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Insights endpoint — generate_insights raises an exception
# ---------------------------------------------------------------------------


def test_insights_returns_500_when_generate_insights_raises():
    """POST /api/insights returns 500 when generate_insights raises any exception."""
    client = TestClient(app)
    with patch("api.main.config") as mock_config, \
         patch("api.main.generate_insights", side_effect=RuntimeError("ChromaDB unavailable")):
        mock_config.OPENAI_API_KEY = "sk-test-key"
        response = client.post(
            "/api/insights",
            json={"topic": "skincare", "advertiser": "GlowCo"},
        )
    assert response.status_code == 500


def test_insights_error_detail_contains_exception_message():
    """POST /api/insights propagates the exception message in the error detail."""
    client = TestClient(app)
    with patch("api.main.config") as mock_config, \
         patch("api.main.generate_insights", side_effect=RuntimeError("ChromaDB unavailable")):
        mock_config.OPENAI_API_KEY = "sk-test-key"
        response = client.post(
            "/api/insights",
            json={"topic": "skincare", "advertiser": "GlowCo"},
        )
    assert "ChromaDB unavailable" in response.json()["detail"]


def test_insights_returns_500_when_generate_insights_raises_value_error():
    """POST /api/insights returns 500 for ValueError as well as RuntimeError."""
    client = TestClient(app)
    with patch("api.main.config") as mock_config, \
         patch("api.main.generate_insights", side_effect=ValueError("bad input")):
        mock_config.OPENAI_API_KEY = "sk-test-key"
        response = client.post(
            "/api/insights",
            json={"topic": "skincare", "advertiser": "GlowCo"},
        )
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# Request validation — Pydantic / FastAPI 422 responses
# ---------------------------------------------------------------------------


def test_insights_returns_422_when_topic_is_missing():
    """POST /api/insights returns 422 when required field `topic` is absent."""
    client = TestClient(app)
    response = client.post(
        "/api/insights",
        json={"advertiser": "BrandX"},
    )
    assert response.status_code == 422


def test_insights_returns_422_when_advertiser_is_missing():
    """POST /api/insights returns 422 when required field `advertiser` is absent."""
    client = TestClient(app)
    response = client.post(
        "/api/insights",
        json={"topic": "wellness"},
    )
    assert response.status_code == 422


def test_insights_returns_422_when_body_is_empty():
    """POST /api/insights returns 422 when the request body is an empty object."""
    client = TestClient(app)
    response = client.post("/api/insights", json={})
    assert response.status_code == 422


def test_insights_returns_422_when_body_is_absent():
    """POST /api/insights returns 422 when no request body is sent at all."""
    client = TestClient(app)
    response = client.post("/api/insights")
    assert response.status_code == 422
