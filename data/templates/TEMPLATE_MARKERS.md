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
| 5 Historical Insights (×3) | `[INSIGHT_n]`, `[INSIGHT_n_STAT]` (n=1..3) | matched `historical_research` body | LLM-selected 3 insights, grounded; `_STAT` is the supporting figure |

**Capacity:** 3 product tiles, 4 segment tiles, 3 insight tiles. The deck fills up to these counts; fewer available items should leave the surplus tiles blank (or be handled per #134).

## Static zones (never filled — leave untouched)

- All section headings: Prism Overview, Advertiser Overview, Recommended Products, Recommended Segments, Historical Insights, Appendix, Methodology
- Slide 1 Prism Overview body prose (boilerplate)
- Slide 6 Appendix
- Slide 7 Methodology body prose (boilerplate)

## Notes for #134 (rebuild)

- `deck_builder.py`'s `TEMPLATE_PATH` must point at `prism_plan_template_export.pptx` (the old interim `prism_plan_template.pptx` is removed).
- Historical Insights: `[INSIGHT_n]` = insight text, `[INSIGHT_n_STAT]` = a supporting stat; omit the section when no research matched (`relevant: false`).
- Numeric fields (`PRODUCT_*`, `SEGMENT_*`) are placed verbatim from the structured payload — never LLM-generated.
