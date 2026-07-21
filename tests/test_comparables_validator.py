"""Tests for the comparables validator — the trust guardrail.

Pure function over data. Its job: every brand the LLM returns must exist in
the real roster, or it is dropped. This makes "the LLM can never name a brand
we haven't worked with" an enforced guarantee, not a hope.
"""

from src.comparables_validator import validate_comparables

ROSTER = ["Monzo", "Revolut", "Starling Bank", "Coca-Cola"]


def test_valid_pick_survives():
    picks = [{"brand": "Monzo", "why_similar": "challenger finance"}]

    result = validate_comparables(picks, ROSTER)

    assert len(result) == 1
    assert result[0]["brand"] == "Monzo"
    assert result[0]["why_similar"] == "challenger finance"


def test_invalid_pick_is_dropped():
    picks = [
        {"brand": "Monzo", "why_similar": "challenger finance"},
        {"brand": "N26", "why_similar": "not a real client"},  # not on roster
    ]

    result = validate_comparables(picks, ROSTER)

    assert [p["brand"] for p in result] == ["Monzo"]


def test_empty_input_returns_empty():
    assert validate_comparables([], ROSTER) == []


def test_all_invalid_returns_empty():
    picks = [
        {"brand": "N26", "why_similar": "x"},
        {"brand": "Chime", "why_similar": "y"},
    ]

    assert validate_comparables(picks, ROSTER) == []
