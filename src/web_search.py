import glob
import os
import re
import time
from datetime import datetime

import yaml
from ddgs import DDGS
from openai import OpenAI

import config

SEARCH_RETRIES = 3
SEARCH_RETRY_DELAY = 2  # seconds between retries
SEARCH_DELAY = 1.5  # seconds between successive queries to avoid rate limits

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")

# The client brief reaches the summariser as context, not as a search term.
# It arrives already summarised, so this is a backstop against an outlier.
MAX_BRIEF_CHARS = 800

TOPIC_SECTION_HEADER = 'TOPIC-SPECIFIC RESULTS — {brand} in relation to "{topic}":'
GENERAL_SECTION_HEADER = 'GENERAL BRAND RESULTS — {brand} only, not specific to "{topic}":'
NO_TOPIC_RESULTS = '(none — searches for {brand} and "{topic}" returned nothing)'

# How a skill should let the topic reshape its summary. `lead` puts topic
# material first; `supplement` keeps the skill's general picture whole and adds
# a topic passage to it. Company Overview is `supplement` because it feeds the
# brief's Advertiser Overview section, which needs brand-general facts (scale,
# positioning, group structure) whatever the brief is about — demoting those
# would make thick-roster briefs worse, not better (#155 AC4).
TOPIC_FOCUS_LEAD = "lead"
TOPIC_FOCUS_SUPPLEMENT = "supplement"

# Appended to every skill prompt when the brief carries a topic. Composed here
# rather than written into each skills/*.md so that adding a new skill file
# still needs no code change — and so no skill can quietly opt out of the
# instruction that stops general brand material being passed off as topic
# material (#155).
_DIRECTIVE_HEADER = """

---

## Brief context

This research supports an advertising brief for {brand} on the subject of: **{topic}**.{brief_line}

The search results above are split into two sections. Treat them differently:
"""

_LEAD_RULES = """
- Lead with the TOPIC-SPECIFIC results. What they say about {brand} in relation to {topic} is the point of this summary.
- Draw on the GENERAL BRAND RESULTS only as supporting context, and only where it bears on {topic}."""

_SUPPLEMENT_RULES = """
- Keep the general picture of {brand} complete — what they do, scale, market position, customers, positioning, group structure. A brief needs that context whatever its subject, so do not drop it.
- Then add, as its own passage, what the TOPIC-SPECIFIC results say about {brand} in relation to {topic}."""

_SHARED_RULES = """
- If the TOPIC-SPECIFIC section is empty or thin, say so plainly in a sentence — for example "Little material found on {brand} in relation to {topic}." Do not pad the summary with general brand material presented as though it answered the topic.
- Never imply that general brand material is about {topic}."""

BRIEF_CONTEXT_LINE = "\n\nThe client's brief: {client_brief}"


def _build_topic_directive(brand_name, topic, client_brief, topic_focus):
    # type: (str, str, str, str) -> str
    """Compose the topic instruction appended to a skill's prompt.

    `topic_focus` selects how hard the topic reshapes the summary; the rule
    against dressing general brand material up as topic material is shared by
    both, so no skill can opt out of it.
    """
    brief = (client_brief or "").strip()[:MAX_BRIEF_CHARS]
    rules = (
        _SUPPLEMENT_RULES if topic_focus == TOPIC_FOCUS_SUPPLEMENT else _LEAD_RULES
    )
    return (_DIRECTIVE_HEADER + rules + _SHARED_RULES).format(
        brand=brand_name,
        topic=topic,
        brief_line=BRIEF_CONTEXT_LINE.format(client_brief=brief) if brief else "",
    )


def load_skills() -> list[dict]:
    """Load all research skill definitions from skills/*.md files.

    Each skill file has YAML frontmatter (name, description, queries,
    max_results_per_query) and a prompt body below the frontmatter.
    """
    skills = []
    for path in sorted(glob.glob(os.path.join(SKILLS_DIR, "*.md"))):
        with open(path) as f:
            raw = f.read()

        # Split YAML frontmatter from prompt body
        match = re.match(r"^---\n(.+?)\n---\n(.+)", raw, re.DOTALL)
        if not match:
            continue

        meta = yaml.safe_load(match.group(1))
        prompt_body = match.group(2).strip()

        skills.append({
            "name": meta.get("name", os.path.basename(path)),
            "description": meta.get("description", ""),
            "queries": meta.get("queries", []),
            # Topic-anchored searches, run only when the brief supplies a topic.
            "topic_queries": meta.get("topic_queries", []),
            "topic_focus": meta.get("topic_focus", TOPIC_FOCUS_LEAD),
            "max_results_per_query": meta.get("max_results_per_query", 3),
            "timelimit": meta.get("timelimit", "y"),
            "prompt": prompt_body,
            "file": os.path.basename(path),
        })

    return skills


def _run_search(query, max_results, timelimit="y"):
    """Run a single DuckDuckGo search with retries for transient failures."""
    for attempt in range(SEARCH_RETRIES):
        try:
            ddgs = DDGS()
            return list(ddgs.text(query, max_results=max_results, timelimit=timelimit))
        except Exception as e:
            if attempt < SEARCH_RETRIES - 1:
                time.sleep(SEARCH_RETRY_DELAY)
            else:
                raise e
    return []


def _normalise_topic(topic) -> str:
    """The brief's topic as a clean string; absent and blank both become ''."""
    return (topic or "").strip()


def _skill_queries(skill: dict, topic) -> list:
    """Return [(query_template, topic_anchored)] for this run.

    A template is topic-anchored if it mentions {topic}. With no topic in the
    brief those templates are dropped rather than substituted blank — an empty
    substitution would silently widen the search back into a brand-only one.
    """
    templates = list(skill.get("queries") or []) + list(skill.get("topic_queries") or [])
    has_topic = bool(_normalise_topic(topic))

    selected = []
    for template in templates:
        anchored = "{topic}" in template
        if anchored and not has_topic:
            continue
        selected.append((template, anchored))
    return selected


def _dedupe_results(results: list) -> list:
    """Collapse hits found by more than one query, preserving first-seen order.

    A result found by both a brand query and a topic query is topic material:
    the topic flag wins, so shared hits are not stranded in the general pile.
    """
    seen = {}
    order = []
    for r in results:
        key = (r.get("href") or "").strip().lower() or f"title:{r.get('title', '')}"
        if key in seen:
            if r.get("topic_anchored"):
                seen[key]["topic_anchored"] = True
            continue
        seen[key] = r
        order.append(key)
    return [seen[k] for k in order]


def _render_results(results: list) -> str:
    """Render search hits as a markdown bullet list (include URLs)."""
    lines = []
    for r in results:
        href = r.get("href", "")
        if href:
            lines.append(f"- [{r['title']}]({href}): {r['body']}")
        else:
            lines.append(f"- **{r['title']}**: {r['body']}")
    return "\n".join(lines)


def _format_results_block(results: list, brand_name: str, topic) -> str:
    """Format search hits for the summariser prompt.

    With a topic, results are split by provenance so the model can tell what
    was actually found on the subject from what merely concerns the brand —
    and so an empty topic section reads as an absence rather than as licence
    to substitute general brand material for it.

    With no topic, this is the flat list the prompt has always seen.
    """
    topic = _normalise_topic(topic)
    if not topic:
        return _render_results(results)

    topical = [r for r in results if r.get("topic_anchored")]
    general = [r for r in results if not r.get("topic_anchored")]

    return "\n".join([
        TOPIC_SECTION_HEADER.format(brand=brand_name, topic=topic),
        _render_results(topical) if topical
        else NO_TOPIC_RESULTS.format(brand=brand_name, topic=topic),
        "",
        GENERAL_SECTION_HEADER.format(brand=brand_name, topic=topic),
        _render_results(general) if general else "(none)",
    ])


def run_skill(skill: dict, brand_name: str, topic: str = "", client_brief: str = "") -> dict:
    """Execute a single research skill against a brand, on a given topic.

    Runs the skill's search queries — brand-only plus, when the brief supplies
    a topic, the skill's topic-anchored queries — then passes the raw results
    through GPT-4o with the skill's prompt to produce a processed summary.

    `topic` shapes what is searched for; `client_brief` is context for the
    summariser only and is never turned into a search query.

    Returns dict with keys: skill_name, raw_results, processed_summary, error.
    """
    skill_name = skill["name"]
    topic = _normalise_topic(topic)
    all_results = []

    timelimit = skill.get("timelimit", "y")

    try:
        for i, (query_template, anchored) in enumerate(_skill_queries(skill, topic)):
            if i > 0:
                time.sleep(SEARCH_DELAY)
            query = (
                query_template
                .replace("{brand}", brand_name)
                .replace("{topic}", topic)
                .replace("{year}", str(datetime.now().year))
            )
            results = _run_search(query, skill["max_results_per_query"], timelimit=timelimit)
            for r in results:
                all_results.append(dict(r, topic_anchored=anchored))
    except Exception as e:
        return {
            "skill_name": skill_name,
            "raw_results": [],
            "processed_summary": f"Search failed: {e}",
            "error": str(e),
        }

    all_results = _dedupe_results(all_results)

    if not all_results:
        subject = f"{brand_name} and \"{topic}\"" if topic else brand_name
        return {
            "skill_name": skill_name,
            "raw_results": [],
            "processed_summary": f"No search results found for {subject}.",
            "error": None,
        }

    raw_results_str = _format_results_block(all_results, brand_name, topic)

    # Build the processing prompt from the skill template
    processing_prompt = skill["prompt"].replace(
        "{brand}", brand_name
    ).replace(
        "{topic}", topic
    ).replace(
        "{search_results}", raw_results_str
    )

    if topic:
        processing_prompt += _build_topic_directive(
            brand_name, topic, client_brief, skill.get("topic_focus", TOPIC_FOCUS_LEAD)
        )

    # Process through GPT-4o
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=config.CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are a research analyst producing concise, factual summaries from search results."},
                {"role": "user", "content": processing_prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        processed_summary = response.choices[0].message.content
    except Exception as e:
        processed_summary = f"Processing failed: {e}\n\nRaw results:\n{raw_results_str}"

    return {
        "skill_name": skill_name,
        "raw_results": [
            {
                "title": r["title"],
                "body": r["body"],
                "href": r.get("href", ""),
                "topic_anchored": bool(r.get("topic_anchored")),
            }
            for r in all_results
        ],
        "processed_summary": processed_summary,
        "error": None,
    }


def research_advertiser(brand_name: str, topic: str = "", client_brief: str = "") -> list[dict]:
    """Run all research skills against a brand, on the brief's topic.

    Each skill runs independently — if one fails, others still complete.
    Returns a list of skill result dicts.
    """
    skills = load_skills()
    results = []

    for i, skill in enumerate(skills):
        if i > 0:
            time.sleep(SEARCH_DELAY)
        result = run_skill(skill, brand_name, topic=topic, client_brief=client_brief)
        results.append(result)

    return results


# Backward-compatible wrapper
def search_advertiser(brand_name: str, topic: str = "", client_brief: str = "") -> str:
    """Legacy interface — returns a single formatted string of brand research."""
    skill_results = research_advertiser(brand_name, topic=topic, client_brief=client_brief)
    parts = []
    for sr in skill_results:
        parts.append(f"### {sr['skill_name']}\n{sr['processed_summary']}")
    return "\n\n".join(parts) if parts else f"No research results found for {brand_name}."
