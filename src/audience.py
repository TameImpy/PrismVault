"""Segment recommender for the brief pipeline (PRD #96 / slice #98).

Given an advertiser + topic (+ optional client brief), an LLM expands the input
into concept keywords and candidate categories, then a deterministic keyword
filter over the canonical `data/segments.csv` selects and ranks the most
relevant segments per platform. Reach is attached verbatim from the file and
never passes through the LLM.
"""
import csv
import json
import math
import os
import re

import config

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "segments.csv")

_EXPANSION_SYSTEM_PROMPT = (
    "You expand an advertiser brief into concept keywords for matching audience "
    "segments. Given an advertiser, topic and optional client brief, return a "
    "JSON object with two arrays: \"keywords\" (single concept words/short "
    "phrases, generously expanded with synonyms — e.g. the brand Lurpak becomes "
    "butter, dairy, spreads, baking, cooking) and \"categories\" (broad segment "
    "categories such as \"Food & Drink\", \"Gardening\", \"Auto\"). Return ONLY "
    "the JSON object, no prose."
)

# Shown to the user; also fed to the LLM so it never invents a combined figure.
NEVER_SUM_NOTE = (
    "Reach figures are per-segment and must not be summed — segments overlap "
    "and are not de-duplicated against each other."
)

# Platform framing, shown once as a list header (never repeated per row).
_PLATFORM_FRAMING = {
    "AP": "Modelled first-party audience — broad reach",
    "Permutive": "Behavioural — recently engaged browsers",
}
# Fixed display order (AP first: broad modelled reach, then behavioural).
_PLATFORM_ORDER = ["AP", "Permutive"]


def load_segments(csv_path=None):
    # type: (str) -> list
    """Load the canonical segment rows from data/segments.csv."""
    if csv_path is None:
        csv_path = DEFAULT_CSV_PATH
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _parse_expansion_json(raw):
    """Parse the model's response into {keywords, categories}; tolerant of noise."""
    empty = {"keywords": [], "categories": []}
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(
            line for line in cleaned.splitlines() if not line.strip().startswith("```")
        ).strip()
    if not cleaned.startswith("{"):
        return empty
    try:
        data = json.loads(cleaned)
    except (ValueError, TypeError):
        return empty
    keywords = [str(k).strip() for k in data.get("keywords", []) if str(k).strip()]
    categories = [str(c).strip() for c in data.get("categories", []) if str(c).strip()]
    return {"keywords": keywords, "categories": categories}


def expand_query(advertiser, topic, client_brief="", client=None, model=None):
    # type: (...) -> dict
    """LLM term-expansion: advertiser + topic + brief -> keywords + categories.

    `client` is injectable for testing so this never hits OpenAI in tests.
    Returns {"keywords": [...], "categories": [...]}; empty lists on any failure.
    """
    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
    if model is None:
        model = getattr(config, "CHAT_MODEL", "gpt-4o")

    user_prompt = "Advertiser: %s\nTopic: %s\nClient brief: %s" % (
        advertiser, topic, client_brief or "(none)",
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _EXPANSION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        return _parse_expansion_json(response.choices[0].message.content)
    except Exception:
        return {"keywords": [], "categories": []}


def _stem(token):
    """Very light suffix stripper so 'baking'/'bakers'/'baked' share a stem.

    Not a full stemmer — just enough to bridge common wording drift without a
    dependency. Short tokens are left alone to avoid over-collapsing.
    """
    for suffix in ("ing", "ers", "er", "ed", "es", "s"):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _tokenise(text):
    """Lowercase, stemmed word tokens from a blob of text."""
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", (text or "").lower())]


def _segment_haystack(segment):
    """Stemmed token set over a segment's name + description + category."""
    return set(_tokenise(
        "%s %s %s" % (segment.get("segment_name", ""),
                      segment.get("description", ""),
                      segment.get("category", ""))
    ))


def _segment_matches_keywords(segment, keywords):
    """True if any keyword stem appears in the segment's searchable text."""
    haystack = _segment_haystack(segment)
    for kw in keywords:
        if set(_tokenise(kw)) & haystack:
            return True
    return False


def _keyword_weights(segments, keywords):
    """Inverse-document-frequency weight per keyword: rarer keywords score higher.

    A keyword like "gut" that matches a handful of segments is far more
    discriminating than "food", which matches hundreds; weighting by log(N/df)
    lets a niche, on-topic segment outrank a generic high-reach one.
    """
    total = max(len(segments), 1)
    weights = {}
    for kw in keywords:
        kw_stems = set(_tokenise(kw))
        if not kw_stems:
            continue
        df = sum(1 for s in segments if kw_stems & _segment_haystack(s))
        if df:
            weights[kw] = math.log(1 + total / df)
    return weights


def _relevance_score(segment, keyword_weights):
    """Sum of matched keyword weights; matches in the name count for more."""
    haystack = _segment_haystack(segment)
    name_stems = set(_tokenise(segment.get("segment_name", "")))
    score = 0.0
    for kw, weight in keyword_weights.items():
        kw_stems = set(_tokenise(kw))
        if kw_stems & haystack:
            score += weight * (1.5 if (kw_stems & name_stems) else 1.0)
    return score


def _to_item(segment):
    """Project a raw segment row into a clean payload item (reach as int)."""
    try:
        reach = int(float(segment.get("reach")))
    except (TypeError, ValueError):
        reach = 0
    return {
        "segment_name": segment.get("segment_name", ""),
        "reach": reach,
        "platform": segment.get("platform", ""),
        "category": segment.get("category", ""),
        "plain_english": segment.get("plain_english", ""),
        "description": segment.get("description", ""),
        "code": segment.get("code", ""),
        "frequency": segment.get("frequency", ""),
        "window": segment.get("window", ""),
    }


# Below this many keyword hits, the ladder broadens to category-only matches.
_MIN_KEYWORD_MATCHES = 3


def _segment_in_categories(segment, categories):
    """True if the segment's category matches a candidate category (case-insensitive)."""
    seg_cat = (segment.get("category", "") or "").strip().lower()
    return any(seg_cat == (c or "").strip().lower() for c in categories)


def _match_with_fallback(segments, keywords, categories):
    """Keyword-match; if too few, broaden to include category-only matches."""
    keyword_matches = [s for s in segments if _segment_matches_keywords(s, keywords)]
    if len(keyword_matches) >= _MIN_KEYWORD_MATCHES or not categories:
        return keyword_matches

    matched = list(keyword_matches)
    seen = set(id(s) for s in matched)
    for s in segments:
        if id(s) not in seen and _segment_in_categories(s, categories):
            matched.append(s)
            seen.add(id(s))
    return matched


def recommend_segments(advertiser, topic, client_brief="", segments=None,
                       expansion=None, client=None, per_platform_limit=8):
    # type: (...) -> dict
    """Return the deterministic audience_segments payload."""
    if segments is None:
        segments = load_segments()

    keywords = list(expansion.get("keywords", [])) if expansion else []
    categories = list(expansion.get("categories", [])) if expansion else []

    matched = _match_with_fallback(segments, keywords, categories)
    # Relevance weights are computed over the whole catalogue so a rare, on-topic
    # keyword ("gut") outweighs a common one ("food"). Segments are then ranked
    # by relevance first, reach second — so the most relevant niche segments are
    # never buried under generic high-reach ones (and cut by the per-platform cap).
    weights = _keyword_weights(segments, keywords)

    platforms = []
    for platform in _PLATFORM_ORDER:
        rows = [s for s in matched if s.get("platform") == platform]
        rows.sort(
            key=lambda s: (_relevance_score(s, weights), _to_item(s)["reach"]),
            reverse=True,
        )
        platforms.append({
            "platform": platform,
            "framing": _PLATFORM_FRAMING[platform],
            "segments": [_to_item(s) for s in rows[:per_platform_limit]],
        })

    has_any = any(p["segments"] for p in platforms)
    return {
        "matched": has_any,
        "note": NEVER_SUM_NOTE,
        "query_terms": keywords,
        "platforms": platforms,
    }


def format_audience_segments(payload):
    # type: (dict) -> str
    """Render the payload as prompt-ready text for the {audience_segments} slot.

    Reach is quoted verbatim from the payload; the model is explicitly told to
    quote it as-is and never sum across segments.
    """
    if not payload.get("matched"):
        return (
            "No strongly-matched audience segments were found for this brief. "
            "State this honestly and do not invent segments or reach figures."
        )

    lines = [
        "Recommended audience segments, split by platform. Quote each reach "
        "figure verbatim; never add, total or sum reach across segments "
        "(segments overlap and are not de-duplicated).",
    ]
    for plat in payload["platforms"]:
        if not plat["segments"]:
            continue
        lines.append("")
        lines.append("%s (%s):" % (plat["platform"], plat["framing"]))
        for seg in plat["segments"]:
            lines.append(
                "- %s — reach %s. %s" % (
                    seg["segment_name"], "{:,}".format(seg["reach"]), seg["plain_english"],
                )
            )
    return "\n".join(lines)
