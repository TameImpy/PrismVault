import csv
import os

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "format_recommendations.csv")

DISPLAY_COLUMNS = [
    "Format", "format_family", "CTR avg", "Viewability", "Indicative cost",
    "primary_objective", "secondary_objective", "best_for_brief",
    "best_for_advertiser_type", "When to use this",
]


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
        lines.append(row.get("Format", "Unknown Format"))
        lines.append("  Family: %s" % row.get("format_family", "N/A"))
        lines.append("  CTR avg: %s" % row.get("CTR avg", "N/A"))
        lines.append("  Viewability: %s" % row.get("Viewability", "N/A"))
        lines.append("  Indicative cost: %s" % row.get("Indicative cost", "N/A"))
        lines.append("  Primary objective: %s" % row.get("primary_objective", "N/A"))
        lines.append("  Secondary objective: %s" % row.get("secondary_objective", "N/A"))
        lines.append("  Best for brief: %s" % row.get("best_for_brief", "N/A"))
        lines.append("  Best for advertiser type: %s" % row.get("best_for_advertiser_type", "N/A"))
        lines.append("  When to use: %s" % row.get("When to use this", "N/A"))
        parts.append("\n".join(lines))

    return "\n\n".join(parts)
