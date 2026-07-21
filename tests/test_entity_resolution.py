"""Tests for the deterministic entity-resolution module.

The resolver is a pure function over data: no LLM, no I/O. These tests
exercise its public interface (`resolve` / `normalise_name`) and assert
observable behaviour — the three highest-risk properties being the
confident match, the false-positive guard, and suffix/punctuation
normalisation.
"""

from src.entity_resolution import resolve, normalise_name

ROSTER = [
    "Tesco",
    "Aldi",
    "Jaguar Landrover",
    "Skyscanner",
    "BBC Good Food",
    "Coca-Cola",
]


def test_confident_exact_match():
    result = resolve("Tesco", ROSTER)

    assert result["status"] == "match"
    assert result["matched_name"] == "Tesco"


def test_token_subset_matches():
    # "Jaguar" is a full-token subset of "Jaguar Landrover" — same brand.
    result = resolve("Jaguar", ROSTER)

    assert result["status"] == "match"
    assert result["matched_name"] == "Jaguar Landrover"


def test_false_positive_guard_sky_not_skyscanner():
    # The headline false positive from the old substring match. "Sky" shares
    # no whole token with "Skyscanner", so it must NOT resolve to it.
    result = resolve("Sky", ROSTER)

    assert result["status"] == "no_match"
    assert result["matched_name"] is None


def test_legal_suffix_normalisation():
    # "Tesco Ltd." with a trailing suffix + punctuation resolves to "Tesco".
    result = resolve("Tesco Ltd.", ROSTER)

    assert result["status"] == "match"
    assert result["matched_name"] == "Tesco"


def test_punctuation_normalisation():
    # "Coca Cola" (no hyphen) resolves to the hyphenated roster entry.
    result = resolve("Coca Cola", ROSTER)

    assert result["status"] == "match"
    assert result["matched_name"] == "Coca-Cola"


def test_ampersand_normalisation():
    result = normalise_name("Marks & Spencer") == normalise_name("Marks and Spencer")
    assert result is True


def test_genuine_no_match():
    result = resolve("Netflix", ROSTER)

    assert result["status"] == "no_match"
    assert result["matched_name"] is None
    assert result["candidates"] == []


# --- Three-state: the ambiguous "possible_match" band (#109) ---

AMBIGUOUS_ROSTER = ["Virgin Media", "Virgin Atlantic", "Tesco", "Audi"]


def test_ambiguous_name_is_possible_match_with_candidates():
    # "Virgin" is a whole-token subset of two different roster brands, so we
    # must not assert either — flag both for the salesperson to verify.
    result = resolve("Virgin", AMBIGUOUS_ROSTER)

    assert result["status"] == "possible_match"
    assert result["matched_name"] is None
    assert set(result["candidates"]) == {"Virgin Media", "Virgin Atlantic"}


def test_mid_band_near_miss_is_possible_not_match():
    # "Aldi" vs "Audi" (~75) is a risky near-miss: flag it, never assert it.
    result = resolve("Aldi", AMBIGUOUS_ROSTER)

    assert result["status"] == "possible_match"
    assert result["matched_name"] is None
    assert result["candidates"] == ["Audi"]


def test_exact_match_wins_over_subset_candidates():
    # An exact normalised hit is confident even when subset candidates exist.
    result = resolve("Virgin Media", AMBIGUOUS_ROSTER)

    assert result["status"] == "match"
    assert result["matched_name"] == "Virgin Media"
