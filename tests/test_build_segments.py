"""Unit tests for scripts/build_segments.py pure helper functions.

No .xlsx files are read — all fixtures are constructed in-memory.
The tests cover the full surface of the importable helpers and verify
the key invariants documented in the module's docstring.
"""
import os
import sys

# scripts/ has no __init__.py; insert its directory onto sys.path so we can
# import build_segments directly (same pattern as conftest.py does for root).
_SCRIPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import build_segments as bs

# ---------------------------------------------------------------------------
# to_int_reach
# ---------------------------------------------------------------------------


def test_to_int_reach_positive_int():
    assert bs.to_int_reach(68641) == 68641


def test_to_int_reach_positive_float():
    # Floats that represent whole numbers should convert cleanly.
    assert bs.to_int_reach(12345.0) == 12345


def test_to_int_reach_positive_string():
    assert bs.to_int_reach("50000") == 50000


def test_to_int_reach_zero_returns_none():
    assert bs.to_int_reach(0) is None


def test_to_int_reach_zero_string_returns_none():
    assert bs.to_int_reach("0") is None


def test_to_int_reach_empty_string_returns_none():
    assert bs.to_int_reach("") is None


def test_to_int_reach_none_returns_none():
    assert bs.to_int_reach(None) is None


def test_to_int_reach_non_numeric_string_returns_none():
    assert bs.to_int_reach("abc") is None


def test_to_int_reach_negative_returns_none():
    assert bs.to_int_reach(-100) is None


def test_to_int_reach_negative_string_returns_none():
    assert bs.to_int_reach("-5") is None


def test_to_int_reach_float_string():
    # "68641.0" often comes from xlsx exports that store numbers as text.
    assert bs.to_int_reach("68641.0") == 68641


# ---------------------------------------------------------------------------
# canonical_category
# ---------------------------------------------------------------------------


def test_canonical_category_arts_lowercase():
    assert bs.canonical_category("arts & entertainment") == "Arts & Entertainment"


def test_canonical_category_arts_mixed_case():
    # The raw export sometimes uses sentence case.
    assert bs.canonical_category("Arts & entertainment") == "Arts & Entertainment"


def test_canonical_category_sport_singular():
    assert bs.canonical_category("Sport") == "Sports"


def test_canonical_category_sports_already_plural():
    assert bs.canonical_category("Sports") == "Sports"


def test_canonical_category_food_and_drink():
    assert bs.canonical_category("food & drink") == "Food & Drink"


def test_canonical_category_blank_returns_uncategorised():
    assert bs.canonical_category("") == "Uncategorised"


def test_canonical_category_none_returns_uncategorised():
    assert bs.canonical_category(None) == "Uncategorised"


def test_canonical_category_unknown_passes_through_stripped():
    assert bs.canonical_category("  Motoring  ") == "Motoring"


def test_canonical_category_unknown_preserves_original_casing():
    # Values not in the canon map should come back as-is (stripped).
    assert bs.canonical_category("Travel & Leisure") == "Travel & Leisure"


# ---------------------------------------------------------------------------
# parse_permutive_category
# ---------------------------------------------------------------------------


def test_parse_permutive_category_food_and_drink():
    name = "Food & Drink - White Wine fans (F & 90 Days)"
    assert bs.parse_permutive_category(name) == "Food & Drink"


def test_parse_permutive_category_sport_variant_folds():
    name = "Sport - Football fans (R & 90 Days)"
    assert bs.parse_permutive_category(name) == "Sports"


def test_parse_permutive_category_arts_mixed_case_folds():
    name = "Arts & entertainment - Film lovers (O & All time)"
    assert bs.parse_permutive_category(name) == "Arts & Entertainment"


def test_parse_permutive_category_no_separator_returns_uncategorised():
    assert bs.parse_permutive_category("No separator here") == "Uncategorised"


def test_parse_permutive_category_blank_returns_uncategorised():
    assert bs.parse_permutive_category("") == "Uncategorised"


def test_parse_permutive_category_none_returns_uncategorised():
    assert bs.parse_permutive_category(None) == "Uncategorised"


# ---------------------------------------------------------------------------
# extract_variant
# ---------------------------------------------------------------------------


def test_extract_variant_r_90_days():
    name = "Food & Drink - White Wine fans (R & 90 Days)"
    assert bs.extract_variant(name) == ("R", "90 Days")


def test_extract_variant_f_all_time():
    name = "Sport - Football (F & All time)"
    assert bs.extract_variant(name) == ("F", "All Time")


def test_extract_variant_o_all_time():
    name = "Tech - Gadgets (O & All time)"
    assert bs.extract_variant(name) == ("O", "All Time")


def test_extract_variant_window_normalised_to_title():
    # "all time" should become "All Time" regardless of raw casing.
    name = "Something (R & all time)"
    letter, window = bs.extract_variant(name)
    assert letter == "R"
    assert window == "All Time"


def test_extract_variant_no_suffix_returns_empty_tuple():
    assert bs.extract_variant("No suffix here") == ("", "")


def test_extract_variant_non_rof_letter_returns_empty():
    # A letter that is not R, O, or F should not match.
    name = "Something (X & 90 Days)"
    assert bs.extract_variant(name) == ("", "")


def test_extract_variant_none_input_returns_empty():
    assert bs.extract_variant(None) == ("", "")


def test_extract_variant_empty_string_returns_empty():
    assert bs.extract_variant("") == ("", "")


# ---------------------------------------------------------------------------
# normalise_window
# ---------------------------------------------------------------------------


def test_normalise_window_all_time_lower():
    assert bs.normalise_window("all time") == "All Time"


def test_normalise_window_all_times_variant():
    assert bs.normalise_window("all times") == "All Time"


def test_normalise_window_90_days_lower():
    assert bs.normalise_window("90 days") == "90 Days"


def test_normalise_window_90days_no_space():
    assert bs.normalise_window("90days") == "90 Days"


def test_normalise_window_30_days():
    assert bs.normalise_window("30 days") == "30 Days"


def test_normalise_window_7_days():
    assert bs.normalise_window("7 days") == "7 Days"


def test_normalise_window_blank_returns_empty():
    assert bs.normalise_window("") == ""


def test_normalise_window_none_returns_empty():
    assert bs.normalise_window(None) == ""


def test_normalise_window_already_canonical_passthrough():
    assert bs.normalise_window("90 Days") == "90 Days"


# ---------------------------------------------------------------------------
# icon_key_for
# ---------------------------------------------------------------------------


def test_icon_key_food_drink():
    assert bs.icon_key_for("Food & Drink") == "food-drink"


def test_icon_key_arts_entertainment():
    assert bs.icon_key_for("Arts & Entertainment") == "arts-entertainment"


def test_icon_key_sports():
    assert bs.icon_key_for("Sports") == "sports"


def test_icon_key_blank_returns_uncategorised():
    assert bs.icon_key_for("") == "uncategorised"


def test_icon_key_uncategorised_literal():
    assert bs.icon_key_for("Uncategorised") == "uncategorised"


def test_icon_key_deterministic_for_same_input():
    # Same input must always produce the same slug.
    assert bs.icon_key_for("Travel & Leisure") == bs.icon_key_for("Travel & Leisure")


def test_icon_key_lowercase_slug_no_ampersand():
    # Ampersands should be collapsed into the separator, not left in.
    result = bs.icon_key_for("Food & Drink")
    assert "&" not in result
    assert result == result.lower()


# ---------------------------------------------------------------------------
# permutive_plain_english
# ---------------------------------------------------------------------------

_PERM_DESC = (
    "This is a segment of users who have browsed for White Wine content at least 2 times "
    "in the last 90 days."
)


def test_permutive_plain_english_r_letter():
    assert bs.permutive_plain_english(_PERM_DESC, "R") == "Regularly browses White Wine content"


def test_permutive_plain_english_f_letter():
    assert bs.permutive_plain_english(_PERM_DESC, "F") == "Frequently browses White Wine content"


def test_permutive_plain_english_o_letter():
    assert bs.permutive_plain_english(_PERM_DESC, "O") == "Occasionally browses White Wine content"


def test_permutive_plain_english_no_topic_in_description():
    # When the description doesn't match the regex, falls back gracefully.
    result = bs.permutive_plain_english("Some totally different text.", "R")
    assert result == "Regularly browses related content"


def test_permutive_plain_english_none_description():
    result = bs.permutive_plain_english(None, "R")
    assert result == "Regularly browses related content"


def test_permutive_plain_english_unknown_letter():
    # An unexpected letter falls back to the "" verb ("Browses").
    result = bs.permutive_plain_english(_PERM_DESC, "Z")
    assert result == "Browses White Wine content"


# ---------------------------------------------------------------------------
# ap_plain_english
# ---------------------------------------------------------------------------


def test_ap_plain_english_strips_boilerplate():
    raw = "We define these users as those who pay for a BT entertainment package"
    assert bs.ap_plain_english(raw) == "Pay for a BT entertainment package"


def test_ap_plain_english_strips_boilerplate_case_insensitive():
    raw = "WE DEFINE THESE USERS AS THOSE WHO subscribe to a streaming service"
    assert bs.ap_plain_english(raw) == "Subscribe to a streaming service"


def test_ap_plain_english_no_boilerplate_passthrough():
    raw = "Interested in home insurance products"
    assert bs.ap_plain_english(raw) == "Interested in home insurance products"


def test_ap_plain_english_capitalises_first_letter():
    raw = "We define these users as those who own a pet"
    result = bs.ap_plain_english(raw)
    assert result[0].isupper()


def test_ap_plain_english_empty_string_returns_empty():
    assert bs.ap_plain_english("") == ""


def test_ap_plain_english_none_returns_empty():
    assert bs.ap_plain_english(None) == ""


# ---------------------------------------------------------------------------
# normalise_permutive_row
# ---------------------------------------------------------------------------

# Row order: Name, Clean Audience Name, Code, Description, Size
_PERM_ROW_VALID = (
    "Food & Drink - White Wine fans (R & 90 Days)",  # Name
    "White Wine Fans",                                # Clean Audience Name
    189337.0,                                         # Code (float from xlsx)
    _PERM_DESC,                                       # Description
    68641,                                            # Size
)

_PERM_ROW_ZERO_REACH = (
    "Food & Drink - White Wine fans (R & 90 Days)",
    "White Wine Fans",
    189337.0,
    _PERM_DESC,
    0,
)

_PERM_ROW_BLANK_REACH = (
    "Food & Drink - White Wine fans (R & 90 Days)",
    "White Wine Fans",
    189337.0,
    _PERM_DESC,
    None,
)


def test_normalise_permutive_row_valid_returns_dict():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result is not None
    assert isinstance(result, dict)


def test_normalise_permutive_row_zero_reach_returns_none():
    assert bs.normalise_permutive_row(_PERM_ROW_ZERO_REACH) is None


def test_normalise_permutive_row_blank_reach_returns_none():
    assert bs.normalise_permutive_row(_PERM_ROW_BLANK_REACH) is None


def test_normalise_permutive_row_reach_is_int():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["reach"] == 68641
    assert isinstance(result["reach"], int)


def test_normalise_permutive_row_platform():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["platform"] == "Permutive"


def test_normalise_permutive_row_category():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["category"] == "Food & Drink"


def test_normalise_permutive_row_segment_name_from_clean_name():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["segment_name"] == "White Wine Fans"


def test_normalise_permutive_row_segment_name_falls_back_to_raw():
    # When clean name is blank, fall back to the raw Name field.
    row = (
        "Food & Drink - White Wine fans (R & 90 Days)",
        "",         # blank clean name
        189337.0,
        _PERM_DESC,
        68641,
    )
    result = bs.normalise_permutive_row(row)
    assert result["segment_name"] == "Food & Drink - White Wine fans (R & 90 Days)"


def test_normalise_permutive_row_code_float_cast_to_string():
    # Code 189337.0 (float) should become the string "189337".
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["code"] == "189337"


def test_normalise_permutive_row_frequency():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["frequency"] == "R"


def test_normalise_permutive_row_window():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["window"] == "90 Days"


def test_normalise_permutive_row_plain_english():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["plain_english"] == "Regularly browses White Wine content"


def test_normalise_permutive_row_icon_key():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["icon_key"] == "food-drink"


def test_normalise_permutive_row_private_keys_present():
    # _clean_name and _rank must be present for collapse to work.
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert "_clean_name" in result
    assert "_rank" in result


def test_normalise_permutive_row_private_clean_name_is_lowercase():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["_clean_name"] == "white wine fans"


def test_normalise_permutive_row_icon_key_non_empty():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["icon_key"] != ""


# ---------------------------------------------------------------------------
# normalise_ap_row
# ---------------------------------------------------------------------------

_AP_HEADERS = [
    "Name",
    "Cleaned name",
    "Cleaned Segment Code",
    "Cleaned Segment Description",
    "Segment Category",
    "Size",
]

_AP_ROW_VALID = (
    "BT Sport Fans",                                        # Name
    "BT Sport Fans (Clean)",                               # Cleaned name
    "AP_001",                                              # Cleaned Segment Code
    "We define these users as those who pay for a BT entertainment package",  # Description
    "Sports",                                              # Segment Category
    45000,                                                 # Size
)

_AP_ROW_ZERO_REACH = (
    "BT Sport Fans",
    "BT Sport Fans (Clean)",
    "AP_001",
    "We define these users as those who pay for a BT entertainment package",
    "Sports",
    0,
)

_AP_ROW_BLANK_REACH = (
    "BT Sport Fans",
    "BT Sport Fans (Clean)",
    "AP_001",
    "We define these users as those who pay for a BT entertainment package",
    "Sports",
    None,
)


def test_normalise_ap_row_valid_returns_dict():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result is not None
    assert isinstance(result, dict)


def test_normalise_ap_row_zero_reach_returns_none():
    assert bs.normalise_ap_row(_AP_ROW_ZERO_REACH, _AP_HEADERS) is None


def test_normalise_ap_row_blank_reach_returns_none():
    assert bs.normalise_ap_row(_AP_ROW_BLANK_REACH, _AP_HEADERS) is None


def test_normalise_ap_row_platform():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result["platform"] == "AP"


def test_normalise_ap_row_reach_is_int():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result["reach"] == 45000
    assert isinstance(result["reach"], int)


def test_normalise_ap_row_segment_name_from_cleaned_name():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result["segment_name"] == "BT Sport Fans (Clean)"


def test_normalise_ap_row_segment_name_falls_back_to_name():
    headers = ["Name", "Cleaned name", "Cleaned Segment Code",
               "Cleaned Segment Description", "Segment Category", "Size"]
    row = ("Raw Name", "", "AP_002", "Some description", "Sports", 1000)
    result = bs.normalise_ap_row(row, headers)
    assert result["segment_name"] == "Raw Name"


def test_normalise_ap_row_category_normalised():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result["category"] == "Sports"


def test_normalise_ap_row_plain_english_strips_boilerplate():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result["plain_english"] == "Pay for a BT entertainment package"


def test_normalise_ap_row_frequency_is_empty():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result["frequency"] == ""


def test_normalise_ap_row_window_is_empty():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result["window"] == ""


def test_normalise_ap_row_icon_key_non_empty():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result["icon_key"] != ""


def test_normalise_ap_row_icon_key_for_sports():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result["icon_key"] == "sports"


def test_normalise_ap_row_platform_non_empty():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result["platform"] != ""


# ---------------------------------------------------------------------------
# collapse_permutive_variants
# ---------------------------------------------------------------------------

def _make_perm_dict(clean_name, frequency, reach, segment_name=None):
    """Build a minimal normalised Permutive dict for collapse tests."""
    rank = bs._VARIANT_RANK.get(frequency, 0)
    return {
        "segment_name": segment_name or clean_name.title(),
        "platform": "Permutive",
        "reach": reach,
        "category": "Test",
        "description": "desc",
        "plain_english": "Browses test content",
        "code": "12345",
        "frequency": frequency,
        "window": "90 Days",
        "icon_key": "test",
        "_clean_name": clean_name.lower(),
        "_rank": rank,
    }


def test_collapse_single_row_returned():
    rows = [_make_perm_dict("white wine fans", "R", 50000)]
    result = bs.collapse_permutive_variants(rows)
    assert len(result) == 1


def test_collapse_r_preferred_over_f():
    rows = [
        _make_perm_dict("white wine fans", "F", 80000),
        _make_perm_dict("white wine fans", "R", 50000),
    ]
    result = bs.collapse_permutive_variants(rows)
    assert len(result) == 1
    assert result[0]["frequency"] == "R"


def test_collapse_r_preferred_over_o():
    rows = [
        _make_perm_dict("white wine fans", "O", 100000),
        _make_perm_dict("white wine fans", "R", 1000),
    ]
    result = bs.collapse_permutive_variants(rows)
    assert len(result) == 1
    assert result[0]["frequency"] == "R"


def test_collapse_f_preferred_over_o():
    rows = [
        _make_perm_dict("white wine fans", "O", 90000),
        _make_perm_dict("white wine fans", "F", 10000),
    ]
    result = bs.collapse_permutive_variants(rows)
    assert len(result) == 1
    assert result[0]["frequency"] == "F"


def test_collapse_tie_on_rank_higher_reach_wins():
    rows = [
        _make_perm_dict("white wine fans", "R", 50000),
        _make_perm_dict("white wine fans", "R", 80000),
    ]
    result = bs.collapse_permutive_variants(rows)
    assert len(result) == 1
    assert result[0]["reach"] == 80000


def test_collapse_different_clean_names_kept_separate():
    rows = [
        _make_perm_dict("white wine fans", "R", 50000),
        _make_perm_dict("football fans", "R", 30000),
    ]
    result = bs.collapse_permutive_variants(rows)
    assert len(result) == 2


def test_collapse_reach_not_summed():
    """Invariant: reach must be copied verbatim, never summed."""
    rows = [
        _make_perm_dict("white wine fans", "R", 50000),
        _make_perm_dict("white wine fans", "F", 80000),
        _make_perm_dict("white wine fans", "O", 20000),
    ]
    result = bs.collapse_permutive_variants(rows)
    # The winner is R; reach must be 50000, not 50000+80000+20000.
    assert result[0]["reach"] == 50000


def test_collapse_private_keys_stripped_from_output():
    rows = [_make_perm_dict("white wine fans", "R", 50000)]
    result = bs.collapse_permutive_variants(rows)
    assert "_clean_name" not in result[0]
    assert "_rank" not in result[0]


def test_collapse_output_platform_non_empty():
    rows = [_make_perm_dict("white wine fans", "R", 50000)]
    result = bs.collapse_permutive_variants(rows)
    assert result[0]["platform"] != ""


def test_collapse_output_icon_key_non_empty():
    rows = [_make_perm_dict("white wine fans", "R", 50000)]
    result = bs.collapse_permutive_variants(rows)
    assert result[0]["icon_key"] != ""


def test_collapse_empty_input_returns_empty():
    assert bs.collapse_permutive_variants([]) == []


# ---------------------------------------------------------------------------
# Key cross-cutting invariants
# ---------------------------------------------------------------------------


def test_permutive_row_reach_never_summed_by_itself():
    """A single valid row: reach is the original value, not modified."""
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result["reach"] == 68641


def test_ap_row_platform_always_non_empty():
    result = bs.normalise_ap_row(_AP_ROW_VALID, _AP_HEADERS)
    assert result is not None
    assert len(result["platform"]) > 0


def test_permutive_row_icon_key_always_non_empty():
    result = bs.normalise_permutive_row(_PERM_ROW_VALID)
    assert result is not None
    assert len(result["icon_key"]) > 0


def test_zero_reach_excluded_for_both_platforms():
    """Both platforms must return None for reach == 0."""
    perm = bs.normalise_permutive_row(_PERM_ROW_ZERO_REACH)
    ap = bs.normalise_ap_row(_AP_ROW_ZERO_REACH, _AP_HEADERS)
    assert perm is None
    assert ap is None
