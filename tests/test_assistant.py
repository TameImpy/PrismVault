import os
from unittest.mock import patch, MagicMock

import json

from src.assistant import load_knowledge_base, build_category_summary, search_segments, chat, chat_stream


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


def test_search_segments_sources_from_canonical_segments_csv():
    """Chat and brief share data/segments.csv, so reach never contradicts.

    "Baking Fans" is a Permutive segment whose reach in the canonical file is
    2,282,660; the Assistant must return that same figure and a platform tag.
    """
    results = search_segments("Baking Fans")
    match = [r for r in results if r["name"] == "Baking Fans"]
    assert match, "expected the canonical 'Baking Fans' segment"
    row = match[0]
    assert str(row["size"]) == "2282660"
    assert row["platform"] == "Permutive"


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


@patch("src.assistant.OpenAI")
def test_chat_stream_yields_content_and_done_events(mock_openai_cls):
    """chat_stream() should yield content events and a final done event."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    # Simulate streaming chunks
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "Hello"
    chunk1.choices[0].delta.tool_calls = None

    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = " world"
    chunk2.choices[0].delta.tool_calls = None

    chunk3 = MagicMock()
    chunk3.choices = [MagicMock()]
    chunk3.choices[0].delta.content = None
    chunk3.choices[0].delta.tool_calls = None

    mock_client.chat.completions.create.return_value = iter([chunk1, chunk2, chunk3])

    messages = [{"role": "user", "content": "Hi"}]
    events = list(chat_stream(messages))

    # Should have content events and a done event
    content_events = [e for e in events if e["type"] == "content"]
    done_events = [e for e in events if e["type"] == "done"]

    assert len(content_events) == 2
    assert content_events[0]["text"] == "Hello"
    assert content_events[1]["text"] == " world"
    assert len(done_events) == 1


@patch("src.assistant.OpenAI")
def test_chat_stream_yields_status_during_tool_call(mock_openai_cls):
    """chat_stream() should yield a status event when executing a tool call."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    # First stream: model requests a tool call (no content)
    tc_chunk1 = MagicMock()
    tc_chunk1.choices = [MagicMock()]
    tc_chunk1.choices[0].delta.content = None
    tc_delta = MagicMock()
    tc_delta.id = "call_123"
    tc_delta.function.name = "search_segments"
    tc_delta.function.arguments = '{"query": "pet"}'
    tc_chunk1.choices[0].delta.tool_calls = [tc_delta]

    # Second stream: follow-up response after tool execution
    result_chunk = MagicMock()
    result_chunk.choices = [MagicMock()]
    result_chunk.choices[0].delta.content = "We have pet segments."
    result_chunk.choices[0].delta.tool_calls = None

    mock_client.chat.completions.create.side_effect = [
        iter([tc_chunk1]),    # first call triggers tool
        iter([result_chunk]),  # second call with tool results
    ]

    messages = [{"role": "user", "content": "What pet segments do you have?"}]
    events = list(chat_stream(messages))

    types = [e["type"] for e in events]
    assert "status" in types
    status_event = [e for e in events if e["type"] == "status"][0]
    assert "Searching" in status_event["message"]

    content_events = [e for e in events if e["type"] == "content"]
    assert len(content_events) >= 1
    assert content_events[0]["text"] == "We have pet segments."


@patch("src.assistant.OpenAI")
def test_assistant_chat_stream_endpoint_returns_sse(mock_openai_cls):
    """POST /api/assistant/chat/stream should return text/event-stream."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta.content = "Hello"
    chunk.choices[0].delta.tool_calls = None

    chunk_end = MagicMock()
    chunk_end.choices = [MagicMock()]
    chunk_end.choices[0].delta.content = None
    chunk_end.choices[0].delta.tool_calls = None

    mock_client.chat.completions.create.return_value = iter([chunk, chunk_end])

    client = TestClient(app)
    client.post("/api/auth/signup", json={
        "email": "stream@test.com",
        "name": "Test",
        "password": "testpass123",
    })
    response = client.post(
        "/api/assistant/chat/stream",
        json={"messages": [{"role": "user", "content": "Hi"}]},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Parse SSE events from the response body
    lines = response.text.strip().split("\n")
    data_lines = [l for l in lines if l.startswith("data: ")]
    events = [json.loads(l[6:]) for l in data_lines]

    types = [e["type"] for e in events]
    assert "content" in types
    assert "done" in types
