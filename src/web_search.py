import glob
import os
import re
import time

import yaml
from ddgs import DDGS
from openai import OpenAI

import config

SEARCH_RETRIES = 3
SEARCH_RETRY_DELAY = 2  # seconds between retries
SEARCH_DELAY = 1.5  # seconds between successive queries to avoid rate limits

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")


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
            "max_results_per_query": meta.get("max_results_per_query", 3),
            "prompt": prompt_body,
            "file": os.path.basename(path),
        })

    return skills


def _run_search(query: str, max_results: int) -> list[dict]:
    """Run a single DuckDuckGo search with retries for transient failures."""
    for attempt in range(SEARCH_RETRIES):
        try:
            ddgs = DDGS()
            return list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            if attempt < SEARCH_RETRIES - 1:
                time.sleep(SEARCH_RETRY_DELAY)
            else:
                raise e
    return []


def run_skill(skill: dict, brand_name: str) -> dict:
    """Execute a single research skill against a brand.

    Runs the skill's search queries, then passes the raw results through
    GPT-4o with the skill's prompt to produce a processed summary.

    Returns dict with keys: skill_name, raw_results, processed_summary, error.
    """
    skill_name = skill["name"]
    all_results = []

    try:
        for i, query_template in enumerate(skill["queries"]):
            if i > 0:
                time.sleep(SEARCH_DELAY)
            query = query_template.replace("{brand}", brand_name)
            results = _run_search(query, skill["max_results_per_query"])
            all_results.extend(results)
    except Exception as e:
        return {
            "skill_name": skill_name,
            "raw_results": [],
            "processed_summary": f"Search failed: {e}",
            "error": str(e),
        }

    if not all_results:
        return {
            "skill_name": skill_name,
            "raw_results": [],
            "processed_summary": f"No search results found for {brand_name}.",
            "error": None,
        }

    # Format raw results as text for the GPT-4o prompt (include URLs)
    raw_text = []
    for r in all_results:
        href = r.get("href", "")
        if href:
            raw_text.append(f"- [{r['title']}]({href}): {r['body']}")
        else:
            raw_text.append(f"- **{r['title']}**: {r['body']}")
    raw_results_str = "\n".join(raw_text)

    # Build the processing prompt from the skill template
    processing_prompt = skill["prompt"].replace(
        "{brand}", brand_name
    ).replace(
        "{search_results}", raw_results_str
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
        "raw_results": [{"title": r["title"], "body": r["body"], "href": r.get("href", "")} for r in all_results],
        "processed_summary": processed_summary,
        "error": None,
    }


def research_advertiser(brand_name: str) -> list[dict]:
    """Run all research skills against a brand and return results.

    Each skill runs independently — if one fails, others still complete.
    Returns a list of skill result dicts.
    """
    skills = load_skills()
    results = []

    for i, skill in enumerate(skills):
        if i > 0:
            time.sleep(SEARCH_DELAY)
        result = run_skill(skill, brand_name)
        results.append(result)

    return results


# Backward-compatible wrapper
def search_advertiser(brand_name: str) -> str:
    """Legacy interface — returns a single formatted string of brand research."""
    skill_results = research_advertiser(brand_name)
    parts = []
    for sr in skill_results:
        parts.append(f"### {sr['skill_name']}\n{sr['processed_summary']}")
    return "\n\n".join(parts) if parts else f"No research results found for {brand_name}."
