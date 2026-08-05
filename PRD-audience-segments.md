# PRD: Audience Segments & Reach — data-driven segment recommendations in briefs

## Problem Statement

Today the brief pipeline's audience section is powered by `data/audience_trends.csv` — 52 rows of **dummy data**. `src/audience.py:get_topic_trends()` substring-matches the topic and returns a fabricated "peak month / best day / top segment" with a made-up `audience_index`. The segments are vague labels ("health enthusiasts"), and there is **no reach (user count) anywhere**. For a self-serve sales tool — where no analyst is in the loop to catch a weak or invented recommendation — showing fabricated timing and unactionable segments is a credibility risk.

Sales needs the opposite: for any brief (e.g. Lurpak, or keyword "baking"), a recommendation of the **most relevant, targetable segments we actually hold**, and **how many users can be reached in each**. That data now exists, across two platforms, but is not wired into briefs.

Separately, the Prism Assistant chat already recommends segments from an *older, different* file (`data/assistant/segment_library.csv`, 901 rows). Once briefs use fresher, authoritative data, the same brand could return different segments and reach in chat vs brief — quietly undermining trust in both surfaces.

## Solution

Replace the dummy "Audience Timing" section with a real **"Audience Segments & Reach"** section driven by two authoritative segment exports (Permutive + AP), normalised into a single canonical dataset that **both** the brief pipeline and the Assistant read.

For each brief run, an LLM expands `advertiser + topic + client_brief` into concept keywords/categories (so brand names like *Lurpak* resolve to *butter / dairy / baking*), a deterministic filter selects the most relevant segments across both platforms, and the section presents — per platform, in its own scale — the top segments ranked by reach, each with an exact user count pulled verbatim from source. The same structured payload also feeds a new **"Recommended Audiences"** slide in the PowerPoint deck.

## User Stories

1. As a sales user, when I run a brief for a brand (e.g. Lurpak), I want the most relevant targetable segments surfaced automatically, so I don't have to know that "Lurpak" means butter/dairy/baking and search for it myself.
2. As a sales user, I want to see how many users I can reach in each recommended segment, so I can advise a client on realistic scale.
3. As a sales user, I want segments split by platform with a one-line explanation of what each platform's reach means, so I don't oversell a broad modelled audience as precise intent.
4. As a sales user, I want a plain-English reason each segment was recommended, so I can justify it to a client without exposing internal jargon.
5. As a sales user, I want the same segments and reach whether I see them in a brief, in the Assistant chat, or in the generated deck, so the numbers never contradict each other.
6. As a sales user, I want a "Recommended Audiences" slide in my deck with a relevant icon per segment, so it's client-ready without manual formatting.

## Implementation Decisions

### Data sources (the two platforms)
- **Permutive** (1,357 rows): behavioural segments ("browsed X content ≥ N times"). Has `Size` (reach). Category is embedded in the `Name` prefix ("Food & Drink - …"). Engagement encoded as a `(R/O/F & window)` suffix.
- **AP** (493 rows, latest export): first-party / DFP intent segments. Now has `Size` (reach) and a clean `Segment Category` column.
- **Scale differs ~55×** (AP median reach ~6.2M, up to 32M ≈ whole UK online population; Permutive median ~113k). They are **different currencies** and are always shown as **separate lists, each in its own scale, each tagged with platform**.

### Canonical dataset + build script
- `scripts/build_segments.py` (new) reads the monthly `.xlsx` export(s) and normalises both platforms into one canonical **`data/segments.csv`** with schema: `segment_name, platform, reach, category, description, plain_english, code, frequency, window, icon_key`.
- Normalisation applies at build time: Permutive category parsed from `Name` prefix; AP category taken from `Segment Category`; R-variant collapse; 0/blank-reach exclusion; a cleaned plain-English descriptor derived from the raw description.
- Runtime only ever reads the clean CSV (no `.xlsx` parsing in the request path). Refresh cycle: drop new export → rerun script → commit → redeploy. Versioned and diffable in git.
- **Single source of truth:** both the brief pipeline and the Assistant's `search_segments()` read `data/segments.csv`.

### Matching engine (LLM term-expansion + keyword filter)
- One GPT-4o call takes `advertiser + topic + client_brief` and returns concept keywords + candidate categories, expanded generously with synonyms (e.g. *Lurpak → butter, dairy, spreads, baking, home cooking*). This is what makes **brand names resolvable** — literal matching returns zero for "Lurpak".
- Deterministic token/stem filter over `segment_name + description + category` across both platforms (milliseconds, pandas, no vector DB).
- **Fallback ladder:** too few matches → broaden to category-only; zero → the section honestly states "no strongly-matched segments" rather than surfacing junk.
- The call fires **concurrently** with the existing gather steps (synthesiser is async), so it adds ≈ 0 wall-clock time. It is the cheapest LLM call in the pipeline.

### Selection & ranking
- **Variant collapse:** group by `Clean Audience Name`; keep the **R (Regular, ≥2×)** variant. Fallback order **R → F → O** (favour engagement over raw reach when no R exists).
- **Exclude reach ≤ 0 or blank** (un-pitchable).
- **Relevance-gated**, then **ordered by reach descending, up to 8 per platform** (Permutive and AP as separate lists).

### Output section & hard rules
- New **"Audience Segments & Reach"** section **replaces** "Audience Timing". Fabricated peak-month/best-day timing is removed; seasonality is a Phase-2 item only if a real source appears.
- Reach is a **deterministic structured payload** (mirroring `google_trends` / `format_recommendations`): the pipeline attaches exact reach from the file and the frontend renders it. **Numbers never pass through the LLM** — hallucination of reach is structurally impossible. The LLM narrative may reference segments but is instructed to quote reach verbatim.
- **Never sum reach — anywhere.** No total figure exists (segments overlap and are not de-duplicated against each other). A visible note states this so salespeople don't sum it themselves.
- **Per-platform framing shown once** as a list header (not repeated per row): AP = "modelled first-party audience — broad reach"; Permutive = "behavioural — recently engaged browsers".
- **Per segment:** name + reach + platform, with a **plain-English "why"** as the headline; the raw "browsed X ≥2×" methodology kept as a secondary evidence line/tooltip; ad-ops `code` available but tucked away.

### Deck: "Recommended Audiences" slide
- The same structured payload feeds a new deck slide via `python-pptx`.
- **Icons — bundled local PNG set, no AI generation.** `data/segment_icons/` holds ~30–40 open-licensed PNGs (Lucide/Tabler MIT or Noto Emoji Apache-2.0). Mapping: deterministic **category → icon** (covers every segment with a generic fallback), plus **keyword overrides** for polish (baking → oven-glove, wine → glass). Optional near-free upgrade: the existing expansion call returns an `icon_key` chosen from the fixed allow-list, with the category icon as the guaranteed fallback. No network, no per-run cost, milliseconds. (SVG is not used — `python-pptx` inserts PNG only.)

### Consistency
- Repoint `src/assistant.py:search_segments()` at `data/segments.csv` so chat, brief, and deck never contradict each other on segments or reach.

### Files touched
- **New:** `scripts/build_segments.py`, `data/segments.csv`, `data/segment_icons/`, `PRD-audience-segments.md`.
- **Modified:** `src/audience.py` (rewrite → segment recommender), `src/synthesiser.py` (swap audience step; return `audience_segments` payload), `src/prompts.py` (section + placeholder), `src/assistant.py` (`search_segments` repoint), `src/deck_builder.py` + `src/slide_content.py` ("Recommended Audiences" slide), frontend audience renderer.
- **Retired:** `data/audience_trends.csv`.

## Testing Decisions

Per project convention, launch the `unit-test-runner` agent after implementation. Backend `python3 -m pytest tests/ -v`; frontend `cd frontend && npm test`.

- `build_segments.py`: correct normalisation (category parsing, R-variant collapse, 0-reach exclusion, plain-English derivation) on representative fixtures from both sheets.
- Matching: "baking" returns baking segments; "Lurpak" resolves via expansion to butter/dairy/baking (not zero); fallback ladder triggers correctly; zero-match path returns the honest empty state.
- Selection: R-variant preferred (R→F→O fallback); ≤ 8 per platform; ordered by reach desc; 0/blank reach excluded.
- Invariants: reach values in the payload match the source file exactly; **no summed total** appears in payload or rendered output; every segment carries a platform tag and an icon key.
- Deck: slide builds without corruption (see `pptx-validator`); every segment resolves to a real PNG (fallback never missing).

## Out of Scope

- **Seasonality / timing** (peak month, best day) — no real source; deferred to Phase 2.
- **AI-generated segment imagery** — rejected on cost/latency/consistency; bundled icons only.
- **Cross-segment / cross-platform de-duplication or overlap modelling** — segments are not de-duped; the product's answer is "never sum", not "compute true combined reach".
- **Semantic/embeddings matching** — the keyword-filter approach is not a one-way door; embeddings can be bolted on behind the same interface if recall proves weak.
- **Automated monthly refresh** — refresh is a manual run-the-script-and-commit step for now.

## Further Notes

- **Assumptions to confirm:** (1) "up to 8" = per platform, not combined; (2) variant fallback R→F→O; (3) exclude 0/blank reach; (4) refresh monthly, owner Abel/Luca (per Prism Plan V1).
- **Prism Plan V1 alignment:** this delivers the "audience" job of the V1 experience with real reach evidence, and feeds the client-ready deck (core to V1). It intentionally avoids editorial/vector work (Phase 2) and impressions-by-format (out of scope for V1).
- **Recall is the only real risk** of the chosen matching engine (a relevant segment whose wording doesn't overlap the LLM's terms can be silently missed). Mitigated by generous synonym expansion, matching on name+description+category, stem matching, and the fallback ladder. Monitor and consider embeddings if it bites.
