import csv
import json
import os
from collections import Counter

from openai import OpenAI

import config
from src.special_categories import (
    SPECIAL_CATEGORY_MESSAGE,
    SPECIAL_CATEGORY_PROMPT_RULE,
    detect_special_category,
)

ASSISTANT_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "assistant")

_KNOWLEDGE_FILES = [
    "data_proposition.md",
    "faqs.md",
    "slas_and_process.md",
]

# Single source of truth: the Assistant reads the same canonical segment file
# as the brief pipeline (PRD #96 / slice #101), so chat and brief never
# contradict each other on segments or reach. The older
# data/assistant/segment_library.csv is retired as the segment source.
SEGMENT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "segments.csv")


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
    categories = Counter(row.get("category", "Unknown") for row in segments)

    lines = ["## Available Segment Categories\n"]
    for category, count in sorted(categories.items()):
        # Get a few example segment names for this category
        examples = [
            row["segment_name"] for row in segments
            if row.get("category") == category
        ][:3]
        example_str = ", ".join(examples)
        lines.append("- **%s** (%d segments) — e.g. %s" % (category, count, example_str))

    return "\n".join(lines)


def search_segments(query, category=None, max_results=20):
    """Search the canonical segment file by query and optional category filter.

    Reads data/segments.csv (the same file the brief pipeline uses). Returns a
    list of dicts with keys: name, size, category, description, platform.
    The plain-English descriptor is preferred for `description` so chat mirrors
    the brief's wording; the raw methodology falls back if it is absent.
    """
    segments = _load_segments()
    query_lower = query.lower()

    matches = []
    for row in segments:
        name = row.get("segment_name", "")
        description = row.get("plain_english", "") or row.get("description", "")
        seg_category = row.get("category", "")

        # Filter by category if provided
        if category and category.lower() not in seg_category.lower():
            continue

        # Match query against name and description
        if query_lower in name.lower() or query_lower in description.lower():
            matches.append({
                "name": name,
                "size": (row.get("reach") or "0").strip(),
                "category": seg_category,
                "description": description,
                "platform": row.get("platform", ""),
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
6. Format responses for readability: use blank lines between paragraphs, bullet points for lists, and bold headers (e.g. **Section Name:**) to break up distinct topics. Never write long blocks of unbroken text.
7. Special category requests are handled by the rule below, which overrides rule 2 — they are a restriction, not a gap in your knowledge.

{special_category_rule}

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
        special_category_rule=SPECIAL_CATEGORY_PROMPT_RULE,
    )


def _latest_user_text(messages):
    """The text of the most recent user turn, or "" if there is none.

    Only the latest turn is scanned. Scanning the whole history would leave a
    conversation permanently gated once a sensitive word appeared in it, which is
    the over-blocking #164 warns against; the tool-call gate below is what catches
    a sensitive request the user carried over from an earlier turn, because the
    model has to name it in a segment query before segments can come back.
    """
    for message in reversed(messages or []):
        if isinstance(message, dict) and message.get("role") == "user":
            return message.get("content") or ""
    return ""


def _special_category_reply(category):
    return {
        "role": "assistant",
        "content": SPECIAL_CATEGORY_MESSAGE,
        "special_category": category,
    }


def _special_category_events(category):
    """The streaming form of `_special_category_reply`."""
    yield {"type": "special_category", "category": category}
    yield {"type": "content", "text": SPECIAL_CATEGORY_MESSAGE}
    yield {"type": "done"}


def _special_category_in_tool_args(args):
    """The Article 9 category a search_segments call concerns, or None."""
    return detect_special_category(
        " ".join(str(args.get(key) or "") for key in ("query", "category"))
    )


def chat(messages):
    """Send a chat request and return the assistant's response.

    Handles a single round of function calling if the model requests it.
    Returns a dict with keys: role, content, special_category. `special_category`
    names the Article 9 category when the request was restricted (issue #164) and
    is None otherwise, so callers can tell a restriction from an ordinary answer.
    """
    category = detect_special_category(_latest_user_text(messages))
    if category:
        return _special_category_reply(category)

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

        # The model can reach a special category by a wording the user never used.
        # Gate the lookup itself so no segments come back either way.
        tool_category = _special_category_in_tool_args(args)
        if tool_category:
            return _special_category_reply(tool_category)

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
        "special_category": None,
    }


def chat_stream(messages):
    """Stream a chat response, yielding event dicts.

    Event types:
      {"type": "content", "text": "..."}  — a text token
      {"type": "status", "message": "..."} — status update (e.g. during tool call)
      {"type": "special_category", "category": "..."} — the request concerned
          GDPR Article 9 data and was answered with the restricted message
          instead of segments (issue #164)
      {"type": "done"} — stream complete

    Handles a single round of function calling if the model requests it.
    """
    category = detect_special_category(_latest_user_text(messages))
    if category:
        yield from _special_category_events(category)
        return

    system_prompt = _build_system_prompt()
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    stream = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=full_messages,
        tools=[SEARCH_SEGMENTS_TOOL],
        temperature=0.3,
        stream=True,
    )

    # Accumulate tool call data if the model requests one
    tool_call_id = None
    tool_call_name = None
    tool_call_args = ""
    assistant_content = ""

    for chunk in stream:
        delta = chunk.choices[0].delta

        # Check for tool calls
        if delta.tool_calls:
            tc = delta.tool_calls[0]
            if tc.id:
                tool_call_id = tc.id
            if tc.function and tc.function.name:
                tool_call_name = tc.function.name
            if tc.function and tc.function.arguments:
                tool_call_args += tc.function.arguments
            continue

        # Stream content tokens
        if delta.content:
            assistant_content += delta.content
            yield {"type": "content", "text": delta.content}

    # If there was a tool call, execute it and stream the follow-up
    if tool_call_id and tool_call_name == "search_segments":
        args = json.loads(tool_call_args)

        # Same gate as chat(): a query the model derived can be special category
        # even when the user's own wording was not.
        tool_category = _special_category_in_tool_args(args)
        if tool_category:
            yield from _special_category_events(tool_category)
            return

        yield {"type": "status", "message": "Searching segments..."}

        results = search_segments(
            query=args.get("query", ""),
            category=args.get("category"),
            max_results=args.get("max_results", 20),
        )

        # Build the follow-up messages
        assistant_msg = {
            "role": "assistant",
            "content": assistant_content or None,
            "tool_calls": [{
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": tool_call_name,
                    "arguments": tool_call_args,
                },
            }],
        }
        full_messages.append(assistant_msg)
        full_messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(results),
        })

        # Second streaming call with tool results
        stream2 = client.chat.completions.create(
            model=config.CHAT_MODEL,
            messages=full_messages,
            tools=[SEARCH_SEGMENTS_TOOL],
            temperature=0.3,
            stream=True,
        )

        for chunk in stream2:
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"type": "content", "text": delta.content}

    yield {"type": "done"}
