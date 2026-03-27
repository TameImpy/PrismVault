from openai import OpenAI
import config
from src.vectorstore import search_transcripts
from src.web_search import research_advertiser
from src.audience import load_audience_data, get_topic_trends
from src.trends import get_trend_data
from src.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


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


def generate_insights(
    topic: str,
    advertiser: str,
    kpi: str,
    include_google_trends: bool = True,
) -> dict:
    """Main pipeline: gather data from all sources, synthesise with GPT-4o.

    Returns dict with keys: content, sources, research_skills,
    audience_timing, google_trends.
    """
    # 1. Search vector DB for editorial insights
    results = search_transcripts(topic, n_results=5)
    editorial_insights, sources = _format_editorial_insights(results)

    # 2. Skill-based advertiser research
    skill_results = research_advertiser(advertiser)
    advertiser_research = _format_advertiser_research(skill_results)

    # 3. Load audience trend data
    df = load_audience_data()
    audience_timing = get_topic_trends(df, topic)

    # 4. Optionally pull Google Trends
    if include_google_trends:
        trend_data = get_trend_data(topic)
        google_trends = trend_data["summary"]
    else:
        google_trends = "Google Trends data not requested."

    # 5. Assemble prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        topic=topic,
        advertiser=advertiser,
        advertiser_kpi=kpi,
        editorial_insights=editorial_insights,
        advertiser_research=advertiser_research,
        audience_timing=audience_timing,
        google_trends=google_trends,
    )

    # 6. Call GPT-4o
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )

    content = response.choices[0].message.content

    return {
        "content": content,
        "sources": sources,
        "research_skills": skill_results,
        "audience_timing": audience_timing,
        "google_trends": google_trends,
    }
