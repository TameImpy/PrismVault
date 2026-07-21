"""Deterministic entity resolution for the campaign-history lookup.

Pure module: no LLM, no I/O. Answers "have we run a direct campaign with
this advertiser?" by normalising the queried brand name and token-set
fuzzy-matching it against a roster of canonical advertiser names.

Public interface:
    normalise_name(name) -> str
    resolve(brand, roster) -> {"status", "matched_name", "candidates"}

`status` is one of {"match", "no_match"} in this slice.

Uses only the standard library (difflib) so the module stays pure and
dependency-free, which is what makes it exhaustively testable.
"""

import re
from difflib import SequenceMatcher

# Score (0-100) at or above which a candidate is a confident match.
MATCH_THRESHOLD = 88
# Score band [POSSIBLE_THRESHOLD, MATCH_THRESHOLD) is the ambiguous "verify"
# zone. Also, several candidates at/above MATCH_THRESHOLD is ambiguous.
POSSIBLE_THRESHOLD = 72

# Legal suffixes / corporate-form tokens stripped during normalisation so
# "Tesco Ltd" resolves to "Tesco". Kept small and conservative.
_LEGAL_SUFFIXES = {
    "ltd", "limited", "plc", "inc", "incorporated", "llc", "llp",
    "co", "corp", "corporation", "gmbh", "ag", "sa", "bv", "pty",
}

_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")


def normalise_name(name):
    # type: (str) -> str
    """Canonicalise a brand name for comparison.

    Lowercases, normalises ``&`` to ``and``, strips punctuation, and drops
    legal-suffix tokens (Ltd/Plc/Inc/...). Returns a whitespace-collapsed
    string of significant tokens.
    """
    text = (name or "").lower()
    text = text.replace("&", " and ")
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()

    tokens = [t for t in text.split(" ") if t and t not in _LEGAL_SUFFIXES]
    return " ".join(tokens)


def _ratio(a, b):
    # type: (str, str) -> float
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _token_set_ratio(a, b):
    # type: (str, str) -> float
    """Token-set similarity in [0, 100], after rapidfuzz's approach.

    A full-token subset (e.g. "jaguar" vs "jaguar landrover") scores 100,
    while partial-word overlaps that don't share a whole token (e.g. "sky"
    vs "skyscanner") stay low.
    """
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0

    intersection = " ".join(sorted(tokens_a & tokens_b))
    combined_a = " ".join(sorted(tokens_a & tokens_b) + sorted(tokens_a - tokens_b)).strip()
    combined_b = " ".join(sorted(tokens_a & tokens_b) + sorted(tokens_b - tokens_a)).strip()

    best = max(
        _ratio(intersection, combined_a),
        _ratio(intersection, combined_b),
        _ratio(combined_a, combined_b),
    )
    return best * 100.0


def _score(brand, candidate):
    # type: (str, str) -> float
    return _token_set_ratio(normalise_name(brand), normalise_name(candidate))


def resolve(brand, roster, aliases=None):
    # type: (str, list, dict) -> dict
    """Resolve a queried brand against the roster of canonical names.

    Three-way outcome:
      - ``match`` — one confident winner (exact normalised hit, or a single
        candidate at/above ``MATCH_THRESHOLD``). ``matched_name`` is set.
      - ``possible_match`` — ambiguous: either several strong candidates
        (e.g. "Virgin" → Virgin Media / Virgin Atlantic) or a single
        mid-band near-miss. ``matched_name`` is ``None`` and ``candidates``
        lists the names to verify; we assert nothing.
      - ``no_match`` — nothing crosses the possible band.

    ``aliases`` is an optional dict of ``{normalised_alias: canonical_name}``
    (a reactive, manually-maintained table). A known alias (e.g. "Coke" →
    "Coca-Cola") short-circuits to a confident match, provided its canonical
    is actually on the roster; a stale alias pointing off-roster is ignored.
    """
    normalised_brand = normalise_name(brand)

    # Reactive alias table: a known alias resolves straight to its canonical,
    # but only if that canonical is genuinely on the roster.
    if aliases and normalised_brand in aliases:
        canonical = aliases[normalised_brand]
        for candidate in roster:
            if normalise_name(candidate) == normalise_name(canonical):
                return {"status": "match", "matched_name": candidate, "candidates": []}

    # An exact normalised hit is unambiguous and wins over subset candidates
    # (so "Sky" resolves to "Sky", not to "Sky Betting And Gaming").
    for candidate in roster:
        if normalise_name(candidate) == normalised_brand and normalised_brand:
            return {"status": "match", "matched_name": candidate, "candidates": []}

    scored = [(candidate, _score(brand, candidate)) for candidate in roster]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    strong = [name for name, score in scored if score >= MATCH_THRESHOLD]
    in_band = [name for name, score in scored if score >= POSSIBLE_THRESHOLD]

    if len(strong) == 1:
        return {"status": "match", "matched_name": strong[0], "candidates": []}

    if in_band:
        # Multiple strong candidates, or a single mid-band near-miss: ambiguous.
        return {"status": "possible_match", "matched_name": None, "candidates": in_band}

    return {"status": "no_match", "matched_name": None, "candidates": []}
