# Deck template marker reference

Template: `data/templates/prism_plan_template_export.pptx` (official 8-slide V1 template, tokenised for slice #132 / PRD #131).

Naming convention: `UPPER_SNAKE_CASE`, wrapped in square brackets, with a numeric index for repeated tiles (`[SEGMENT_2_NAME]`). The code fills a marker by exact-string match, preserving the template's own run formatting.

## Dynamic markers → data source

| Slide | Marker(s) | Source | Fill rule |
|---|---|---|---|
| 0 Title | `[ADVERTISER_NAME]` | brief input (advertiser) | verbatim (renders "`<Advertiser>` Brief") |
| 2 Advertiser Overview | `[ADVERTISER_OVERVIEW]` | brief advertiser research | LLM prose |
| 3 Recommended Products (×3) | `[PRODUCT_n_FORMAT]`, `[PRODUCT_n_CTR]`, `[PRODUCT_n_VIEW]` (n=1..3) | `format_recommendations` rows (`Format`, `CTR avg`, `Viewability`) | **verbatim** |
| 4 Recommended Segments (×4) | `[SEGMENT_n_NAME]`, `[SEGMENT_n_REACH]` (n=1..4) | `audience_segments` (`segment_name`, `reach`) | **verbatim** |
| 5 Historical Insights (×3) | `[INSIGHT_n]`, `[INSIGHT_n_STAT]` (n=1..3) | matched `historical_research` body | LLM-selected 3 insights, grounded in the matched body |

**Insight tiles:** the tile mirrors the product tile — `[INSIGHT_n]` is the 40pt ExtraBold hero line and carries the *figure*; `[INSIGHT_n_STAT]` is the 26pt ExtraLight line beneath it and carries the supporting phrase. (The marker names read the other way round; the layout is what the code follows.)

**Capacity:** 3 product tiles, 4 segment tiles, 3 insight tiles. The deck fills up to these counts. Segments are taken round-robin across the matched platforms so both audience engines are represented. A tile with no data behind it is blanked — the marker run is emptied and removed, never left showing `[MARKER]`.

## Static zones (never filled — leave untouched)

- All section headings: Prism Overview, Advertiser Overview, Recommended Products, Recommended Segments, Historical Insights, Appendix, Methodology
- Slide 1 Prism Overview body prose (boilerplate)
- Slide 6 Appendix
- Slide 7 Methodology body prose (boilerplate)

## How the code fills it (#134)

- `deck_builder.py` populates `prism_plan_template_export.pptx` (the interim `prism_plan_template.pptx` is gone). Text is written into the template's own marker runs, so each populated run keeps the placeholder's font, size and colour. **No styling lives in Python** — change the look by editing this template.
- The whole Historical Insights slide is dropped when no research matched (`relevant: false`), rather than left blank.
- Numeric fields (`PRODUCT_*`, `SEGMENT_*`) are placed verbatim from the structured payload — never LLM-generated. The LLM writes only `[ADVERTISER_OVERVIEW]` and picks the insights.
- The tiles carry values only; any wording that labels them (e.g. "avg CTR", "viewability") belongs in the template artwork, not in the code.
