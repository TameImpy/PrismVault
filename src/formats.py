import csv
import os

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "format_recommendations.csv")

# V2 schema: `When to use this` and `avoid_when` are dropped. Indicative cost
# is retained here as model context but is not surfaced to users (enforced via
# the prompt).
DISPLAY_COLUMNS = [
    "Format", "format_family", "CTR avg", "Viewability", "Indicative cost",
    "primary_objective", "secondary_objective", "best_for_brief",
    "best_for_advertiser_type",
]


def load_format_names(csv_path=None):
    # type: (str) -> list
    """Return the exact list of confirmed format names from the catalogue.

    Names are stripped of surrounding whitespace (defensive data hygiene) and
    returned in file order. This is the deep, pure interface the name-validation
    guardrail and prompt assembly both rely on. Returns an empty list if the
    file is missing or empty.
    """
    if csv_path is None:
        csv_path = DEFAULT_CSV_PATH

    if not os.path.exists(csv_path):
        return []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        names = []
        for row in reader:
            name = (row.get("Format") or "").strip()
            if name:
                names.append(name)
    return names


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
