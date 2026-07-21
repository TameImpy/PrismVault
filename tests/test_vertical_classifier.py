"""Tests for the vertical classifier (ingest-time brand→vertical lookup).

The new-brand diff is a pure function and is tested directly. The
classification orchestration is tested with the LLM classifier stubbed —
we verify the Python logic (diff, caching, flagging), never model output.
"""

import os
import csv
import json
import tempfile

from src.vertical_classifier import (
    diff_new_brands,
    refresh_brand_verticals,
    load_brand_verticals,
    seed_vertical_from_category,
    distinct_brands_with_hints,
)


def test_diff_new_brands_detects_uncached():
    roster = ["Tesco", "Aldi", "Monzo"]
    cached = {"Tesco": "Supermarket", "Aldi": "Supermarket"}

    new = diff_new_brands(roster, cached)

    assert new == ["Monzo"]


def _seed_lookup(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["brand", "vertical", "source", "needs_review"]
        )
        writer.writeheader()
        writer.writerows(rows)


def test_refresh_classifies_only_new_brands_and_flags_them():
    with tempfile.TemporaryDirectory() as tmpdir:
        lookup_path = os.path.join(tmpdir, "brand_verticals.csv")
        _seed_lookup(
            lookup_path,
            [{"brand": "Tesco", "vertical": "Supermarket",
              "source": "seed", "needs_review": "false"}],
        )

        roster = ["Tesco", "Monzo", "Revolut"]
        hints = {"Tesco": "Supermarket", "Monzo": "Finance", "Revolut": "Finance"}
        taxonomy = ["Supermarket", "Finance"]

        seen = {}

        def fake_classifier(brands, category_hints, tax):
            seen["brands"] = list(brands)
            return {b: "Finance" for b in brands}

        result = refresh_brand_verticals(
            roster, hints, taxonomy, lookup_path, fake_classifier
        )

        # Cached brand is never re-classified (deterministic / cheap refresh).
        assert set(seen["brands"]) == {"Monzo", "Revolut"}
        # New brands are added and flagged for review.
        assert set(result["added"]) == {"Monzo", "Revolut"}
        assert set(result["flagged"]) == {"Monzo", "Revolut"}
        # Cache file now holds all three brands.
        assert load_brand_verticals(lookup_path) == {
            "Tesco": "Supermarket",
            "Monzo": "Finance",
            "Revolut": "Finance",
        }


def test_refresh_is_idempotent():
    """A second refresh with the same roster classifies nothing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        lookup_path = os.path.join(tmpdir, "brand_verticals.csv")
        _seed_lookup(
            lookup_path,
            [{"brand": "Tesco", "vertical": "Supermarket",
              "source": "seed", "needs_review": "false"}],
        )
        roster = ["Tesco", "Monzo"]
        hints = {"Tesco": "Supermarket", "Monzo": "Finance"}
        taxonomy = ["Supermarket", "Finance"]

        def classifier(brands, category_hints, tax):
            return {b: "Finance" for b in brands}

        refresh_brand_verticals(roster, hints, taxonomy, lookup_path, classifier)

        calls = {"n": 0}

        def counting_classifier(brands, category_hints, tax):
            calls["n"] += len(list(brands))
            return {b: "Finance" for b in brands}

        result = refresh_brand_verticals(
            roster, hints, taxonomy, lookup_path, counting_classifier
        )

        assert calls["n"] == 0
        assert result["added"] == []


def test_seed_vertical_maps_known_category_and_rejects_junk():
    assert seed_vertical_from_category("Food") == "Food & Drink"
    assert seed_vertical_from_category("gambling") == "Gambling"
    # Junk / numeric / unknown categories map to nothing (left for review).
    assert seed_vertical_from_category("1972520") == ""
    assert seed_vertical_from_category("") == ""


def test_distinct_brands_with_hints_uses_modal_category():
    rows = [
        {"advertiser": "Acme", "category": "Food", "campaign_id": "1",
         "campaign_name": "a", "start_date": "2025-01-01",
         "impressions": "1", "clicks": "0"},
        {"advertiser": "Acme", "category": "Food", "campaign_id": "2",
         "campaign_name": "b", "start_date": "2025-01-01",
         "impressions": "1", "clicks": "0"},
        {"advertiser": "Acme", "category": "1972520", "campaign_id": "3",
         "campaign_name": "c", "start_date": "2025-01-01",
         "impressions": "1", "clicks": "0"},
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "campaigns.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        roster, hints = distinct_brands_with_hints(csv_path)

        assert roster == ["Acme"]
        # "Food" appears twice, the junk category once -> modal is "Food".
        assert hints["Acme"] == "Food"
