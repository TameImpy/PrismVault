"""One-off seed generator for the vertical taxonomy + brand->vertical lookup.

Deterministic (no LLM): reads data/campaign_history.csv, writes
data/vertical_taxonomy.json and data/brand_verticals.csv. Every roster brand
is seeded from its modal raw category where that category maps to a controlled
vertical; brands whose modal category is junk/unmappable are written with a
blank vertical and flagged (needs_review=true) for Matt to fill in.

Re-run after a data refresh to regenerate the seed, then review flagged rows.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.vertical_classifier import (  # noqa: E402
    SEED_TAXONOMY,
    DEFAULT_TAXONOMY_PATH,
    DEFAULT_LOOKUP_PATH,
    LOOKUP_FIELDNAMES,
    distinct_brands_with_hints,
    seed_vertical_from_category,
    save_brand_verticals,
)


def main():
    with open(DEFAULT_TAXONOMY_PATH, "w") as f:
        json.dump(SEED_TAXONOMY, f, indent=2)
        f.write("\n")

    roster, hints = distinct_brands_with_hints()
    rows = []
    flagged = 0
    for brand in roster:
        vertical = seed_vertical_from_category(hints.get(brand, ""))
        needs_review = "false" if vertical else "true"
        if not vertical:
            flagged += 1
        rows.append({
            "brand": brand,
            "vertical": vertical,
            "source": "seed",
            "needs_review": needs_review,
        })

    save_brand_verticals(DEFAULT_LOOKUP_PATH, rows)
    print("Wrote taxonomy (%d verticals) to %s" % (len(SEED_TAXONOMY), DEFAULT_TAXONOMY_PATH))
    print("Wrote %d brands to %s (%d flagged for review)"
          % (len(rows), DEFAULT_LOOKUP_PATH, flagged))


if __name__ == "__main__":
    main()
