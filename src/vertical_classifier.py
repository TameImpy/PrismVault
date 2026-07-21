"""Vertical classifier: builds a clean brand->vertical lookup at ingest.

The raw `category` column in campaign_history.csv is treated as permanently
messy (numeric junk, blanks, one-off labels) and is never reasoned on
directly. Instead we derive a clean, controlled **vertical taxonomy** and a
cached brand->vertical lookup, both versioned under `data/`.

At ingest we diff the current roster against the cached lookup, classify any
**new** brands into the taxonomy (LLM-assisted, using the messy raw category
only as a hint), append them to the cache, and flag the additions for review.

Design for testability: the new-brand diff is a pure function; the
classification step takes an injectable `classifier_fn` so tests can stub the
LLM entirely.
"""

import csv
import json
import os
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DEFAULT_TAXONOMY_PATH = os.path.join(DATA_DIR, "vertical_taxonomy.json")
DEFAULT_LOOKUP_PATH = os.path.join(DATA_DIR, "brand_verticals.csv")
DEFAULT_CAMPAIGN_CSV = os.path.join(DATA_DIR, "campaign_history.csv")

LOOKUP_FIELDNAMES = ["brand", "vertical", "source", "needs_review"]

# Controlled vertical taxonomy, seeded from the meaningful raw category values.
# Reviewable/extendable; the raw category column is only ever a hint.
SEED_TAXONOMY = [
    "Food & Drink",
    "Alcohol",
    "Supermarket",
    "Entertainment",
    "Travel",
    "Motoring",
    "Technology",
    "Health",
    "Finance",
    "Gambling",
    "Gaming",
    "Government",
    "Parenting",
    "Home & Garden",
    "Retail",
    "Pets",
]

# Deterministic map from (lowercased) raw category -> controlled vertical, used
# only to seed the initial cache. Anything not here is left for LLM/review.
CATEGORY_TO_VERTICAL = {
    "food": "Food & Drink",
    "gf": "Food & Drink",
    "alcohol": "Alcohol",
    "supermarket": "Supermarket",
    "entertainment": "Entertainment",
    "on-demand": "Entertainment",
    "history": "Entertainment",
    "social": "Entertainment",
    "social carousel": "Entertainment",
    "travel": "Travel",
    "motoring": "Motoring",
    "tech": "Technology",
    "health": "Health",
    "finance": "Finance",
    "gambling": "Gambling",
    "gaming": "Gaming",
    "government": "Government",
    "parenting": "Parenting",
    "gardening": "Home & Garden",
    "retail": "Retail",
    "pets": "Pets",
}


def diff_new_brands(roster, cached_lookup):
    # type: (list, dict) -> list
    """Return roster brands not already present in the cached lookup.

    Pure function. Order-stable (roster order), so the same input always
    yields the same list — new brands are never re-detected once cached.
    """
    return [brand for brand in roster if brand not in cached_lookup]


def load_taxonomy(path=None):
    # type: (str) -> list
    """Load the controlled vertical taxonomy (list of vertical names)."""
    if path is None:
        path = DEFAULT_TAXONOMY_PATH
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def load_brand_verticals(path=None):
    # type: (str) -> dict
    """Load the cached brand->vertical lookup as a dict of brand -> vertical."""
    if path is None:
        path = DEFAULT_LOOKUP_PATH
    if not os.path.exists(path):
        return {}
    lookup = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lookup[row["brand"]] = row["vertical"]
    return lookup


def save_brand_verticals(path, lookup_rows):
    # type: (str, list) -> None
    """Write the brand->vertical cache (list of full row dicts) to CSV."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOOKUP_FIELDNAMES)
        writer.writeheader()
        writer.writerows(lookup_rows)


def _read_lookup_rows(path):
    # type: (str) -> list
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def refresh_brand_verticals(roster, category_hints, taxonomy, lookup_path, classifier_fn):
    # type: (list, dict, list, str, callable) -> dict
    """Diff the roster against the cache, classify new brands, persist, flag.

    - ``roster``: current distinct advertiser names.
    - ``category_hints``: brand -> raw category, passed to the classifier as a
      hint only (never trusted as the vertical).
    - ``taxonomy``: controlled list of allowed verticals.
    - ``lookup_path``: brand->vertical cache CSV (read and rewritten in place).
    - ``classifier_fn(brands, category_hints, taxonomy) -> {brand: vertical}``:
      injectable so tests stub the LLM.

    Only brands absent from the cache are classified (so the same brand is not
    re-classified every run). Added brands are flagged for review. Returns
    ``{"added": [...], "flagged": [...], "lookup": {brand: vertical}}``.
    """
    existing_rows = _read_lookup_rows(lookup_path)
    cached = {row["brand"]: row["vertical"] for row in existing_rows}

    new_brands = diff_new_brands(roster, cached)

    classified = classifier_fn(new_brands, category_hints, taxonomy) if new_brands else {}

    added = []
    for brand in new_brands:
        vertical = classified.get(brand)
        if not vertical:
            continue  # classifier declined this brand; leave it for next run
        existing_rows.append({
            "brand": brand,
            "vertical": vertical,
            "source": "llm",
            "needs_review": "true",
        })
        added.append(brand)

    save_brand_verticals(lookup_path, existing_rows)

    lookup = {row["brand"]: row["vertical"] for row in existing_rows}
    return {"added": added, "flagged": list(added), "lookup": lookup}


def distinct_brands_with_hints(csv_path=None):
    # type: (str) -> tuple
    """Read campaign_history and return (roster, hints).

    ``roster`` is the sorted distinct advertiser names; ``hints`` maps each
    brand to its **modal** raw category (the single most common category label
    across that brand's rows) — used only as a classification hint.
    """
    if csv_path is None:
        csv_path = DEFAULT_CAMPAIGN_CSV
    if not os.path.exists(csv_path):
        return [], {}

    categories_by_brand = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            brand = (row.get("advertiser") or "").strip()
            if not brand:
                continue
            categories_by_brand.setdefault(brand, Counter())
            category = (row.get("category") or "").strip()
            if category:
                categories_by_brand[brand][category] += 1

    roster = sorted(categories_by_brand)
    hints = {}
    for brand, counter in categories_by_brand.items():
        hints[brand] = counter.most_common(1)[0][0] if counter else ""
    return roster, hints


def seed_vertical_from_category(raw_category):
    # type: (str) -> str
    """Map a raw category to a controlled vertical, or "" if unmappable."""
    return CATEGORY_TO_VERTICAL.get((raw_category or "").strip().lower(), "")


def classify_new_brands_llm(brands, category_hints, taxonomy):
    # type: (list, dict, list) -> dict
    """Default classifier: ask the chat model to place each brand in the
    controlled taxonomy, using the raw category only as a hint.

    Returns {brand: vertical}; any vertical the model returns that is not in
    the taxonomy is dropped, so the cache can only ever hold controlled values.
    Not unit-tested (raw LLM call) — the Python logic around it is.
    """
    if not brands:
        return {}

    from openai import OpenAI
    import config

    lines = []
    for brand in brands:
        hint = category_hints.get(brand, "")
        lines.append("- %s (raw category hint: %s)" % (brand, hint or "none"))

    prompt = (
        "Classify each advertiser brand into exactly one vertical from this "
        "controlled list:\n%s\n\nBrands:\n%s\n\n"
        "Return ONLY a JSON object mapping each brand name (verbatim) to one "
        "vertical from the list. The raw category hint is messy — use your own "
        "knowledge of the brand as the primary signal."
        % (", ".join(taxonomy), "\n".join(lines))
    )

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise brand-vertical classifier. Output only JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    try:
        raw = json.loads(response.choices[0].message.content)
    except (ValueError, TypeError):
        return {}

    allowed = set(taxonomy)
    return {b: v for b, v in raw.items() if b in brands and v in allowed}
