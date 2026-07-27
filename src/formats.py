import csv
import os
import re

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "format_recommendations.csv")

# A recommendation entry is a list item (bullet or number) whose first bold span
# is the format name — matching the "Recommended Products" output format.
_LIST_MARKER = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_BOLD = re.compile(r"\*\*(.+?)\*\*")

# Structured view of the catalogue: snake_case key -> CSV column. This is the
# contract the deck consumes (PRD #131), so the keys are stable regardless of
# how the CSV headers are spelled.
#
# V2 schema: `When to use this` and `avoid_when` are dropped. Indicative cost
# is retained here as model context but is not surfaced to users (enforced via
# the prompt).
ROW_FIELDS = [
    ("format", "Format"),
    ("format_family", "format_family"),
    ("ctr", "CTR avg"),
    ("viewability", "Viewability"),
    ("indicative_cost", "Indicative cost"),
    ("primary_objective", "primary_objective"),
    ("secondary_objective", "secondary_objective"),
    ("best_for_brief", "best_for_brief"),
    ("best_for_advertiser_type", "best_for_advertiser_type"),
]


def load_format_rows(csv_path=None):
    # type: (str) -> list
    """Return the format catalogue as structured, JSON-serialisable rows.

    The prose sibling ``load_format_data`` renders the same catalogue for the
    prompt; this one keeps every value verbatim so CTR and viewability can be
    placed on a slide without ever being re-read out of generated prose. Rows
    with no benchmarks carry empty strings — the "benchmarks not available"
    wording is a prose concern and stays in ``load_format_data``.

    Returns an empty list if the file is missing or holds no data rows.
    """
    if csv_path is None:
        csv_path = DEFAULT_CSV_PATH

    if not os.path.exists(csv_path):
        return []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            entry = {key: (row.get(column) or "").strip() for key, column in ROW_FIELDS}
            if entry["format"]:
                rows.append(entry)
    return rows


def load_format_names(csv_path=None):
    # type: (str) -> list
    """Return the exact list of confirmed format names from the catalogue.

    Names are stripped of surrounding whitespace (defensive data hygiene) and
    returned in file order. This is the deep, pure interface the name-validation
    guardrail and prompt assembly both rely on. Returns an empty list if the
    file is missing or empty.
    """
    return [row["format"] for row in load_format_rows(csv_path)]


def load_format_data(csv_path=None):
    # type: (str) -> str
    """Load format recommendations CSV and return a prompt-ready string.

    Returns a fallback message if the file is missing.
    """
    if csv_path is None:
        csv_path = DEFAULT_CSV_PATH

    if not os.path.exists(csv_path):
        return "No format recommendation data available."

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return "No format recommendation data available."

    parts = []
    for row in rows:
        lines = []
        lines.append((row.get("Format") or "Unknown Format").strip())
        lines.append("  Family: %s" % row.get("format_family", "N/A"))

        ctr = (row.get("CTR avg") or "").strip()
        viewability = (row.get("Viewability") or "").strip()
        if ctr and viewability:
            lines.append("  CTR avg: %s" % ctr)
            lines.append("  Viewability: %s" % viewability)
        else:
            # Non-digital products (print, podcast, email, sponsorship, etc.)
            # have no digital benchmarks. Say so in plain English rather than
            # emitting a blank or "N/A".
            lines.append(
                "  Benchmarks: benchmarks not currently available for this specific format"
            )

        lines.append("  Indicative cost: %s" % row.get("Indicative cost", "N/A"))
        lines.append("  Primary objective: %s" % row.get("primary_objective", "N/A"))
        lines.append("  Secondary objective: %s" % row.get("secondary_objective", "N/A"))
        lines.append("  Best for brief: %s" % row.get("best_for_brief", "N/A"))
        lines.append("  Best for advertiser type: %s" % row.get("best_for_advertiser_type", "N/A"))
        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def validate_format_names(content, valid_names):
    # type: (str, list) -> dict
    """Best-effort, deterministic name-validation guardrail.

    Scans generated recommendation `content` and classifies the format names it
    presents against the confirmed catalogue `valid_names`:

    - ``recognised``: confirmed catalogue names that appear anywhere in the
      content. A lenient substring scan — it answers "did the model use real
      names?", so a name mentioned in passing inside another entry's prose
      counts.
    - ``recommended``: confirmed catalogue names actually *presented* as
      recommendation entries (the leading bold name of a list item), in the
      order the content presents them, spelled as the catalogue spells them.
      This is the stricter reading the deck selects products by — a format
      merely named in prose must not end up on a slide.
    - ``unrecognised``: the same recommendation entries that do NOT match any
      confirmed name — i.e. hallucinated or renamed products.

    Pure and side-effect free (no OpenAI, no I/O) so it is fully testable. This
    is intentionally best-effort per PRD #91: the synthesiser logs unrecognised
    names server-side without blocking the user's response.
    """
    valid_list = [(n or "").strip() for n in valid_names]
    valid_lookup = set(n.lower() for n in valid_list if n)
    # Map back to catalogue casing — the deck joins its rows on these names.
    canonical = {n.lower(): n for n in valid_list if n}

    lowered = content.lower()
    recognised = [n for n in valid_list if n and n.lower() in lowered]

    recommended = []
    unrecognised = []
    seen = set()
    for line in content.splitlines():
        marker = _LIST_MARKER.match(line)
        if not marker:
            continue
        bold = _BOLD.search(line[marker.end():])
        if not bold:
            continue
        candidate = bold.group(1).strip().rstrip(":").strip()
        if not candidate:
            continue
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        if key in valid_lookup:
            recommended.append(canonical[key])
        else:
            unrecognised.append(candidate)

    return {
        "recognised": recognised,
        "recommended": recommended,
        "unrecognised": unrecognised,
    }
