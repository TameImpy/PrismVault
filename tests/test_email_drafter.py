"""
Tests for the email drafter module at src/email_drafter.py.

Uses a mocked OpenAI client — no real API calls.
"""
import sys
import os

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import patch, MagicMock
from src.email_drafter import draft_email


def _mock_openai_response(content):
    """Create a mock OpenAI chat completion response."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@patch("src.email_drafter.OpenAI")
def test_draft_email_returns_subject_and_body(mock_openai_cls):
    """draft_email() returns a dict with 'subject' and 'body' keys."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        "Subject: Partnership opportunity with Yakult\n\n"
        "Hi [Name],\n\n"
        "I wanted to reach out about an exciting alignment between gut health content "
        "and Yakult's brand positioning.\n\n"
        "Best regards"
    )

    result = draft_email(
        brief_content="## Key Recommendations\n1. Align with gut health editorial...",
        topic="gut health",
        advertiser="Yakult",
        kpi="Awareness",
        writing_samples=[],
    )

    assert "subject" in result
    assert "body" in result
    assert "Yakult" in result["subject"]
    assert "[Name]" in result["body"]


@patch("src.email_drafter.OpenAI")
def test_draft_email_uses_gpt4o_mini(mock_openai_cls):
    """draft_email() calls GPT-4o-mini, not GPT-4o."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        "Subject: Test\n\nBody text"
    )

    draft_email("brief", "topic", "advertiser", "Awareness", [])

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"


@patch("src.email_drafter.OpenAI")
def test_prompt_includes_advertiser_topic_kpi(mock_openai_cls):
    """The user prompt sent to the LLM contains the advertiser, topic, and KPI."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        "Subject: Test\n\nBody"
    )

    draft_email("some brief content", "gut health", "Yakult", "Viewability", [])

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    messages = call_kwargs["messages"]
    user_msg = messages[1]["content"]
    assert "Yakult" in user_msg
    assert "gut health" in user_msg
    assert "Viewability" in user_msg
    assert "some brief content" in user_msg


@patch("src.email_drafter.OpenAI")
def test_style_section_included_when_samples_provided(mock_openai_cls):
    """When writing samples are provided, they appear in the system prompt."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        "Subject: Test\n\nBody"
    )

    draft_email("brief", "topic", "adv", "Awareness", ["Hey Sarah, great catching up..."])

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    system_msg = call_kwargs["messages"][0]["content"]
    assert "Hey Sarah, great catching up..." in system_msg
    assert "Match their writing style" in system_msg


@patch("src.email_drafter.OpenAI")
def test_style_section_omitted_when_no_samples(mock_openai_cls):
    """When no writing samples are provided, the style section is not in the prompt."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        "Subject: Test\n\nBody"
    )

    draft_email("brief", "topic", "adv", "Awareness", [])

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    system_msg = call_kwargs["messages"][0]["content"]
    assert "Match their writing style" not in system_msg


def test_parse_email_handles_no_subject():
    """If the LLM doesn't include a Subject: line, subject is empty and body has the full text."""
    from src.email_drafter import _parse_email
    result = _parse_email("Hi [Name],\n\nGreat to connect.\n\nBest")
    assert result["subject"] == ""
    assert result["body"].startswith("Hi [Name],")


# ---------------------------------------------------------------------------
# Provenance (#156) — the email quotes the brief's figures, so it has to carry
# the same account of where they came from.
# ---------------------------------------------------------------------------

PROVENANCE = [
    {"section": "Audience Segments & Reach", "source": "data/segments.csv",
     "as_at": "2026-07-21", "coverage": "Whole network",
     "period": "Rolling 90 days", "cadence": "On request"},
    {"section": "Recommended Products", "source": "The central benchmarking sheet",
     "as_at": "2026-07-20", "coverage": "Whole network",
     "period": "Rolling 12 months", "cadence": "Monthly"},
]


def _draft_with(mock_openai_cls, provenance):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        "Subject: Baking season\n\nHi [Name],\n\n2.3m readers browse baking weekly.\n\nBest"
    )
    return draft_email(
        brief_content="## Key Recommendations\n1. Lead with baking.",
        topic="baking", advertiser="Homepride", kpi="Awareness",
        provenance=provenance,
    ), mock_client


@patch("src.email_drafter.OpenAI")
def test_draft_email_footers_the_body_with_its_sources(mock_openai_cls):
    result, _ = _draft_with(mock_openai_cls, PROVENANCE)

    for entry in PROVENANCE:
        assert entry["section"] in result["body"]
        assert entry["source"] in result["body"]
        assert entry["as_at"] in result["body"]
        assert entry["coverage"] in result["body"]
        assert entry["period"] in result["body"]
    # The pitch itself is untouched — the sources sit beneath it.
    assert result["body"].startswith("Hi [Name],")
    assert result["subject"] == "Baking season"


@patch("src.email_drafter.OpenAI")
def test_the_source_footer_never_passes_through_the_model(mock_openai_cls):
    """A provenance line that a copywriting prompt could reword is worth
    nothing — it is appended verbatim, and the model is never shown it."""
    _, mock_client = _draft_with(mock_openai_cls, PROVENANCE)

    sent = "".join(
        m["content"] for m in
        mock_client.chat.completions.create.call_args[1]["messages"]
    )
    assert "data/segments.csv" not in sent


@patch("src.email_drafter.OpenAI")
def test_draft_email_without_provenance_is_unchanged(mock_openai_cls):
    """An older client posting no provenance gets the plain draft, no footer."""
    result, _ = _draft_with(mock_openai_cls, None)

    assert result["body"] == "Hi [Name],\n\n2.3m readers browse baking weekly.\n\nBest"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture()
def api_client(db_url):
    """TestClient backed by the db_url fixture for test isolation."""
    yield TestClient(app)


def test_api_draft_email_returns_401_without_auth(api_client):
    """POST /api/draft-email without auth returns 401."""
    resp = TestClient(app, cookies={}).post(
        "/api/draft-email",
        json={"content": "brief", "topic": "t", "advertiser": "a", "kpi": "k"},
    )
    assert resp.status_code == 401


@patch("api.main.draft_email")
def test_api_draft_email_rejects_a_malformed_provenance_shape(mock_draft, api_client):
    """Provenance entries are read with `.get()` downstream, so a list of
    strings has to be refused at the edge as a 422 rather than becoming an
    AttributeError and a 500 (the shape LESSONS_LEARNED flags for #164)."""
    mock_draft.return_value = {"subject": "s", "body": "b"}
    api_client.post(
        "/api/auth/signup",
        json={"email": "shape@immediate.co.uk", "name": "Test", "password": "password123"},
    )
    resp = api_client.post(
        "/api/draft-email",
        json={"content": "b", "topic": "t", "advertiser": "a", "kpi": "k",
              "provenance": ["not an entry"]},
    )
    assert resp.status_code == 422
    mock_draft.assert_not_called()


@patch("api.main.draft_email")
def test_api_draft_email_passes_provenance_through_as_plain_dicts(mock_draft, api_client):
    """The drafter reads dicts, not pydantic models."""
    mock_draft.return_value = {"subject": "s", "body": "b"}
    api_client.post(
        "/api/auth/signup",
        json={"email": "pass@immediate.co.uk", "name": "Test", "password": "password123"},
    )
    resp = api_client.post(
        "/api/draft-email",
        json={"content": "b", "topic": "t", "advertiser": "a", "kpi": "k",
              "provenance": [PROVENANCE[0]]},
    )
    assert resp.status_code == 200
    passed = mock_draft.call_args[1]["provenance"]
    assert passed == [PROVENANCE[0]]


@patch("api.main.draft_email")
def test_api_draft_email_returns_subject_and_body(mock_draft, api_client):
    """POST /api/draft-email with auth returns subject and body from drafter."""
    mock_draft.return_value = {"subject": "Test Subject", "body": "Test body"}

    api_client.post(
        "/api/auth/signup",
        json={"email": "test@immediate.co.uk", "name": "Test", "password": "password123"},
    )
    resp = api_client.post(
        "/api/draft-email",
        json={"content": "brief content", "topic": "gut health", "advertiser": "Yakult", "kpi": "Awareness"},
    )
    assert resp.status_code == 200
    assert resp.json()["subject"] == "Test Subject"
    assert resp.json()["body"] == "Test body"
