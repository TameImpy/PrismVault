"""
Slide content generator. Condenses an insights brief into structured,
slide-ready JSON using GPT-4o-mini.
"""
import json
from openai import OpenAI
import config
from src.segment_icons import icon_path

DECK_CONTENT_MODEL = getattr(config, "DECK_CONTENT_MODEL", "gpt-4o-mini")


def build_audience_slide_content(payload, per_platform=5):
    """Shape the deterministic audience_segments payload into slide rows.

    Reach is taken verbatim from the payload (never via the LLM) and only
    formatted with thousands separators; each row resolves to a bundled icon.
    Returns {matched, note, platforms:[{platform, framing, segments:[{name,
    why, reach, icon_path}]}]}. There is no summed total — reach must never be
    added across segments.
    """
    if not payload or not payload.get("matched"):
        return {
            "matched": False,
            "note": (payload or {}).get("note", ""),
            "platforms": [],
        }

    platforms = []
    for plat in payload.get("platforms", []):
        rows = []
        for seg in (plat.get("segments") or [])[:per_platform]:
            try:
                reach = int(seg.get("reach") or 0)
            except (TypeError, ValueError):
                reach = 0
            rows.append({
                "name": seg.get("segment_name", ""),
                "why": seg.get("plain_english", "") or seg.get("segment_name", ""),
                "reach": "{:,}".format(reach),
                "icon_path": icon_path(
                    category=seg.get("category"),
                    segment_name=seg.get("segment_name", ""),
                    icon_key=seg.get("icon_key"),
                ),
            })
        if rows:
            platforms.append({
                "platform": plat.get("platform", ""),
                "framing": plat.get("framing", ""),
                "segments": rows,
            })

    return {
        "matched": bool(platforms),
        "note": payload.get("note", ""),
        "platforms": platforms,
    }

SYSTEM_PROMPT = """You are a presentation content specialist. Your job is to condense a strategic insights brief into concise, slide-ready content for a 5-slide sales deck.

Return ONLY valid JSON with this exact structure:

{
  "stats": [
    {"value": "<max 5 chars, e.g. 40%, 2.7x, Q3>", "label": "<max 8 words>"}
  ],
  "left_heading": "Advertiser Overview",
  "left_bullets": ["<max 15 words each>", ...],
  "right_heading": "Editorial Insights & Alignment",
  "right_bullets": ["<max 15 words each>", ...],
  "messaging_heading": "Messaging & Tone",
  "messaging_items": [
    {"headline": "<max 6 words>", "detail": "<max 20 words>"}
  ],
  "products": [
    {"name": "<format name>", "metric": "<key metrics, max 10 words>"}
  ],
  "cta": "<1-2 sentence call to action to book a meeting>"
}

Rules:
- stats: EXACTLY 6 items. Pull the most impactful numbers from the At a Glance section and brief.
- left_bullets: 3-4 bullets about the advertiser (who they are, what they sell, recent strategy)
- right_bullets: 3-4 bullets about editorial insights and strategic alignment
- messaging_items: 3-4 recommendations with short headlines and detail
- products: 2-3 recommended ad formats with key metrics
- Be specific to the advertiser and topic — no generic filler
- Every bullet must be concise and punchy — this is for slides, not a document"""

USER_PROMPT_TEMPLATE = """Condense this insights brief into slide content for:

**Advertiser:** {advertiser}
**Topic:** {topic}
**KPI:** {kpi}

Brief:
{brief_content}"""


def generate_slide_content(brief_content, topic, advertiser, kpi):
    """Condense an insights brief into structured slide content.

    Args:
        brief_content: The full markdown insights brief.
        topic: The editorial topic.
        advertiser: The advertiser name.
        kpi: The campaign KPI.

    Returns:
        dict with structured slide content, validated and truncated.
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(
        advertiser=advertiser,
        topic=topic,
        kpi=kpi,
        brief_content=brief_content,
    )

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=DECK_CONTENT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        max_tokens=1200,
    )

    raw = response.choices[0].message.content
    return _parse_and_validate(raw)


def _truncate_words(text, max_words):
    """Truncate text to max_words."""
    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words])
    return text


def _parse_and_validate(raw):
    """Parse JSON from LLM response and enforce hard limits."""
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    data = json.loads(cleaned)

    # Validate and truncate stats
    stats = data.get("stats", [])[:6]
    while len(stats) < 6:
        stats.append({"value": "—", "label": "Data not available"})
    for stat in stats:
        stat["value"] = str(stat.get("value", "—"))[:5]
        stat["label"] = _truncate_words(str(stat.get("label", "")), 8)

    # Validate bullets
    left_bullets = [_truncate_words(b, 15) for b in data.get("left_bullets", [])[:4]]
    right_bullets = [_truncate_words(b, 15) for b in data.get("right_bullets", [])[:4]]

    # Validate messaging items
    messaging_items = []
    for item in data.get("messaging_items", [])[:4]:
        messaging_items.append({
            "headline": _truncate_words(str(item.get("headline", "")), 6),
            "detail": _truncate_words(str(item.get("detail", "")), 20),
        })

    # Validate products
    products = []
    for item in data.get("products", [])[:3]:
        products.append({
            "name": str(item.get("name", ""))[:30],
            "metric": _truncate_words(str(item.get("metric", "")), 10),
        })

    # Validate CTA
    cta = _truncate_words(str(data.get("cta", "Let's discuss how we can help.")), 30)

    return {
        "stats": stats,
        "left_heading": str(data.get("left_heading", "Advertiser Overview"))[:40],
        "left_bullets": left_bullets,
        "right_heading": str(data.get("right_heading", "Editorial Insights & Alignment"))[:40],
        "right_bullets": right_bullets,
        "messaging_heading": str(data.get("messaging_heading", "Messaging & Tone"))[:40],
        "messaging_items": messaging_items,
        "products": products,
        "cta": cta,
    }
