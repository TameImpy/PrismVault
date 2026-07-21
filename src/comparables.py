"""Comparables engine: on a genuine no-match, surface 2-3 brands we HAVE
worked with that are similar to the queried advertiser.

Tier 1 (precision), this slice: Python filters the roster to a
vertical-matched shortlist, a structured LLM call picks 2-3 and explains, and
the pure validator drops any brand not on the roster. Each survivor is
rendered as name + why-similar + that brand's best-performing format.

The LLM pick step is injected (``pick_fn``) so the tier logic is testable
without the model. Tier 2 (recall) and thin-roster degradation arrive in a
later slice; the return shape already carries ``tier``/``note`` for that.
"""

import json

from src.comparables_validator import validate_comparables
from src.campaign_history import brand_best_format_line

# How many comparables we aim to surface.
MAX_COMPARABLES = 3
# A vertical shortlist smaller than this is "thin" and falls through to Tier 2.
MIN_SHORTLIST = 2

NO_CLOSE_COMPARABLES_NOTE = (
    "No close comparables in our direct client roster — better to make no "
    "comparison than a nonsensical one."
)


def _shortlist_by_vertical(query_vertical, roster, brand_verticals, advertiser):
    # type: (str, list, dict, str) -> list
    """Roster brands in the query's vertical, excluding the queried brand."""
    if not query_vertical:
        return []
    from src.entity_resolution import normalise_name
    advertiser_norm = normalise_name(advertiser)
    return [
        brand for brand in roster
        if brand_verticals.get(brand) == query_vertical
        and normalise_name(brand) != advertiser_norm
    ]


def _attach_best_formats(comparables, campaign_rows):
    # type: (list, list) -> list
    for comparable in comparables:
        comparable["best_format"] = brand_best_format_line(comparable["brand"], campaign_rows)
    return comparables


def _widen_note(query_vertical):
    # type: (str) -> str
    if query_vertical:
        return (
            "No/thin direct clients in the '%s' vertical, so we widened once to "
            "adjacent verticals — these are the closest comparable clients we have."
            % query_vertical
        )
    return (
        "We couldn't place this advertiser in a vertical, so we widened across "
        "the full client roster for the closest comparable clients."
    )


def get_comparables(advertiser, query_vertical, roster, brand_verticals,
                    campaign_rows, pick_fn, full_pick_fn=None):
    # type: (str, str, list, dict, list, callable, callable) -> dict
    """Comparables for a no-match advertiser, with Tier-1 precision then
    Tier-2 recall.

    - **Tier 1**: if the query's vertical yields a shortlist of at least
      ``MIN_SHORTLIST`` brands, ``pick_fn(advertiser, shortlist)`` picks from
      it. Validated survivors → returned as tier 1.
    - **Tier 2**: if the shortlist is empty/thin, or Tier 1 yields nothing
      valid, fall through once to the full roster. ``full_pick_fn(advertiser,
      candidates, brand_verticals)`` applies world knowledge a category column
      can't encode; a widen note is surfaced. (Falls back to ``pick_fn`` if no
      ``full_pick_fn`` is given.)
    - If Tier 2 still yields nothing valid → "no close comparables".

    Every returned brand is validated against the roster, so no brand we
    haven't worked with can ever appear. Returns ``{"comparables", "tier",
    "note", "widened"}``.
    """
    shortlist = _shortlist_by_vertical(query_vertical, roster, brand_verticals, advertiser)

    if len(shortlist) >= MIN_SHORTLIST:
        picks = pick_fn(advertiser, shortlist) or []
        validated = validate_comparables(picks, roster)[:MAX_COMPARABLES]
        if validated:
            comparables = _attach_best_formats(validated, campaign_rows)
            return {"comparables": comparables, "tier": 1, "note": "", "widened": False}

    # Tier 2 (recall): full-roster reasoning pass, still post-validated.
    from src.entity_resolution import normalise_name
    advertiser_norm = normalise_name(advertiser)
    full_candidates = [b for b in roster if normalise_name(b) != advertiser_norm]

    if full_pick_fn is not None:
        picks = full_pick_fn(advertiser, full_candidates, brand_verticals) or []
    else:
        picks = pick_fn(advertiser, full_candidates) or []
    validated = validate_comparables(picks, roster)[:MAX_COMPARABLES]

    if validated:
        comparables = _attach_best_formats(validated, campaign_rows)
        return {"comparables": comparables, "tier": 2,
                "note": _widen_note(query_vertical), "widened": True}

    return {"comparables": [], "tier": 2,
            "note": NO_CLOSE_COMPARABLES_NOTE, "widened": True}


def format_comparables_block(advertiser, result):
    # type: (str, dict) -> str
    """Render the validated comparables as a prompt-ready text block.

    Empty comparables → "" in this slice (the "no close comparables" wording is
    added with the Tier-2 degradation slice).
    """
    comparables = result.get("comparables", [])
    note = result.get("note", "")
    if not comparables:
        # Surface the honest "no close comparables" degradation, if present.
        return note or ""

    lines = [
        "Comparable brands we have worked with (no direct history with '%s'):"
        % advertiser
    ]
    for comparable in comparables:
        best_format = comparable.get("best_format", "")
        suffix = (" — best format: %s" % best_format) if best_format else ""
        lines.append("- %s — %s%s" % (comparable["brand"], comparable["why_similar"], suffix))
    if note:
        lines.append("Note: %s" % note)
    return "\n".join(lines)


def pick_comparables_llm(advertiser, shortlist):
    # type: (str, list) -> list
    """Default structured LLM pick step (not unit-tested — raw model call).

    Returns a list of ``{"brand", "why_similar"}``. Only fired on the no-match
    path by the pipeline. Brands are still validated downstream.
    """
    if not shortlist:
        return []

    from openai import OpenAI
    import config

    prompt = (
        "We have no direct campaign history with the advertiser \"%s\".\n"
        "From ONLY this list of brands we HAVE worked with, pick the 2-3 most "
        "similar and give a one-line reason for each:\n%s\n\n"
        "Return ONLY a JSON object of the form "
        '{\"comparables\": [{\"brand\": <name from the list, verbatim>, '
        '\"why_similar\": <one line>}]}. Pick nothing outside the list.'
        % (advertiser, "\n".join("- %s" % b for b in shortlist))
    )

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise brand-similarity analyst. Output only JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        data = json.loads(response.choices[0].message.content)
    except (ValueError, TypeError):
        return []
    return data.get("comparables", []) if isinstance(data, dict) else []


def pick_comparables_full_roster_llm(advertiser, candidates, brand_verticals):
    # type: (str, list, dict) -> list
    """Default Tier-2 (recall) pick step over the full roster (not unit-tested).

    Hands the model the full client roster with each brand's vertical as a
    hint, so it can apply world knowledge a category column can't encode
    (e.g. Sky → NowTV). Brands are still validated downstream.
    """
    if not candidates:
        return []

    from openai import OpenAI
    import config

    listed = "\n".join(
        "- %s (%s)" % (b, brand_verticals.get(b, "vertical unknown")) for b in candidates
    )
    prompt = (
        "We have no direct campaign history with the advertiser \"%s\", and no "
        "close match in its own vertical. From ONLY this full list of brands we "
        "HAVE worked with (vertical shown as a hint), pick the 2-3 genuinely "
        "most similar and give a one-line reason for each. If NONE are genuinely "
        "comparable, return an empty list rather than reaching for a weak fit.\n"
        "%s\n\n"
        "Return ONLY a JSON object of the form "
        '{\"comparables\": [{\"brand\": <name from the list, verbatim>, '
        '\"why_similar\": <one line>}]}.'
        % (advertiser, listed)
    )

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise brand-similarity analyst. Output only JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        data = json.loads(response.choices[0].message.content)
    except (ValueError, TypeError):
        return []
    return data.get("comparables", []) if isinstance(data, dict) else []
