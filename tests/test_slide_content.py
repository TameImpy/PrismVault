"""
Tests for the slide content generator at src/slide_content.py.

Uses a mocked OpenAI client — no real API calls.
"""
import sys
import os
import json

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import patch, MagicMock
from src.slide_content import generate_slide_content


def _mock_openai_response(content):
    """Create a mock OpenAI chat completion response."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


SAMPLE_LLM_OUTPUT = json.dumps({
    "stats": [
        {"value": "40%", "label": "addressable audience share"},
        {"value": "112", "label": "audience index health enthusiasts"},
        {"value": "2.7x", "label": "average frequency reach"},
        {"value": "Q3", "label": "peak engagement quarter"},
        {"value": "85%", "label": "brand safe inventory"},
        {"value": "3.2m", "label": "monthly active food audience"},
    ],
    "left_heading": "Advertiser Overview",
    "left_bullets": [
        "Leading probiotic brand in UK market",
        "Targeting health-conscious ABC1 consumers",
        "Recent campaign focused on gut-brain axis",
    ],
    "right_heading": "Editorial Insights & Alignment",
    "right_bullets": [
        "Editors report growing reader interest in gut health",
        "Strong alignment with wellness editorial calendar",
        "Opportunity for sponsored content partnerships",
    ],
    "messaging_heading": "Messaging & Tone",
    "messaging_items": [
        {"headline": "Lead with science", "detail": "Ground claims in clinical research and editor-endorsed health content"},
        {"headline": "Warm and approachable", "detail": "Avoid clinical jargon, use everyday wellness language"},
        {"headline": "Seasonal hooks", "detail": "Tie messaging to January wellness and September back-to-routine peaks"},
    ],
    "products": [
        {"name": "Infinity Skin", "metric": "CTR 0.42%, Viewability 78%"},
        {"name": "Playstream Video", "metric": "Viewability 91%, strong mobile"},
        {"name": "IM Masthead", "metric": "Premium impact, 2.1m impressions"},
    ],
    "cta": "We'd love to explore how these insights can shape your next campaign. Let's book a call to discuss.",
})


@patch("src.slide_content.OpenAI")
def test_generate_slide_content_returns_valid_structure(mock_openai_cls):
    """generate_slide_content() returns a dict with all required slide fields."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_openai_response(SAMPLE_LLM_OUTPUT)

    result = generate_slide_content(
        brief_content="## Key Recommendations\n1. Align with gut health...",
        topic="gut health",
        advertiser="Yakult",
        kpi="Awareness",
    )

    # Verify all required keys
    assert "stats" in result
    assert len(result["stats"]) == 6
    assert "left_heading" in result
    assert "left_bullets" in result
    assert "right_heading" in result
    assert "right_bullets" in result
    assert "messaging_heading" in result
    assert "messaging_items" in result
    assert "products" in result
    assert "cta" in result


@patch("src.slide_content.OpenAI")
def test_uses_gpt4o_mini(mock_openai_cls):
    """generate_slide_content() calls GPT-4o-mini."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_openai_response(SAMPLE_LLM_OUTPUT)

    generate_slide_content("brief", "topic", "advertiser", "Awareness")

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"


@patch("src.slide_content.OpenAI")
def test_prompt_includes_inputs(mock_openai_cls):
    """The user prompt contains the advertiser, topic, KPI, and brief content."""
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_openai_response(SAMPLE_LLM_OUTPUT)

    generate_slide_content("some brief content here", "gut health", "Yakult", "Viewability")

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    user_msg = call_kwargs["messages"][1]["content"]
    assert "Yakult" in user_msg
    assert "gut health" in user_msg
    assert "Viewability" in user_msg
    assert "some brief content here" in user_msg


def test_truncation_enforces_limits():
    """Post-processing truncates overlong fields to hard limits."""
    from src.slide_content import _parse_and_validate

    overlong = json.dumps({
        "stats": [
            {"value": "123456789", "label": "one two three four five six seven eight nine ten"},
        ] * 8,  # 8 stats, should be capped to 6
        "left_heading": "Advertiser Overview",
        "left_bullets": ["word " * 20] * 6,  # 6 bullets of 20 words, capped to 4 bullets of 15 words
        "right_heading": "Editorial",
        "right_bullets": ["short"],
        "messaging_heading": "Messaging",
        "messaging_items": [
            {"headline": "one two three four five six seven eight", "detail": "word " * 25}
        ],
        "products": [{"name": "x" * 50, "metric": "word " * 15}],
        "cta": "word " * 40,
    })

    result = _parse_and_validate(overlong)

    # Stats capped to 6, values to 5 chars, labels to 8 words
    assert len(result["stats"]) == 6
    assert len(result["stats"][0]["value"]) <= 5
    assert len(result["stats"][0]["label"].split()) <= 8

    # Bullets capped to 4 items, 15 words each
    assert len(result["left_bullets"]) <= 4
    for bullet in result["left_bullets"]:
        assert len(bullet.split()) <= 15

    # Messaging headline max 6 words, detail max 20 words
    for item in result["messaging_items"]:
        assert len(item["headline"].split()) <= 6
        assert len(item["detail"].split()) <= 20

    # Product name max 30 chars, metric max 10 words
    for prod in result["products"]:
        assert len(prod["name"]) <= 30
        assert len(prod["metric"].split()) <= 10

    # CTA max 30 words
    assert len(result["cta"].split()) <= 30


def test_parse_handles_markdown_code_fences():
    """LLM responses wrapped in ```json fences are handled correctly."""
    from src.slide_content import _parse_and_validate

    wrapped = "```json\n" + SAMPLE_LLM_OUTPUT + "\n```"
    result = _parse_and_validate(wrapped)
    assert len(result["stats"]) == 6
