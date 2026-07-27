"""
Slide content step for the deck download (PRD #131).

Two jobs, deliberately kept apart:

- ``build_segment_rows`` / ``build_product_rows`` shape the structured payload
  the brief run already produced into slide rows. Pure, deterministic, and the
  only path numeric fields take — reach, CTR and viewability are placed exactly
  as the source data holds them and never pass through the model.
- ``generate_slide_content`` is the one LLM call, reduced to the two fields
  that genuinely need summarising: the advertiser-overview prose and the
  selection of 3 insights from the matched historical-research body.
"""
import json

from openai import OpenAI

import config
from src.historical_research import load_research_body

DECK_CONTENT_MODEL = getattr(config, "DECK_CONTENT_MODEL", "gpt-4o-mini")

# Tile capacity of the official template (see data/templates/TEMPLATE_MARKERS.md).
SEGMENT_TILES = 4
PRODUCT_TILES = 3
INSIGHT_TILES = 3

# Content caps that keep text inside its tile. Sizes and fonts are the
# template's business — these are purely about length.
OVERVIEW_MAX_WORDS = 60
INSIGHT_STAT_MAX_CHARS = 12
INSIGHT_TEXT_MAX_WORDS = 12


def build_segment_rows(payload, limit=SEGMENT_TILES):
    """Shape the ``audience_segments`` payload into ``{name, reach}`` tile rows.

    Segments are taken round-robin across the matched platforms so both
    audience engines are represented rather than the first one filling every
    tile. Reach is the payload's own figure — only thousands separators are
    added, and reach is never summed across segments (they overlap).
    Returns [] when nothing matched.
    """
    if not payload or not payload.get("matched"):
        return []

    queues = [list(plat.get("segments") or []) for plat in payload.get("platforms", [])]
    rows = []
    while len(rows) < limit and any(queues):
        for queue in queues:
            if not queue:
                continue
            seg = queue.pop(0)
            rows.append({
                "name": seg.get("segment_name", ""),
                "reach": _format_reach(seg.get("reach")),
            })
            if len(rows) >= limit:
                break
    return rows


def _format_reach(reach):
    """Thousands separators for a numeric reach; anything else passes through."""
    try:
        return "{:,}".format(int(reach))
    except (TypeError, ValueError):
        return str(reach or "")


def build_product_rows(rows, limit=PRODUCT_TILES):
    """Shape the ``format_recommendations`` rows into ``{format, ctr,
    viewability}`` tile rows, verbatim. Formats with no digital benchmarks keep
    their empty strings — a blank tile is honest, an invented number is not.
    """
    return [
        {
            "format": row.get("format", ""),
            "ctr": row.get("ctr", ""),
            "viewability": row.get("viewability", ""),
        }
        for row in (rows or [])[:limit]
    ]


SYSTEM_PROMPT = """You are a presentation content specialist. You write two things for a sales deck built from a strategic insights brief: a short advertiser overview, and a selection of historical-research insights.

Return ONLY valid JSON with this exact structure:

{
  "advertiser_overview": "<2-3 sentences, max 60 words>",
  "insights": [
    {"stat": "<the figure itself, max 12 characters, e.g. 68% or 2.4x>",
     "text": "<what the figure shows, max 12 words>"}
  ]
}

Rules:
- advertiser_overview: who the advertiser is, what they sell, and their current strategic focus. Flowing prose — no bullets, no markdown, no headings.
- insights: EXACTLY 3, chosen from the RESEARCH EXTRACT for relevance to this brief and this advertiser. Every figure must appear in the extract — never invent, round or re-scale one. Each "text" reads as a continuation of its figure.
- Return "insights": [] when no RESEARCH EXTRACT is supplied.
- No other fields and no commentary outside the JSON."""

USER_PROMPT_TEMPLATE = """Write the deck content for:

**Advertiser:** {advertiser}
**Topic:** {topic}
**KPI:** {kpi}

Brief:
{brief_content}
{research_section}"""

RESEARCH_SECTION_TEMPLATE = """
RESEARCH EXTRACT (the only source for "insights"):
{research_body}"""


def generate_slide_content(brief_content, topic, advertiser, kpi, historical_research=None):
    """Generate the deck's two prose fields.

    Args:
        brief_content: The full markdown insights brief.
        topic: The editorial topic.
        advertiser: The advertiser name.
        kpi: The campaign KPI.
        historical_research: The matched research payload from the brief run,
            or None. Its body is re-read from the catalogue so the insights are
            grounded in the same text the brief matched.

    Returns:
        ``{"advertiser_overview": str, "insights": [{"stat", "text"}]}``.
        ``insights`` is empty when no research matched, so the deck omits the
        Historical Insights slide entirely.
    """
    research_body = load_research_body(historical_research)
    research_section = (
        RESEARCH_SECTION_TEMPLATE.format(research_body=research_body) if research_body else ""
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        advertiser=advertiser,
        topic=topic,
        kpi=kpi,
        brief_content=brief_content,
        research_section=research_section,
    )

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=DECK_CONTENT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        max_tokens=800,
    )

    return _parse_and_validate(response.choices[0].message.content,
                               has_research=bool(research_body))


def _truncate_words(text, max_words):
    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words])
    return text


def _parse_and_validate(raw, has_research):
    """Parse the model's JSON and enforce the tile limits.

    A response that cannot be parsed degrades to empty content: the deck still
    builds and simply carries no prose, rather than the download failing.
    """
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(
            line for line in cleaned.split("\n") if not line.strip().startswith("```")
        )

    try:
        data = json.loads(cleaned)
    except (ValueError, TypeError):
        return {"advertiser_overview": "", "insights": []}

    overview = _truncate_words(str(data.get("advertiser_overview", "")), OVERVIEW_MAX_WORDS)

    insights = []
    if has_research:
        for item in data.get("insights") or []:
            stat = str(item.get("stat", "")).strip()[:INSIGHT_STAT_MAX_CHARS]
            text = _truncate_words(str(item.get("text", "")).strip(), INSIGHT_TEXT_MAX_WORDS)
            # Half a tile reads as a mistake — a figure needs its line, and a
            # line without a figure has nothing to sit under.
            if stat and text:
                insights.append({"stat": stat, "text": text})
            if len(insights) == INSIGHT_TILES:
                break

    return {"advertiser_overview": overview, "insights": insights}
