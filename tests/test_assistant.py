import os
from unittest.mock import patch, MagicMock

from src.assistant import load_knowledge_base, build_category_summary, search_segments, chat


def test_load_knowledge_base_returns_content_with_key_sections():
    content = load_knowledge_base()
    assert len(content) > 0
    assert "Prism" in content
    assert "Permutive" in content
    assert "Audience Project" in content
    assert "SLA" in content or "Service-Level" in content
    assert "FAQ" in content or "Frequently Asked" in content


def test_build_category_summary_contains_categories_and_counts():
    summary = build_category_summary()
    assert len(summary) > 0
    # Should contain at least some known categories from the CSV
    assert "Demographics" in summary
    assert "Food & Drink" in summary or "Arts & Entertainment" in summary
    # Should contain numbers (segment counts)
    import re
    assert re.search(r"\d+", summary), "Summary should contain numeric counts"


def test_search_segments_finds_by_query():
    results = search_segments("pet")
    assert len(results) > 0
    # All results should mention "pet" in name or description
    for r in results:
        combined = (r["name"] + " " + r["description"]).lower()
        assert "pet" in combined


def test_search_segments_filters_by_category():
    results = search_segments("", category="Food & Drink")
    assert len(results) > 0
    for r in results:
        assert "Food & Drink" in r["category"]


def test_search_segments_respects_max_results():
    # Empty query with no category matches everything — should cap at max_results
    results = search_segments("", max_results=5)
    assert len(results) == 5


@patch("src.assistant.OpenAI")
def test_chat_returns_assistant_response(mock_openai_cls):
    """chat() should return the assistant's response content."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    # Mock a simple response (no tool calls)
    mock_choice = MagicMock()
    mock_choice.message.content = "Prism is our first-party data proposition."
    mock_choice.message.tool_calls = None
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    messages = [{"role": "user", "content": "What is Prism?"}]
    result = chat(messages)

    assert result["role"] == "assistant"
    assert result["content"] == "Prism is our first-party data proposition."
    # Verify system prompt was included
    call_args = mock_client.chat.completions.create.call_args
    sent_messages = call_args[1]["messages"]
    assert sent_messages[0]["role"] == "system"
    assert "Prism" in sent_messages[0]["content"]


# --- API endpoint tests ---

import sys
_project_root = os.path.join(os.path.dirname(__file__), "..")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi.testclient import TestClient
from api.main import app
import pytest


@pytest.fixture(autouse=True)
def _fresh_db(db_url):
    yield


def test_assistant_chat_returns_401_without_auth():
    client = TestClient(app)
    response = client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "What is Prism?"}]},
    )
    assert response.status_code == 401


@patch("src.assistant.OpenAI")
def test_assistant_chat_returns_200_with_auth(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = "Prism is our data proposition."
    mock_choice.message.tool_calls = None
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    client = TestClient(app)
    # Sign up to get auth cookie
    client.post("/api/auth/signup", json={
        "email": "assistant@test.com",
        "name": "Test",
        "password": "testpass123",
    })
    response = client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "What is Prism?"}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert data["content"] == "Prism is our data proposition."
