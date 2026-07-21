import logging

from openai import OpenAI
import config
# NOTE: Editorial vector search disabled for now (Phase 2). The vector-DB
# layer (src.vectorstore / src.embeddings / ingest.py) is left intact and
# dormant; re-enable by restoring the import and the search call below.
# from src.vectorstore import search_transcripts
from src.web_search import research_advertiser
from src.audience import expand_query, recommend_segments, format_audience_segments
from src.trends import get_trend_data
from src.brief import summarise_brief
from src.formats import load_format_data, load_format_names, validate_format_names
from src.campaign_history import get_campaign_summary, load_campaign_rows
from src.alias_table import DEFAULT_UNMATCHED_LOG_PATH
from src.comparables import (
    get_comparables,
    format_comparables_block,
    pick_comparables_llm,
    pick_comparables_full_roster_llm,
)
from src.vertical_classifier import (
    load_brand_verticals,
    load_taxonomy,
    classify_new_brands_llm,
)
from src.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


def _run_format_name_guardrail(content):
    # type: (str) -> dict
    """Validate recommended format names against the confirmed catalogue.

    Best-effort and non-blocking: any unrecognised (format-like) names are
    logged server-side so drift/hallucination is surfaced without failing the
    user's response. Never raises.
    """
    try:
        valid_names = load_format_names()
        result = validate_format_names(content or "", valid_names)
    except Exception:  # pragma: no cover - guardrail must never break a response
        logger.exception("Format-name guardrail failed; continuing without it.")
        return {"recognised": [], "unrecognised": []}

    if result["unrecognised"]:
        logger.warning(
            "Format-name guardrail flagged unrecognised format names in the "
            "generated brief: %s",
            result["unrecognised"],
        )
    return result


def _format_editorial_insights(results: dict) -> tuple[str, list[dict]]:
    """Format ChromaDB results into attributed text and source list."""
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    if not documents:
        return "No editorial insights found for this topic.", []

    formatted = []
    sources = []
    for doc, meta in zip(documents, metadatas):
        attribution = f"[Editor: {meta['editor_name']}, {meta['publication']}, {meta['date']}]"
        formatted.append(f"{attribution}:\n{doc}")
        source = {
            "editor": meta["editor_name"],
            "publication": meta["publication"],
            "date": meta["date"],
            "vertical": meta["vertical"],
            "topics": meta["topics"],
        }
        if source not in sources:
            sources.append(source)

    return "\n\n".join(formatted), sources


def _format_advertiser_research(skill_results: list[dict]) -> str:
    """Format skill results into a labelled block for the prompt."""
    sections = []
    for sr in skill_results:
        sections.append(f"**{sr['skill_name']}:**\n{sr['processed_summary']}")
    return "\n\n".join(sections) if sections else "No advertiser research available."


def _build_comparables_block(advertiser, topic):
    # type: (str, str) -> str
    """On a no-match, infer the advertiser's vertical, run the comparables
    engine (Tier 1), and render the validated result for the prompt.

    Best-effort and non-blocking: never raises into the pipeline.
    """
    try:
        rows = load_campaign_rows()
        roster = sorted({r.get("advertiser", "") for r in rows if r.get("advertiser")})
        brand_verticals = load_brand_verticals()
        taxonomy = load_taxonomy()

        classified = classify_new_brands_llm([advertiser], {advertiser: topic}, taxonomy)
        query_vertical = classified.get(advertiser, "")

        result = get_comparables(
            advertiser, query_vertical, roster, brand_verticals, rows,
            pick_comparables_llm, full_pick_fn=pick_comparables_full_roster_llm,
        )
        return format_comparables_block(advertiser, result)
    except Exception:  # pragma: no cover - comparables must never break a response
        logger.exception("Comparables engine failed; continuing without it.")
        return ""


def generate_insights(
    topic: str,
    advertiser: str,
    kpi: str,
    include_google_trends: bool = True,
    client_brief: str = "",
) -> dict:
    """Main pipeline: gather data from all sources, synthesise with GPT-4o.

    Returns dict with keys: content, sources, research_skills,
    audience_segments, google_trends.
    """
    # 1. Editorial vector search disabled for now (Phase 2). `sources` stays an
    #    empty list so the return contract is unchanged for the API/frontend.
    sources = []

    # 2. Skill-based advertiser research
    skill_results = research_advertiser(advertiser)
    advertiser_research = _format_advertiser_research(skill_results)

    # 3. Recommend audience segments (LLM term-expansion + deterministic filter).
    #    Reach is attached verbatim from data/segments.csv — never via the LLM.
    expansion = expand_query(advertiser, topic, client_brief)
    audience_segments = recommend_segments(advertiser, topic, client_brief, expansion=expansion)
    audience_segments_text = format_audience_segments(audience_segments)

    # 4. Optionally pull Google Trends
    if include_google_trends:
        trend_data = get_trend_data(topic)
        google_trends = trend_data["summary"]
    else:
        google_trends = "Google Trends data not requested."

    # 5. Load format recommendations
    format_recommendations = load_format_data()

    # 6. Look up direct campaign history (deterministic resolution). Enable
    #    miss-logging so the reactive alias table can grow from real queries.
    campaign_result = get_campaign_summary(advertiser, log_path=DEFAULT_UNMATCHED_LOG_PATH)
    campaign_history = campaign_result["summary"]

    # 6b. On a genuine no-match ONLY, surface validated comparable brands.
    #     Matched / possible-match paths make no extra LLM call.
    if campaign_result.get("status") == "no_match":
        comparables_block = _build_comparables_block(advertiser, topic)
        if comparables_block:
            campaign_history = campaign_history + "\n\n" + comparables_block

    # 7. Summarise client brief if provided
    client_brief_summary = summarise_brief(client_brief)

    # 8. Assemble prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        topic=topic,
        advertiser=advertiser,
        advertiser_kpi=kpi,
        advertiser_research=advertiser_research,
        audience_segments=audience_segments_text,
        google_trends=google_trends,
        format_recommendations=format_recommendations,
        campaign_history=campaign_history,
        client_brief=client_brief_summary,
    )

    # 9. Call GPT-4o
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=4096,
    )

    content = response.choices[0].message.content

    # 10. Guardrail: flag any recommended format names not in the catalogue
    # (best-effort, non-blocking — logs server-side, never fails the response).
    _run_format_name_guardrail(content)

    return {
        "content": content,
        "sources": sources,
        "research_skills": skill_results,
        "audience_segments": audience_segments,
        "google_trends": google_trends,
        "format_recommendations": format_recommendations,
        "campaign_history": campaign_history,
        "client_brief_summary": client_brief_summary,
    }
