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
