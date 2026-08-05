"""Tests for the GDPR special-category gate (issue #164).

The point of these tests is the *distinction*: the Assistant already referred
sensitive requests to the audience team, but only by falling through its generic
"I don't know" rule. These tests assert the special-category path fired, not
that the user merely got a referral.
"""

import csv
import os

from src.special_categories import (
    SPECIAL_CATEGORY_MESSAGE,
    SPECIAL_CATEGORY_PROMPT_RULE,
    detect_special_category,
)

SEGMENT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "segments.csv")


# --- Recognition: Article 9 categories ---


def test_detects_health_condition():
    assert detect_special_category("Do we have audiences with hearing loss?") == "health"


def test_detects_health_across_several_conditions():
    for query in [
        "target people with diabetes",
        "cancer patients",
        "audiences living with a disability",
        "anyone with dementia",
        "people on medication for depression",
    ]:
        assert detect_special_category(query) == "health", query


def test_detects_ethnicity():
    assert detect_special_category("can we target by ethnicity?") == "racial or ethnic origin"


def test_detects_religious_belief():
    assert (
        detect_special_category("muslim audiences")
        == "religious or philosophical beliefs"
    )


def test_detects_political_opinion():
    assert detect_special_category("segments by voting intention") == "political opinions"


def test_detects_trade_union_membership():
    assert detect_special_category("trade union members") == "trade union membership"


def test_detects_sexual_orientation():
    assert detect_special_category("lgbt audiences") == "sex life or sexual orientation"


def test_detects_genetic_or_biometric_data():
    assert (
        detect_special_category("anything based on genetic data?")
        == "genetic or biometric data"
    )


def test_detection_is_case_insensitive():
    assert detect_special_category("HEARING LOSS AUDIENCES") == "health"


def test_detection_handles_empty_and_none():
    assert detect_special_category("") is None
    assert detect_special_category(None) is None


def test_detection_handles_falsy_non_string_values():
    """Falsy non-string content (e.g. an empty list) must not crash the gate."""
    assert detect_special_category([]) is None
    assert detect_special_category({}) is None
    assert detect_special_category(0) is None


def test_detects_through_multi_part_content():
    """OpenAI allows `content` to be a list of parts, not just a string.

    A list is truthy, so it would reach `re.search` and raise TypeError — a gate
    that crashes on an input shape is a gate that isn't applied. The parts are
    flattened and scanned instead.
    """
    assert detect_special_category(
        [{"type": "text", "text": "hearing loss audiences"}]
    ) == "health"
    assert detect_special_category(
        [{"type": "text", "text": "what pet segments do you have?"}]
    ) is None


def test_detects_through_unfamiliar_content_shapes():
    """An unknown shape must still be read, not silently skipped."""
    assert detect_special_category({"body": "target by ethnicity"}) == "racial or ethnic origin"
    assert detect_special_category(["please find", ["muslim audiences"]]) == (
        "religious or philosophical beliefs"
    )


# --- No over-blocking: ordinary requests are unaffected ---


def test_ordinary_audience_queries_are_not_flagged():
    for query in [
        "pet owners",
        "health conscious foodies",
        "fitness and training fans",
        "gym membership considerers",
        "healthcare professionals",
        "vegan and gluten free food fans",
        "political podcast listeners",
        "christmas gift buyers",
        "racing games fans",
        "peaky blinders fans",
        "what is Prism?",
        "how long does a bespoke segment take to build?",
        "audiences for a car brand targeting families",
    ]:
        assert detect_special_category(query) is None, query


def test_no_segment_in_the_catalogue_is_flagged():
    """The whole catalogue is sellable; nothing in it may trip the gate.

    If a new segment ever does trip it, that is a commercial/legal question
    about the segment, not a reason to loosen the term list quietly.
    """
    with open(SEGMENT_CSV, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    flagged = []
    for row in rows:
        blob = "%s %s %s" % (
            row.get("segment_name", ""),
            row.get("category", ""),
            row.get("plain_english", "") or row.get("description", ""),
        )
        category = detect_special_category(blob)
        if category:
            flagged.append((row.get("segment_name", ""), category))

    assert flagged == [], "catalogue segments tripped the gate: %r" % flagged[:10]


# --- The message and the prompt rule ---


def test_message_names_the_reason_and_the_audience_team():
    lowered = SPECIAL_CATEGORY_MESSAGE.lower()
    assert "health" in lowered
    assert "ethnicity" in lowered
    assert "beliefs" in lowered
    assert "dl-audience-ads@immediate.co.uk" in lowered


def test_prompt_rule_carries_the_message_verbatim():
    """Wordings the term list misses still have to land on the same message."""
    assert SPECIAL_CATEGORY_MESSAGE in SPECIAL_CATEGORY_PROMPT_RULE
    assert "special category" in SPECIAL_CATEGORY_PROMPT_RULE.lower()
