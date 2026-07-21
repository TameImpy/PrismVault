"""Tests for the comparables engine (Tier 1 — precision path).

The LLM pick step is injected (`pick_fn`) so tests exercise the Python tier
logic — vertical shortlisting, validation, best-format attachment — never the
model's output.
"""

from src.comparables import get_comparables

ROSTER = ["Monzo", "Revolut", "Starling Bank", "Tesco", "Aldi"]
BRAND_VERTICALS = {
    "Monzo": "Finance",
    "Revolut": "Finance",
    "Starling Bank": "Finance",
    "Tesco": "Supermarket",
    "Aldi": "Supermarket",
}
CAMPAIGN_ROWS = [
    {"advertiser": "Monzo", "campaign_name": "Monzo Homepage Takeover",
     "campaign_id": "1", "category": "Finance", "start_date": "2025-01-01",
     "impressions": "1000000", "clicks": "4000"},
    {"advertiser": "Revolut", "campaign_name": "Revolut Launch",
     "campaign_id": "2", "category": "Finance", "start_date": "2025-01-01",
     "impressions": "1000000", "clicks": "2000"},
]


def test_tier1_shortlists_by_vertical_and_validates():
    seen = {}

    def pick_fn(advertiser, shortlist):
        seen["shortlist"] = list(shortlist)
        # Model picks two real Finance brands plus one hallucinated brand.
        return [
            {"brand": "Monzo", "why_similar": "challenger bank"},
            {"brand": "Revolut", "why_similar": "fintech"},
            {"brand": "N26", "why_similar": "not a client"},
        ]

    result = get_comparables(
        advertiser="Chime",
        query_vertical="Finance",
        roster=ROSTER,
        brand_verticals=BRAND_VERTICALS,
        campaign_rows=CAMPAIGN_ROWS,
        pick_fn=pick_fn,
    )

    # Shortlist is only Finance brands (not Supermarket ones).
    assert set(seen["shortlist"]) == {"Monzo", "Revolut", "Starling Bank"}
    # Hallucinated N26 is dropped by validation; only real clients survive.
    assert [c["brand"] for c in result["comparables"]] == ["Monzo", "Revolut"]
    assert result["tier"] == 1


def test_tier1_attaches_best_format():
    def pick_fn(advertiser, shortlist):
        return [{"brand": "Monzo", "why_similar": "challenger bank"}]

    result = get_comparables(
        advertiser="Chime",
        query_vertical="Finance",
        roster=ROSTER,
        brand_verticals=BRAND_VERTICALS,
        campaign_rows=CAMPAIGN_ROWS,
        pick_fn=pick_fn,
    )

    monzo = result["comparables"][0]
    assert monzo["best_format"] == "Monzo Homepage Takeover (0.40% CTR)"


def test_query_brand_excluded_from_shortlist():
    """If the queried brand somehow shares the vertical, it is not compared
    against itself."""
    seen = {}

    def pick_fn(advertiser, shortlist):
        seen["shortlist"] = list(shortlist)
        return []

    get_comparables(
        advertiser="Monzo",
        query_vertical="Finance",
        roster=ROSTER,
        brand_verticals=BRAND_VERTICALS,
        campaign_rows=CAMPAIGN_ROWS,
        pick_fn=pick_fn,
    )

    assert "Monzo" not in seen["shortlist"]


def test_format_comparables_block_renders_name_why_and_format():
    from src.comparables import format_comparables_block
    result = {
        "comparables": [
            {"brand": "Monzo", "why_similar": "challenger bank",
             "best_format": "Monzo Homepage Takeover (0.40% CTR)"},
        ],
        "tier": 1,
        "note": "",
    }

    block = format_comparables_block("Chime", result)

    assert "Monzo" in block
    assert "challenger bank" in block
    assert "Monzo Homepage Takeover (0.40% CTR)" in block
    assert "Chime" in block


def test_format_comparables_block_empty_when_none():
    from src.comparables import format_comparables_block
    assert format_comparables_block("Chime", {"comparables": [], "tier": 1, "note": ""}) == ""
