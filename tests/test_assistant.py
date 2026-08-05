import os
from unittest.mock import patch, MagicMock

import json

import pytest

from src.assistant import (
    load_knowledge_base,
    build_category_summary,
    search_segments,
    chat,
    chat_stream,
    _build_system_prompt,
    _latest_user_text,
)
from src.special_categories import SPECIAL_CATEGORY_MESSAGE


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


# --- Special category requests (issue #164) ---


def _tool_call_response(query):
    """A mocked non-streaming response in which the model calls search_segments."""
    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.arguments = json.dumps({"query": query})
    choice = MagicMock()
    choice.message.content = None
    choice.message.tool_calls = [tool_call]
    response = MagicMock()
    response.choices = [choice]
    return response


@patch("src.assistant.OpenAI")
def test_chat_returns_the_special_category_message_without_calling_the_model(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    result = chat([{"role": "user", "content": "Do we have audiences with hearing loss?"}])

    assert result["content"] == SPECIAL_CATEGORY_MESSAGE
    mock_client.chat.completions.create.assert_not_called()


@patch("src.assistant.OpenAI")
def test_special_category_response_is_distinguishable_from_the_generic_fallback(mock_openai_cls):
    """The whole point of #164: the referral must be provably the Article 9 path.

    Today's accidental behaviour also refers the user to the audience team, so a
    test that only checked for a referral would pass against the bug.
    """
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    choice = MagicMock()
    choice.message.content = (
        "I don't have that in the knowledge base — email dl-audience-ads@immediate.co.uk."
    )
    choice.message.tool_calls = None
    response = MagicMock()
    response.choices = [choice]
    mock_client.chat.completions.create.return_value = response

    sensitive = chat([{"role": "user", "content": "audiences by ethnicity please"}])
    generic = chat([{"role": "user", "content": "what is our CPM for video?"}])

    assert sensitive["special_category"] == "racial or ethnic origin"
    assert generic["special_category"] is None


@patch("src.assistant.OpenAI")
def test_chat_blocks_special_category_segments_requested_via_the_tool(mock_openai_cls):
    """A wording the term list misses can still reach the tool — gate it there too."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _tool_call_response("hearing loss")

    result = chat([{"role": "user", "content": "who struggles to follow the telly?"}])

    assert result["content"] == SPECIAL_CATEGORY_MESSAGE
    assert result["special_category"] == "health"
    # No second completion: the tool result never became an answer with segments.
    assert mock_client.chat.completions.create.call_count == 1


@patch("src.assistant.OpenAI")
def test_ordinary_tool_call_still_returns_segments(mock_openai_cls):
    """No over-blocking: an innocent tool query runs the second completion."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    final = MagicMock()
    final.choices = [MagicMock()]
    final.choices[0].message.content = "We have pet segments."
    final.choices[0].message.tool_calls = None
    mock_client.chat.completions.create.side_effect = [
        _tool_call_response("pet"),
        final,
    ]

    result = chat([{"role": "user", "content": "what pet segments do you have?"}])

    assert result["content"] == "We have pet segments."
    assert result["special_category"] is None
    assert mock_client.chat.completions.create.call_count == 2


@patch("src.assistant.OpenAI")
def test_chat_stream_emits_a_special_category_event(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    events = list(chat_stream([{"role": "user", "content": "muslim audiences?"}]))

    flags = [e for e in events if e["type"] == "special_category"]
    assert len(flags) == 1
    assert flags[0]["category"] == "religious or philosophical beliefs"

    text = "".join(e["text"] for e in events if e["type"] == "content")
    assert text == SPECIAL_CATEGORY_MESSAGE
    assert events[-1]["type"] == "done"
    mock_client.chat.completions.create.assert_not_called()


@patch("src.assistant.OpenAI")
def test_chat_stream_blocks_special_category_segments_requested_via_the_tool(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    tc_chunk = MagicMock()
    tc_chunk.choices = [MagicMock()]
    tc_chunk.choices[0].delta.content = None
    tc_delta = MagicMock()
    tc_delta.id = "call_123"
    tc_delta.function.name = "search_segments"
    tc_delta.function.arguments = '{"query": "diabetes"}'
    tc_chunk.choices[0].delta.tool_calls = [tc_delta]

    mock_client.chat.completions.create.return_value = iter([tc_chunk])

    events = list(chat_stream([{"role": "user", "content": "who needs sugar-free?"}]))

    flags = [e for e in events if e["type"] == "special_category"]
    assert [f["category"] for f in flags] == ["health"]
    text = "".join(e["text"] for e in events if e["type"] == "content")
    assert text == SPECIAL_CATEGORY_MESSAGE
    # Only the first completion ran — no follow-up answer built on segments.
    assert mock_client.chat.completions.create.call_count == 1


def test_search_segments_is_not_consulted_for_special_category_queries():
    """Belt and braces: the gate fires before any segment lookup happens."""
    with patch("src.assistant.search_segments") as mock_search, \
            patch("src.assistant.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value = MagicMock()
        mock_openai_cls.return_value.chat.completions.create.return_value = (
            _tool_call_response("ethnicity")
        )
        chat([{"role": "user", "content": "segments for our community campaign"}])
    mock_search.assert_not_called()


def test_system_prompt_carries_the_special_category_rule():
    """Wordings the term list misses still have to land on the same message."""
    prompt = _build_system_prompt()
    assert SPECIAL_CATEGORY_MESSAGE in prompt
    assert "Article 9" in prompt


# --- _latest_user_text: message-shape robustness ---


def test_latest_user_text_returns_empty_string_when_no_user_messages():
    assert _latest_user_text([]) == ""
    assert _latest_user_text([{"role": "assistant", "content": "hi"}]) == ""


def test_latest_user_text_returns_empty_string_for_none_messages():
    """chat()/chat_stream() must not crash before the gate even runs."""
    assert _latest_user_text(None) == ""


def test_latest_user_text_handles_missing_content_key():
    assert _latest_user_text([{"role": "user"}]) == ""


def test_latest_user_text_handles_none_content():
    assert _latest_user_text([{"role": "user", "content": None}]) == ""


def test_latest_user_text_ignores_non_dict_entries():
    """A malformed entry in the list (e.g. a bare string) must not raise."""
    messages = ["not a message", {"role": "user", "content": "hearing loss"}]
    assert _latest_user_text(messages) == "hearing loss"


def test_latest_user_text_finds_the_most_recent_user_turn_across_history():
    messages = [
        {"role": "user", "content": "what is Prism?"},
        {"role": "assistant", "content": "Prism is our data proposition."},
        {"role": "user", "content": "and what about pet owners?"},
    ]
    assert _latest_user_text(messages) == "and what about pet owners?"


# --- Multi-turn conversations: the gate looks only at the latest user turn ---


@patch("src.assistant.OpenAI")
def test_chat_does_not_block_when_only_an_earlier_turn_was_sensitive(mock_openai_cls):
    """No over-blocking: a sensitive word earlier in the conversation must not
    permanently gate every later, unrelated turn."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = "We have several pet segments."
    mock_choice.message.tool_calls = None
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    messages = [
        {"role": "user", "content": "audiences with hearing loss?"},
        {"role": "assistant", "content": SPECIAL_CATEGORY_MESSAGE},
        {"role": "user", "content": "ok, what about pet owners then?"},
    ]
    result = chat(messages)

    assert result["special_category"] is None
    assert result["content"] == "We have several pet segments."
    mock_client.chat.completions.create.assert_called_once()


@patch("src.assistant.OpenAI")
def test_chat_blocks_when_the_latest_turn_turns_sensitive_after_benign_history(mock_openai_cls):
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    messages = [
        {"role": "user", "content": "what is Prism?"},
        {"role": "assistant", "content": "Prism is our first-party data proposition."},
        {"role": "user", "content": "ok, now what about muslim audiences?"},
    ]
    result = chat(messages)

    assert result["special_category"] == "religious or philosophical beliefs"
    assert result["content"] == SPECIAL_CATEGORY_MESSAGE
    mock_client.chat.completions.create.assert_not_called()


@patch("src.assistant.OpenAI")
def test_chat_with_empty_messages_list_does_not_block(mock_openai_cls):
    """No user turn at all -- must fall through to the model, not the gate."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_choice = MagicMock()
    mock_choice.message.content = "How can I help?"
    mock_choice.message.tool_calls = None
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    result = chat([])

    assert result["special_category"] is None
    mock_client.chat.completions.create.assert_called_once()


@patch("src.assistant.OpenAI")
def test_chat_gates_multi_part_message_content(mock_openai_cls):
    """`content` may be a list of parts, not a string — the gate still has to fire.

    `AssistantChatRequest.messages` is an untyped list, so nothing at the API
    layer stops a client sending OpenAI's multi-part shape. A gate that raised on
    it would fail loudly rather than restrict, and a direct caller of chat() would
    get a TypeError instead of the restricted message.
    """
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    messages = [
        {"role": "user", "content": [{"type": "text", "text": "audiences with hearing loss"}]}
    ]
    result = chat(messages)

    assert result["special_category"] == "health"
    assert result["content"] == SPECIAL_CATEGORY_MESSAGE
    mock_client.chat.completions.create.assert_not_called()


# --- Streaming: no segment data leaks through the gate ---


@patch("src.assistant.OpenAI")
def test_chat_stream_emits_no_status_or_extra_events_when_blocked_via_latest_turn(mock_openai_cls):
    """Belt and braces on top of the existing create.assert_not_called(): the event
    stream itself must contain nothing that looks like a segment search was run."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    events = list(chat_stream([{"role": "user", "content": "genetic testing audiences?"}]))

    types = [e["type"] for e in events]
    assert types == ["special_category", "content", "done"]
    assert "status" not in types


@patch("src.assistant.OpenAI")
def test_chat_stream_emits_no_status_event_when_blocked_via_the_tool(mock_openai_cls):
    """The tool-args gate fires before the "Searching segments..." status event."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    tc_chunk = MagicMock()
    tc_chunk.choices = [MagicMock()]
    tc_chunk.choices[0].delta.content = None
    tc_delta = MagicMock()
    tc_delta.id = "call_123"
    tc_delta.function.name = "search_segments"
    tc_delta.function.arguments = '{"query": "trade union members"}'
    tc_chunk.choices[0].delta.tool_calls = [tc_delta]

    mock_client.chat.completions.create.return_value = iter([tc_chunk])

    events = list(chat_stream([{"role": "user", "content": "who's in a workplace collective?"}]))

    types = [e["type"] for e in events]
    assert "status" not in types
    assert types[0] == "special_category"
    assert events[0]["category"] == "trade union membership"


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
        "email": "assistant@immediate.co.uk",
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
def test_assistant_chat_endpoint_flags_special_category_requests(mock_openai_cls):
    mock_openai_cls.return_value = MagicMock()

    client = TestClient(app)
    client.post("/api/auth/signup", json={
        "email": "sensitive@immediate.co.uk",
        "name": "Test",
        "password": "testpass123",
    })
    response = client.post(
        "/api/assistant/chat",
        json={"messages": [{"role": "user", "content": "audiences with hearing loss?"}]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["special_category"] == "health"
    assert data["content"] == SPECIAL_CATEGORY_MESSAGE


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
        "email": "stream@immediate.co.uk",
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


@patch("src.assistant.OpenAI")
def test_assistant_chat_stream_endpoint_carries_the_special_category_event(mock_openai_cls):
    """The SSE endpoint must forward chat_stream()'s special_category event
    end-to-end, not just the underlying generator function (#164)."""
    mock_openai_cls.return_value = MagicMock()

    client = TestClient(app)
    client.post("/api/auth/signup", json={
        "email": "sse-sensitive@immediate.co.uk",
        "name": "Test",
        "password": "testpass123",
    })
    response = client.post(
        "/api/assistant/chat/stream",
        json={"messages": [{"role": "user", "content": "audiences by sexual orientation?"}]},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    lines = response.text.strip().split("\n")
    data_lines = [l for l in lines if l.startswith("data: ")]
    events = [json.loads(l[6:]) for l in data_lines]

    types = [e["type"] for e in events]
    assert types == ["special_category", "content", "done"]

    flag = [e for e in events if e["type"] == "special_category"][0]
    assert flag["category"] == "sex life or sexual orientation"

    content = "".join(e["text"] for e in events if e["type"] == "content")
    assert content == SPECIAL_CATEGORY_MESSAGE

    # No model call was ever made for a request the gate intercepted.
    mock_openai_cls.return_value.chat.completions.create.assert_not_called()
