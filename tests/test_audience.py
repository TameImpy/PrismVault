"""Tests for the segment recommender (PRD #96 / slice #98).

The deterministic engine (match / rank / fallback) is exercised through
`recommend_segments` with injected `segments` and `expansion`, so no test here
touches OpenAI or the real data/segments.csv.
"""
from unittest.mock import MagicMock

from src.audience import recommend_segments, expand_query, format_audience_segments


def _fixtures():
    """A small, representative canonical segment set across both platforms."""
    return [
        {"segment_name": "Baking Fans", "platform": "Permutive", "reach": "120000",
         "category": "Food & Drink", "description": "browsed for baking content at least 2 times",
         "plain_english": "Regularly browses baking content", "code": "101",
         "frequency": "R", "window": "90 Days", "icon_key": "food-drink"},
        {"segment_name": "Home Baking Intenders", "platform": "AP", "reach": "5000000",
         "category": "Food & Drink", "description": "users who buy baking ingredients",
         "plain_english": "Buy baking ingredients", "code": "ap_x 1",
         "frequency": "", "window": "", "icon_key": "food-drink"},
        {"segment_name": "White Wine fans", "platform": "Permutive", "reach": "90000",
         "category": "Food & Drink", "description": "browsed for white wine content",
         "plain_english": "Regularly browses white wine content", "code": "102",
         "frequency": "R", "window": "All Time", "icon_key": "food-drink"},
        {"segment_name": "Auto Intenders", "platform": "AP", "reach": "8000000",
         "category": "Auto", "description": "in market for a new car",
         "plain_english": "In market for a new car", "code": "ap_x 2",
         "frequency": "", "window": "", "icon_key": "auto"},
    ]


def _by_platform(payload):
    return {p["platform"]: p for p in payload["platforms"]}


def test_keyword_match_returns_relevant_segments_split_by_platform():
    payload = recommend_segments(
        advertiser="Homepride", topic="baking",
        segments=_fixtures(),
        expansion={"keywords": ["baking"], "categories": []},
    )
    platforms = _by_platform(payload)
    assert "AP" in platforms and "Permutive" in platforms

    ap_names = [s["segment_name"] for s in platforms["AP"]["segments"]]
    perm_names = [s["segment_name"] for s in platforms["Permutive"]["segments"]]
    assert "Home Baking Intenders" in ap_names
    assert "Baking Fans" in perm_names
    # Unrelated segments are not surfaced by a "baking" keyword.
    assert "Auto Intenders" not in ap_names
    assert "White Wine fans" not in perm_names


def test_reach_is_int_copied_verbatim_from_source():
    payload = recommend_segments(
        advertiser="Homepride", topic="baking",
        segments=_fixtures(),
        expansion={"keywords": ["baking"], "categories": []},
    )
    platforms = _by_platform(payload)
    ap_seg = platforms["AP"]["segments"][0]
    assert ap_seg["segment_name"] == "Home Baking Intenders"
    # Verbatim from the source row's "5000000", as an int (not a string, not summed).
    assert ap_seg["reach"] == 5000000
    assert isinstance(ap_seg["reach"], int)


def test_capped_at_eight_per_platform_ordered_by_reach_desc():
    # 10 matching Permutive segments with ascending reach.
    segs = [
        {"segment_name": "Baking Fans %d" % i, "platform": "Permutive",
         "reach": str((i + 1) * 1000), "category": "Food & Drink",
         "description": "baking", "plain_english": "Browses baking", "code": str(i),
         "frequency": "R", "window": "All Time", "icon_key": "food-drink"}
        for i in range(10)
    ]
    payload = recommend_segments(
        advertiser="X", topic="baking", segments=segs,
        expansion={"keywords": ["baking"], "categories": []},
    )
    perm = _by_platform(payload)["Permutive"]["segments"]
    assert len(perm) == 8  # capped
    reaches = [s["reach"] for s in perm]
    assert reaches == sorted(reaches, reverse=True)  # ordered by reach desc
    assert reaches[0] == 10000  # the largest survived the cap


def _all_keys(obj):
    """Recursively yield every dict key in a nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            for kk in _all_keys(v):
                yield kk
    elif isinstance(obj, list):
        for item in obj:
            for kk in _all_keys(item):
                yield kk


def test_payload_carries_fields_note_and_no_total():
    payload = recommend_segments(
        advertiser="Homepride", topic="baking",
        segments=_fixtures(),
        expansion={"keywords": ["baking"], "categories": []},
    )
    assert payload["matched"] is True
    # A visible "never sum" note is part of the payload.
    assert "note" in payload
    assert "sum" in payload["note"].lower()
    # No total/summed figure anywhere in the structure.
    keys = set(_all_keys(payload))
    assert "total" not in keys
    assert "total_reach" not in keys
    # Every surfaced segment carries the fields the UI/deck rely on.
    for plat in payload["platforms"]:
        for seg in plat["segments"]:
            assert seg["platform"] == plat["platform"]
            assert seg["category"]
            assert seg["plain_english"]


def test_fallback_broadens_to_category_when_too_few_keyword_hits():
    # Only ONE keyword hit ("Allotment" mentions 'garden'), which is < 3, so the
    # ladder broadens to include category-only matches in "Gardening".
    segs = [
        {"segment_name": "Allotment Growers", "platform": "Permutive", "reach": "50000",
         "category": "Gardening", "description": "browsed for garden allotment content",
         "plain_english": "Browses allotment content", "code": "1",
         "frequency": "R", "window": "All Time", "icon_key": "gardening"},
        {"segment_name": "Rose Enthusiasts", "platform": "Permutive", "reach": "40000",
         "category": "Gardening", "description": "browsed for rose growing content",
         "plain_english": "Browses rose content", "code": "2",
         "frequency": "R", "window": "All Time", "icon_key": "gardening"},
        {"segment_name": "Lawn Care Buyers", "platform": "AP", "reach": "3000000",
         "category": "Gardening", "description": "buy lawn care products",
         "plain_english": "Buy lawn care products", "code": "ap_x 9",
         "frequency": "", "window": "", "icon_key": "gardening"},
        {"segment_name": "Crypto Traders", "platform": "AP", "reach": "9000000",
         "category": "Finance", "description": "trade cryptocurrency",
         "plain_english": "Trade crypto", "code": "ap_x 10",
         "frequency": "", "window": "", "icon_key": "finance"},
    ]
    payload = recommend_segments(
        advertiser="GardenCo", topic="gardening", segments=segs,
        expansion={"keywords": ["garden"], "categories": ["Gardening"]},
    )
    names = [s["segment_name"] for p in payload["platforms"] for s in p["segments"]]
    # Category broadening pulled in the rose + lawn-care rows that "garden" alone missed.
    assert "Allotment Growers" in names
    assert "Rose Enthusiasts" in names
    assert "Lawn Care Buyers" in names
    # A different category is still excluded.
    assert "Crypto Traders" not in names


def test_zero_matches_returns_honest_empty_state():
    payload = recommend_segments(
        advertiser="Obscure Brand", topic="nonexistent",
        segments=_fixtures(),
        expansion={"keywords": ["quantumwidget"], "categories": ["Aerospace"]},
    )
    assert payload["matched"] is False
    # Both platform lists are present but empty (structure + note still shown).
    for plat in payload["platforms"]:
        assert plat["segments"] == []
    assert "sum" in payload["note"].lower()


def _lurpak_fixtures():
    return [
        {"segment_name": "Peanut Butter Fans", "platform": "Permutive", "reach": "45000",
         "category": "Food & Drink", "description": "browsed for peanut butter content",
         "plain_english": "Browses peanut butter content", "code": "1",
         "frequency": "R", "window": "All Time", "icon_key": "food-drink"},
        {"segment_name": "Dairy Free Fans", "platform": "Permutive", "reach": "60000",
         "category": "Food & Drink", "description": "browsed for dairy content",
         "plain_english": "Browses dairy content", "code": "2",
         "frequency": "R", "window": "All Time", "icon_key": "food-drink"},
        {"segment_name": "Home Baking Intenders", "platform": "AP", "reach": "5000000",
         "category": "Food & Drink", "description": "buy baking ingredients",
         "plain_english": "Buy baking ingredients", "code": "ap_x 1",
         "frequency": "", "window": "", "icon_key": "food-drink"},
    ]


def test_lurpak_literal_misses_but_expansion_resolves():
    # The literal brand name matches nothing in the catalogue.
    literal = recommend_segments(
        advertiser="Lurpak", topic="Lurpak", segments=_lurpak_fixtures(),
        expansion={"keywords": ["lurpak"], "categories": []},
    )
    assert literal["matched"] is False

    # Expansion into concept synonyms is what makes the brand resolvable.
    expanded = recommend_segments(
        advertiser="Lurpak", topic="Lurpak", segments=_lurpak_fixtures(),
        expansion={"keywords": ["butter", "dairy", "baking"], "categories": ["Food & Drink"]},
    )
    assert expanded["matched"] is True
    names = [s["segment_name"] for p in expanded["platforms"] for s in p["segments"]]
    assert "Peanut Butter Fans" in names
    assert "Dairy Free Fans" in names


def test_specific_low_reach_segment_beats_generic_high_reach():
    # A niche segment matching a RARE keyword ("gut") must be selected over
    # generic segments matching a COMMON keyword ("food"), even though the
    # generic ones have far higher reach. Relevance gates before reach.
    segs = [
        {"segment_name": "Gut-Friendly Fans", "platform": "Permutive", "reach": "40000",
         "category": "Food & Drink", "description": "browsed for gut friendly content",
         "plain_english": "Browses gut-friendly content", "code": "1",
         "frequency": "R", "window": "All Time", "icon_key": "food-drink"},
    ]
    # 10 generic, huge-reach food segments that only match the common keyword.
    segs += [
        {"segment_name": "Food Fans %d" % i, "platform": "Permutive",
         "reach": str(1000000 + i), "category": "Food & Drink",
         "description": "browsed for food content", "plain_english": "Browses food",
         "code": str(100 + i), "frequency": "R", "window": "All Time",
         "icon_key": "food-drink"}
        for i in range(10)
    ]
    payload = recommend_segments(
        advertiser="Yakult", topic="gut health", segments=segs,
        expansion={"keywords": ["gut", "food"], "categories": []},
    )
    perm = payload["platforms"][1]["segments"]
    names = [s["segment_name"] for s in perm]
    assert "Gut-Friendly Fans" in names  # survived the ≤8 cap on relevance
    assert perm[0]["segment_name"] == "Gut-Friendly Fans"  # ranked most relevant first


def test_matching_is_stem_based_not_just_exact():
    # Keyword "baking" should still match a segment whose text only says "bakers"
    # (shared stem "bak"), so wording drift doesn't silently drop a relevant segment.
    segs = [
        {"segment_name": "Home Bakers", "platform": "Permutive", "reach": "70000",
         "category": "Food & Drink", "description": "keen bakers who make bread",
         "plain_english": "Keen bakers", "code": "1",
         "frequency": "R", "window": "All Time", "icon_key": "food-drink"},
    ]
    payload = recommend_segments(
        advertiser="X", topic="baking", segments=segs,
        expansion={"keywords": ["baking"], "categories": []},
    )
    names = [s["segment_name"] for p in payload["platforms"] for s in p["segments"]]
    assert "Home Bakers" in names


def _fake_client(content):
    """A stand-in OpenAI client whose completion returns `content`."""
    client = MagicMock()
    message = MagicMock()
    message.content = content
    client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=message)])
    return client


def test_expand_query_parses_model_json():
    client = _fake_client(
        '{"keywords": ["butter", "dairy", "baking"], "categories": ["Food & Drink"]}'
    )
    result = expand_query("Lurpak", "Lurpak butter", client_brief="", client=client)
    assert result["keywords"] == ["butter", "dairy", "baking"]
    assert result["categories"] == ["Food & Drink"]


def test_expand_query_tolerates_code_fenced_json():
    client = _fake_client(
        '```json\n{"keywords": ["gardening"], "categories": ["Gardening"]}\n```'
    )
    result = expand_query("GardenCo", "gardening", client=client)
    assert result["keywords"] == ["gardening"]


def test_expand_query_returns_empty_on_garbage():
    client = _fake_client("sorry, I cannot help with that")
    result = expand_query("X", "y", client=client)
    assert result == {"keywords": [], "categories": []}


def test_format_audience_segments_text_for_prompt():
    payload = recommend_segments(
        advertiser="Homepride", topic="baking",
        segments=_fixtures(),
        expansion={"keywords": ["baking"], "categories": []},
    )
    text = format_audience_segments(payload)
    # Names + exact reach appear, with per-platform framing headers.
    assert "Home Baking Intenders" in text
    assert "5,000,000" in text or "5000000" in text
    assert "Modelled first-party" in text  # AP framing
    assert "Behavioural" in text  # Permutive framing
    # The model is told to quote reach verbatim and never sum.
    assert "verbatim" in text.lower()
    assert "sum" in text.lower()


def test_format_audience_segments_empty_state_is_honest():
    payload = recommend_segments(
        advertiser="X", topic="nonexistent", segments=_fixtures(),
        expansion={"keywords": ["quantumwidget"], "categories": []},
    )
    text = format_audience_segments(payload)
    assert "no strongly-matched" in text.lower() or "no strongly matched" in text.lower()
