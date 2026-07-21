"""Tests for the deterministic audience slide-content transform (slice #100).

Reach never passes through the LLM: this pure transform shapes the
audience_segments payload into slide rows with resolved icon paths.
"""
import os
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.slide_content import build_audience_slide_content


def _payload():
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
                     "plain_english": "Feel confident when baking", "description": "",
                     "code": "ap_x 1", "frequency": "", "window": ""},
                ],
            },
            {
                "platform": "Permutive",
                "framing": "Behavioural — recently engaged browsers",
                "segments": [
                    {"segment_name": "Segment %d" % i, "reach": 1000 * (10 - i),
                     "platform": "Permutive", "category": "Food & Drink",
                     "plain_english": "Browses food content", "description": "browsed",
                     "code": str(i), "frequency": "R", "window": "All Time"}
                    for i in range(8)
                ],
            },
        ],
    }


def test_transform_shapes_rows_with_reach_and_icon():
    content = build_audience_slide_content(_payload())
    assert content["matched"] is True
    ap = [p for p in content["platforms"] if p["platform"] == "AP"][0]
    seg = ap["segments"][0]
    assert seg["why"] == "Feel confident when baking"
    assert seg["reach"] == "10,486,296"  # verbatim, formatted, never summed
    assert seg["icon_path"].endswith("baking.png")  # keyword override
    assert os.path.exists(seg["icon_path"])


def test_transform_caps_rows_per_platform():
    content = build_audience_slide_content(_payload(), per_platform=5)
    perm = [p for p in content["platforms"] if p["platform"] == "Permutive"][0]
    assert len(perm["segments"]) == 5


def test_transform_has_no_summed_total():
    content = build_audience_slide_content(_payload())

    def keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield k
                yield from keys(v)
        elif isinstance(obj, list):
            for it in obj:
                yield from keys(it)

    assert "total" not in set(keys(content))


def test_transform_empty_state():
    empty = {"matched": False, "note": "none", "platforms": []}
    content = build_audience_slide_content(empty)
    assert content["matched"] is False
    assert content["platforms"] == []
