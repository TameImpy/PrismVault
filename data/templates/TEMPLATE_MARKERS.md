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
| 6 Appendix (×6) | `[PROVENANCE_n]` (n=1..6) | `provenance` entries from the brief run | **verbatim** — one line per data section |

**Provenance lines (#156):** one per data section the brief drew on, naming its source, as-at date, coverage (whole network vs a single site), period and refresh cadence. The wording is the registry's own (`data/provenance.csv`, read by `src/provenance.py`) — the deck places it exactly as the brief showed it, so the two can never give different accounts of the same figure. Sections a brief did not render carry no line and their marker blanks. Because the appendix reaches clients, the registry names systems ("the ad deliveries central benchmarking sheet"), never repository paths; `tests/test_provenance.py` enforces that.

**Appendix capacity:** 6 lines, the number of data sections a brief can carry. Add a section to the registry and the seventh line has nowhere to go — extend `PROVENANCE_TILES` in `src/slide_content.py` and re-run `scripts/add_provenance_markers.py`. `tests/test_deck_builder.py` measures the block against the slide height, so verbose registry prose fails the build rather than overflowing the slide.

**Insight tiles:** the tile mirrors the product tile — `[INSIGHT_n]` is the 40pt ExtraBold hero line and carries the *figure*; `[INSIGHT_n_STAT]` is the 26pt ExtraLight line beneath it and carries the supporting phrase. (The marker names read the other way round; the layout is what the code follows.)

**Capacity:** 3 product tiles, 4 segment tiles, 3 insight tiles. The deck fills up to these counts. Segments are taken round-robin across the matched platforms so both audience engines are represented. A tile with no data behind it is blanked — the marker run is emptied and removed, never left showing `[MARKER]`.

## Static zones (never filled — leave untouched)

- All section headings: Prism Overview, Advertiser Overview, Recommended Products, Recommended Segments, Historical Insights, Appendix, Methodology
- Slide 1 Prism Overview body prose (boilerplate)
- Slide 6 Appendix intro line ("Every figure in this deck traces back to one of these sources.") — the `[PROVENANCE_n]` lines beneath it are filled
- Slide 7 Methodology body prose (boilerplate)

## How the code fills it (#134)

- `deck_builder.py` populates `prism_plan_template_export.pptx` (the interim `prism_plan_template.pptx` is gone). Text is written into the template's own marker runs, so each populated run keeps the placeholder's font, size and colour. **No styling lives in Python** — change the look by editing this template.
- The whole Historical Insights slide is dropped when no research matched (`relevant: false`), rather than left blank.
- Numeric fields (`PRODUCT_*`, `SEGMENT_*`) are placed verbatim from the structured payload — never LLM-generated. The LLM writes only `[ADVERTISER_OVERVIEW]` and picks the insights.
- The tiles carry values only; any wording that labels them (e.g. "avg CTR", "viewability") belongs in the template artwork, not in the code.
- A **new marker is authored into the template**, never drawn at build time. `scripts/add_provenance_markers.py` is how the appendix markers were added: it clones an existing text box so Barlow, the colour and the bullet styling come across verbatim, and is idempotent so it can be re-run after a template revision. Keep that pattern — a .pptx diff tells a reviewer nothing, so the script is the record of the edit.
