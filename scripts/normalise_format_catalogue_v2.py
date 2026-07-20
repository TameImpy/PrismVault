"""Normalise the raw V2 format catalogue into the final data file.

Reads data/format_recommendations_v2_raw.csv (the confirmed 72-product V2 list),
applies two human-reviewed transformations, and writes the result to
data/format_recommendations.csv:

1. Fixes the `Masthead ` trailing-space data-hygiene issue in the Format name.
2. Rewrites the fragment-style `best_for_brief` / `best_for_advertiser_type`
   values in the 25 print/sponsorship rows into consistent full-sentence form,
   matching the style already used by the digital rows. These sentences were
   reviewed and approved by the product owner (see PRD #91 / slice #92).

The V2 schema already drops `When to use this` and `avoid_when`; no column
changes are made here. Re-run this script whenever the raw file is refreshed.

    python3 scripts/normalise_format_catalogue_v2.py
"""
import csv
import os

HERE = os.path.dirname(__file__)
RAW_PATH = os.path.join(HERE, "..", "data", "format_recommendations_v2_raw.csv")
OUT_PATH = os.path.join(HERE, "..", "data", "format_recommendations.csv")

# Approved sentence-form values, keyed by the Format name (after trailing-space
# fix). best_for_brief -> a campaign-type phrase; best_for_advertiser_type -> an
# "...advertisers" phrase, matching the digital rows' style.
NORMALISED = {
    "DPS Advertorial": (
        "Thought-leadership campaigns needing space to build authority and credibility",
        "Advertisers with an educational or expertise-led story to tell",
    ),
    "Single Page Advertorial": (
        "Brand-positioning campaigns needing a focused single-page statement",
        "Advertisers with an educational or explanatory message",
    ),
    "Half Page Vertical Advertorial": (
        "Brand-visibility campaigns needing presence alongside editorial",
        "Advertisers looking to drive a clear call to action",
    ),
    "Quarter Page Strip Advertorial": (
        "Campaigns needing lightweight logo presence and frequency",
        "Response-focused advertisers seeking efficient exposure",
    ),
    "Bookend Display": (
        "Campaigns building brand association around editorial content",
        "Advertisers looking to drive a clear call to action",
    ),
    "Advertisement Feature": (
        "Thought-leadership campaigns needing in-depth editorial storytelling",
        "Advertisers with an educational or expertise-led story to tell",
    ),
    "Supplement": (
        "Campaigns needing deep engagement through a dedicated print feature",
        "Advertisers with an educational or category-building message",
    ),
    "Subscription Envelope": (
        "Campaigns targeting existing subscribers at the point of delivery",
        "Response-focused advertisers with a direct offer",
    ),
    "Gatefold (General)": (
        "Brand-launch campaigns needing high-impact print presence",
        "Advertisers seeking standout impact for a launch moment",
    ),
    "Display Ad": (
        "Brand-visibility campaigns needing straightforward print presence",
        "Response-focused advertisers with a direct message",
    ),
    "Belly Band": (
        "Campaigns needing mass visibility that wraps around the product",
        "Advertisers seeking standout impact and broad reach",
    ),
    "DPS Listing Strip": (
        "Campaigns needing frequency of exposure across listings",
        "Advertisers looking to drive a clear call to action",
    ),
    "Garden of the Year Sponsorship": (
        "Campaigns seeking category ownership through a flagship sponsorship",
        "Advertisers seeking long-term association with a relevant property",
    ),
    "2-for-1 Gardens Guide": (
        "Campaigns reaching relevant, engaged audiences through a useful guide",
        "Advertisers seeking audience engagement and participation",
    ),
    "Calendar Sponsorship": (
        "Campaigns needing long-term exposure across the year",
        "Advertisers seeking sustained association with a trusted property",
    ),
    "Streaming DPS Sponsored Border": (
        "Campaigns aligning with entertainment and streaming content",
        "Entertainment and streaming advertisers building consideration",
    ),
    "Non-Standard Ad Shape": (
        "Disruptive campaigns needing a standout, unexpected format",
        "Advertisers seeking standout impact and cut-through",
    ),
    "DPS Recipe Content ft Client Talent": (
        "Food-led campaigns pairing recipe content with client talent",
        "Food and drink advertisers with an educational message",
    ),
    "Single Page Recipe Sponsored Border": (
        "Food-led campaigns building recall around recipe content",
        "Food and drink advertisers seeking contextual association",
    ),
    "DPS Recipe Sponsored Corner Turn": (
        "Traffic-driving campaigns anchored to recipe content",
        "Response-focused food and drink advertisers",
    ),
    "BBC Good Food Calendar": (
        "Food-led campaigns seeking long-term presence across the year",
        "Food and drink advertisers seeking sustained association",
    ),
    "Bound-In Barn Door": (
        "Product-launch campaigns needing a standout print innovation",
        "Advertisers seeking standout impact for a launch",
    ),
    "Advent Calendar": (
        "Promotional campaigns needing interactive audience participation",
        "Advertisers seeking engagement and participation",
    ),
    "Feature Sponsorship": (
        "Campaigns seeking subject-matter ownership through feature sponsorship",
        "Advertisers seeking long-term association with a relevant topic",
    ),
    "Gardeners' World Gatefold": (
        "High-impact launch campaigns needing premium print standout",
        "Advertisers seeking standout impact for a launch moment",
    ),
}


def main():
    raw_path = os.path.normpath(RAW_PATH)
    out_path = os.path.normpath(OUT_PATH)

    with open(raw_path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    normalised_count = 0
    masthead_fixed = False
    for row in rows:
        name = (row.get("Format") or "").strip()
        if row.get("Format") != name:
            masthead_fixed = True
        row["Format"] = name

        if name in NORMALISED:
            brief, adv = NORMALISED[name]
            row["best_for_brief"] = brief
            row["best_for_advertiser_type"] = adv
            normalised_count += 1

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    unmatched = sorted(set(NORMALISED) - {(r.get("Format") or "").strip() for r in rows})
    print("Wrote %d rows to %s" % (len(rows), out_path))
    print("Normalised %d fragment rows (expected %d)" % (normalised_count, len(NORMALISED)))
    print("Masthead trailing-space fixed: %s" % masthead_fixed)
    if unmatched:
        print("WARNING: normalisation keys with no matching row: %s" % unmatched)


if __name__ == "__main__":
    main()
