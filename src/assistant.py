import csv
import json
import os
from collections import Counter

from openai import OpenAI

import config

ASSISTANT_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "assistant")

_KNOWLEDGE_FILES = [
    "data_proposition.md",
    "faqs.md",
    "slas_and_process.md",
]

SEGMENT_CSV = os.path.join(ASSISTANT_DATA_DIR, "segment_library.csv")


def load_knowledge_base():
    """Load and concatenate all markdown knowledge base files."""
    parts = []
    for filename in _KNOWLEDGE_FILES:
        path = os.path.join(ASSISTANT_DATA_DIR, filename)
        with open(path) as f:
            parts.append(f.read())
    return "\n\n---\n\n".join(parts)


def _load_segments():
    """Load the segment library CSV and return a list of dicts."""
    with open(SEGMENT_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Strip whitespace from header names
        reader.fieldnames = [h.strip() for h in reader.fieldnames]
        return list(reader)


def build_category_summary():
    """Build a summary of segment categories with counts and example names."""
    segments = _load_segments()
    categories = Counter(row.get("Segment Category", "Unknown") for row in segments)

    lines = ["## Available Segment Categories\n"]
    for category, count in sorted(categories.items()):
        # Get a few example segment names for this category
        examples = [
            row["Name"] for row in segments
            if row.get("Segment Category") == category
        ][:3]
        example_str = ", ".join(examples)
        lines.append("- **%s** (%d segments) — e.g. %s" % (category, count, example_str))

    return "\n".join(lines)


def search_segments(query, category=None, max_results=20):
    """Search the segment library by query string and optional category filter.

    Returns a list of dicts with keys: name, size, category, description.
    """
    segments = _load_segments()
    query_lower = query.lower()

    matches = []
    for row in segments:
        name = row.get("Name", "")
        description = row.get("Segment Description", "")
        seg_category = row.get("Segment Category", "")

        # Filter by category if provided
        if category and category.lower() not in seg_category.lower():
            continue

        # Match query against name and description
        if query_lower in name.lower() or query_lower in description.lower():
            matches.append({
                "name": name,
                "size": row.get("Size", "0").strip(),
                "category": seg_category,
                "description": description,
            })

        if len(matches) >= max_results:
            break

    return matches


SYSTEM_PROMPT_TEMPLATE = """You are Prism Assistant, an internal AI assistant for the Immediate Media sales team.

Your role is to answer questions about IM Audiences, Prism data products, audience segments, targeting methodologies, SLAs, and processes.

Rules:
1. Answer ONLY based on the knowledge base provided below. Never invent segment names, capabilities, or pricing.
2. If you don't know the answer or it's not covered in the knowledge base, say so and direct them to email dl-audience-ads@immediate.co.uk
3. Be concise and practical — sales people want quick answers.
4. When discussing segments, include sizes where available.
5. You can use the search_segments tool to look up specific segments from the segment library.

## Knowledge Base

{knowledge_base}

{category_summary}
"""

SEARCH_SEGMENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "search_segments",
        "description": "Search the IM Audiences segment library for specific audience segments by name, description, or category.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term to match against segment names and descriptions (case-insensitive).",
                },
                "category": {
                    "type": "string",
                    "description": "Optional filter by segment category (e.g. 'Food & Drink', 'Demographics - Age').",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Default 20.",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    },
}


def _build_system_prompt():
    """Build the full system prompt with knowledge base and category summary."""
    knowledge = load_knowledge_base()
    categories = build_category_summary()
    return SYSTEM_PROMPT_TEMPLATE.format(
        knowledge_base=knowledge,
        category_summary=categories,
    )


def chat(messages):
    """Send a chat request and return the assistant's response.

    Handles a single round of function calling if the model requests it.
    Returns a dict with keys: role, content.
    """
    system_prompt = _build_system_prompt()
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=full_messages,
        tools=[SEARCH_SEGMENTS_TOOL],
        temperature=0.3,
    )

    choice = response.choices[0]

    # Handle function calling
    if choice.message.tool_calls:
        tool_call = choice.message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        results = search_segments(
            query=args.get("query", ""),
            category=args.get("category"),
            max_results=args.get("max_results", 20),
        )

        # Add the assistant's tool call message and tool result
        full_messages.append(choice.message)
        full_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(results),
        })

        # Second call with tool results
        response = client.chat.completions.create(
            model=config.CHAT_MODEL,
            messages=full_messages,
            tools=[SEARCH_SEGMENTS_TOOL],
            temperature=0.3,
        )
        choice = response.choices[0]

    return {
        "role": "assistant",
        "content": choice.message.content,
    }
