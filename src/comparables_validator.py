"""Comparables validator — the trust guardrail (pure, deep module).

The comparables engine asks an LLM to name brands similar to the queried
advertiser. This module enforces the hard guarantee that every named brand is
a *real client*: any pick whose brand is not present in the roster is dropped.

Pure function over data — no LLM, no I/O — so it is deterministic and
exhaustively testable. Matching uses the resolver's normalisation, so a pick
of "coca cola" validates against the roster's "Coca-Cola" and is returned with
the canonical roster spelling.
"""

from src.entity_resolution import normalise_name


def validate_comparables(picks, roster):
    # type: (list, list) -> list
    """Return only the picks whose brand exists in the roster.

    ``picks`` is a list of ``{"brand", "why_similar"}`` dicts (as returned by
    the LLM). Each surviving pick's ``brand`` is rewritten to the canonical
    roster spelling. Unknown brands are dropped.
    """
    canonical_by_norm = {normalise_name(name): name for name in roster}

    validated = []
    for pick in picks or []:
        brand = (pick.get("brand") or "").strip()
        canonical = canonical_by_norm.get(normalise_name(brand))
        if not canonical:
            continue
        validated.append({
            "brand": canonical,
            "why_similar": (pick.get("why_similar") or "").strip(),
        })
    return validated
