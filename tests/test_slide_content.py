"""
Tests for the slide content step at src/slide_content.py.

Two halves, matching the module's two jobs (PRD #131 / slice #134):

- the deterministic transforms that shape the structured brief payload into
  slide rows — reach, CTR and viewability never pass through the LLM;
- the single LLM call, which is reduced to advertiser-overview prose plus the
  selection of 3 grounded research insights. Mocked — no real API calls.
"""
import sys
import os
import json

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import patch, MagicMock

from src.slide_content import (
    INSIGHT_STAT_MAX_CHARS,
    INSIGHT_TEXT_MAX_WORDS,
    INSIGHT_TILES,
    OVERVIEW_MAX_WORDS,
    build_product_rows,
    build_segment_rows,
    generate_slide_content,
    _parse_and_validate,
)

# ---------------------------------------------------------------------------
# Deterministic transforms
# ---------------------------------------------------------------------------


def _audience_payload():
    return {
        "matched": True,
        "note": "Reach figures are per-segment and must not be summed.",
        "query_terms": ["baking"],
        "platforms": [
            {
                "platform": "AP",
                "framing": "Modelled first-party audience — broad reach",
                "segments": [
                    {"segment_name": "Confident bakers", "reach": 10486296,
                     "platform": "AP", "category": "Food & Drink",
                     "plain_english": "Feel confident when baking"},
                    {"segment_name": "Cake decorators", "reach": 3401118,
                     "platform": "AP", "category": "Food & Drink",
                     "plain_english": "Decorate cakes at home"},
                ],
            },
            {
                "platform": "Permutive",
                "framing": "Behavioural — recently engaged browsers",
                "segments": [
                    {"segment_name": "Segment %d" % i, "reach": 1000 * (10 - i),
                     "platform": "Permutive", "category": "Food & Drink",
                     "plain_english": "Browses food content"}
                    for i in range(8)
                ],
            },
        ],
    }


def test_segment_rows_carry_name_and_verbatim_reach():
    rows = build_segment_rows(_audience_payload())
    assert rows[0]["name"] == "Confident bakers"
    assert rows[0]["reach"] == "10,486,296"  # digits verbatim, separators only


def test_segment_rows_are_capped_at_the_tile_count():
    assert len(build_segment_rows(_audience_payload(), limit=4)) == 4


def test_segment_rows_alternate_between_platforms():
    """Both audience engines are represented rather than the first one filling
    every tile."""
    rows = build_segment_rows(_audience_payload(), limit=4)
    names = [r["name"] for r in rows]
    assert names == ["Confident bakers", "Segment 0", "Cake decorators", "Segment 1"]


def test_segment_rows_fall_back_to_one_platform_when_only_one_matched():
    payload = _audience_payload()
    payload["platforms"] = payload["platforms"][:1]
    rows = build_segment_rows(payload, limit=4)
    assert [r["name"] for r in rows] == ["Confident bakers", "Cake decorators"]


def test_segment_rows_empty_when_nothing_matched():
    assert build_segment_rows({"matched": False, "platforms": []}) == []
    assert build_segment_rows(None) == []


def test_segment_reach_is_never_summed():
    rows = build_segment_rows(_audience_payload())
    total = "{:,}".format(sum(s["reach"] for s in _audience_payload()["platforms"][0]["segments"]))
    assert total not in [r["reach"] for r in rows]


def test_segment_row_tolerates_a_non_numeric_reach():
    payload = {"matched": True, "platforms": [
        {"platform": "AP", "segments": [{"segment_name": "Odd one", "reach": "n/a"}]}]}
    assert build_segment_rows(payload)[0]["reach"] == "n/a"


FORMAT_ROWS = [
    {"format": "Infinity Skin", "ctr": "0.42%", "viewability": "78.30%"},
    {"format": "Playstream Video", "ctr": "0.31%", "viewability": "91.04%"},
    {"format": "Standard display - MPU", "ctr": "0.05%", "viewability": "39.89%"},
    {"format": "Podcast read", "ctr": "", "viewability": ""},
]


def test_product_rows_are_verbatim():
    rows = build_product_rows(FORMAT_ROWS, limit=3)
    assert rows[0] == {"format": "Infinity Skin", "ctr": "0.42%", "viewability": "78.30%"}
    assert len(rows) == 3


def test_product_rows_keep_formats_without_benchmarks():
    """A non-digital format has no CTR — the tile goes blank, the row stays."""
    rows = build_product_rows(FORMAT_ROWS[3:], limit=3)
    assert rows[0]["format"] == "Podcast read"
    assert rows[0]["ctr"] == ""


def test_product_rows_empty_without_a_payload():
    assert build_product_rows(None) == []
    assert build_product_rows([]) == []


# ---------------------------------------------------------------------------
# LLM step — advertiser overview + grounded insight selection only
# ---------------------------------------------------------------------------


def _mock_openai_response(content):
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


SAMPLE_LLM_OUTPUT = json.dumps({
    "advertiser_overview": (
        "Yakult is the UK's leading probiotic drinks brand, sold mainly through "
        "grocery multiples and increasingly positioned around everyday gut health."
    ),
    "insights": [
        {"stat": "68%", "text": "of readers say gut health matters"},
        {"stat": "2.4x", "text": "more likely to try a new drink"},
        {"stat": "41%", "text": "read health content at least weekly"},
    ],
})

RESEARCH = {"relevant": True, "file": "gut_health.md", "prompt_text": "68% of readers ..."}


def _mock_client(mock_openai_cls, payload=SAMPLE_LLM_OUTPUT):
    client = MagicMock()
    mock_openai_cls.return_value = client
    client.chat.completions.create.return_value = _mock_openai_response(payload)
    return client


@patch("src.slide_content.OpenAI")
def test_generate_slide_content_returns_overview_and_insights(mock_openai_cls):
    _mock_client(mock_openai_cls)

    result = generate_slide_content(
        brief_content="## Key Recommendations\n1. Align with gut health...",
        topic="gut health",
        advertiser="Yakult",
        kpi="Awareness",
        historical_research=RESEARCH,
    )

    assert set(result) == {"advertiser_overview", "insights"}
    assert result["advertiser_overview"].startswith("Yakult is the UK's leading")
    assert len(result["insights"]) == 3
    assert result["insights"][0] == {
        "stat": "68%",
        "text": "of readers say gut health matters",
    }


@patch("src.slide_content.OpenAI")
def test_uses_gpt4o_mini(mock_openai_cls):
    client = _mock_client(mock_openai_cls)
    generate_slide_content("brief", "topic", "advertiser", "Awareness")
    assert client.chat.completions.create.call_args[1]["model"] == "gpt-4o-mini"


@patch("src.slide_content.OpenAI")
def test_prompt_includes_inputs(mock_openai_cls):
    client = _mock_client(mock_openai_cls)

    generate_slide_content("some brief content here", "gut health", "Yakult", "Viewability")

    user_msg = client.chat.completions.create.call_args[1]["messages"][1]["content"]
    assert "Yakult" in user_msg
    assert "gut health" in user_msg
    assert "Viewability" in user_msg
    assert "some brief content here" in user_msg


@patch("src.slide_content.OpenAI")
def test_matched_research_body_is_put_in_front_of_the_model(mock_openai_cls):
    """Insights are selected from the research body, so the body must be in the
    prompt — grounded, not recalled."""
    client = _mock_client(mock_openai_cls)

    generate_slide_content("brief", "gut health", "Yakult", "Awareness",
                           historical_research=RESEARCH)

    user_msg = client.chat.completions.create.call_args[1]["messages"][1]["content"]
    assert "68% of readers ..." in user_msg


@patch("src.slide_content.OpenAI")
def test_research_body_is_reread_from_the_catalogue_by_filename(mock_openai_cls, tmp_path):
    """The client posts back only the matched file name; the body is re-read
    server-side rather than shipped to the browser and back."""
    from src import historical_research

    (tmp_path / "gut.md").write_text(
        "---\ntitle: Gut\ntopics: [gut health]\n---\nSeventy per cent of readers.\n"
    )
    client = _mock_client(mock_openai_cls)

    with patch.object(historical_research, "CATALOGUE_DIR", str(tmp_path)):
        generate_slide_content("brief", "gut health", "Yakult", "Awareness",
                               historical_research={"relevant": True, "file": "gut.md"})

    user_msg = client.chat.completions.create.call_args[1]["messages"][1]["content"]
    assert "Seventy per cent of readers." in user_msg


@patch("src.slide_content.OpenAI")
def test_no_insights_without_matched_research(mock_openai_cls):
    """Nothing matched — the section is omitted rather than filled with prose
    the model made up."""
    _mock_client(mock_openai_cls)

    result = generate_slide_content("brief", "gut health", "Yakult", "Awareness")

    assert result["insights"] == []


@patch("src.slide_content.OpenAI")
def test_no_insights_when_research_is_marked_irrelevant(mock_openai_cls):
    _mock_client(mock_openai_cls)

    result = generate_slide_content("brief", "topic", "Yakult", "Awareness",
                                    historical_research={"relevant": False})

    assert result["insights"] == []


def test_validation_enforces_tile_limits():
    overlong = json.dumps({
        "advertiser_overview": "word " * 120,
        "insights": [{"stat": "sixty eight per cent", "text": "word " * 30}] * 6,
    })

    result = _parse_and_validate(overlong, has_research=True)

    assert len(result["advertiser_overview"].split()) <= OVERVIEW_MAX_WORDS
    assert len(result["insights"]) == INSIGHT_TILES
    for insight in result["insights"]:
        assert len(insight["stat"]) <= INSIGHT_STAT_MAX_CHARS
        assert len(insight["text"].split()) <= INSIGHT_TEXT_MAX_WORDS


def test_validation_drops_a_partial_insight():
    """An insight missing its figure would leave half a tile — drop it."""
    payload = json.dumps({
        "advertiser_overview": "Fine.",
        "insights": [
            {"stat": "68%", "text": "of readers care"},
            {"stat": "", "text": "no figure here"},
            {"stat": "41%", "text": ""},
        ],
    })

    result = _parse_and_validate(payload, has_research=True)

    assert result["insights"] == [{"stat": "68%", "text": "of readers care"}]


def test_parse_handles_markdown_code_fences():
    wrapped = "```json\n" + SAMPLE_LLM_OUTPUT + "\n```"
    assert len(_parse_and_validate(wrapped, has_research=True)["insights"]) == 3


@patch("src.slide_content.OpenAI")
def test_unparseable_response_degrades_to_empty_content(mock_openai_cls):
    """A malformed model response must not fail the download — the deck still
    builds, just without the prose."""
    _mock_client(mock_openai_cls, payload="not json at all")

    result = generate_slide_content("brief", "topic", "Yakult", "Awareness")

    assert result == {"advertiser_overview": "", "insights": []}


# ---------------------------------------------------------------------------
# The caps agree with the prompt, and with the tile that has to hold them (#162)
# ---------------------------------------------------------------------------


def test_the_prompt_asks_for_the_length_the_code_enforces():
    """A cap the model is never told about is a cap that truncates every run."""
    from src.slide_content import (
        INSIGHT_STAT_MAX_CHARS,
        INSIGHT_TEXT_MAX_WORDS,
        OVERVIEW_MAX_WORDS,
        SYSTEM_PROMPT,
    )

    assert "max %d words" % OVERVIEW_MAX_WORDS in SYSTEM_PROMPT
    assert "max %d words" % INSIGHT_TEXT_MAX_WORDS in SYSTEM_PROMPT
    assert "max %d characters" % INSIGHT_STAT_MAX_CHARS in SYSTEM_PROMPT


def test_the_caps_fit_the_tiles_they_are_written_for():
    """Asked-for length and tile capacity have to agree, or every deck arrives
    with its insight lines cut short — the state #162 found them in.

    Measured at the average English word length. A cap cannot guarantee a fit
    for every phrasing — "supermarket" costs half a 26pt line on its own — and
    it does not have to: `src.tile_fit` is the hard guarantee. What this pins is
    that the cap is somewhere near the tile, so shortening is the exception
    rather than something every deck goes through.
    """
    from src.slide_content import INSIGHT_TEXT_MAX_WORDS, OVERVIEW_MAX_WORDS
    from src.tile_fit import budget_for, rendered_lines

    for marker, cap in (("[INSIGHT_1_STAT]", INSIGHT_TEXT_MAX_WORDS),
                        ("[ADVERTISER_OVERVIEW]", OVERVIEW_MAX_WORDS)):
        tile = budget_for(marker)
        at_cap = " ".join(["bread"] * cap)  # five letters: the English average
        lines = rendered_lines(at_cap, tile.width, tile.typeface, tile.size)
        assert len(lines) <= tile.lines, (
            "%s is asked for %d words but its tile holds %d lines, and %d "
            "average-length words need %d" % (marker, cap, tile.lines, cap, len(lines))
        )
