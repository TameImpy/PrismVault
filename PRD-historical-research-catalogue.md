# PRD: Historical Research Catalogue (Proof of Concept)

## Problem Statement

When a salesperson generates a brief, the tool draws on live, generic sources (web research, Google Trends, audience segments, formats, direct campaign history). What it **cannot** do today is reference the company's own **proprietary research** — the audience surveys and category studies that are the actual differentiator a media owner brings to a client conversation. That evidence currently lives in 53-slide decks that no salesperson opens mid-brief.

This is a **proof-of-concept** to prove one specific thing, live, in a demo: **a catalogue of "historical research" files can be referenced by the agent flow and pulled through into the brief — automatically, only when relevant, and visibly to the salesperson.** We are starting with a single, real file — the *Immediate Media Travel Audience Research 2024/25* reference — and proving the end-to-end path. The value we are demonstrating is **grounded, cited, defensible proprietary evidence** appearing in the brief without anyone hunting for a deck.

The bar for the POC is deliberately narrow: prove the *pull-through*, not build a research platform. Everything that makes it scale to N files is explicitly Phase 2.

## Solution

Add a new, catalogue-backed data source that mirrors the pattern every other source in the pipeline already follows, plus one thing they mostly don't: **selective inclusion**.

- **A file catalogue** — markdown files with YAML frontmatter live in `data/historical_research/`, glob-loaded at runtime (the exact pattern the `skills/*.md` system already uses). Adding a file later is dropping a `.md` in the folder — no code change.
- **A deterministic relevance gate** — for each brief, a keyword match decides whether a research file is relevant. It concatenates the brief's `topic + advertiser + client_brief` (lowercased) and matches against each file's frontmatter `topics` + a curated `match_keywords` list. Any single overlap includes the file. No LLM, no API dependency — so the live demo is reproducible every run.
- **Dual surfacing (panel is the hero):** on a match, the relevant file is (1) **injected into the synthesis prompt** under a new `{historical_research}` placeholder so the model genuinely reasons with the evidence and cites it inline, and (2) **surfaced as a distinct "Historical Research" hero card** in the UI — deterministic frontmatter metadata (source, fieldwork dates, respondent base) plus model-generated, brief-tailored "relevant findings" bullets.
- **Disciplined citation** — a minimal claim-use instruction in the system prompt (name the source audience, state the fieldwork date, quote the base `n=` with any percentage, present figures as stated intention not behaviour, never sum multi-select percentages) so the output looks like defensible research, not AI waffle.
- **Graceful absence** — on a non-travel brief nothing matches: the prompt gets a fallback string, the model omits the section entirely, and the card does not render. The result dict always carries a `historical_research` key with a `relevant` boolean.

The proof is the contrast: a non-travel brief shows nothing; a travel brief makes the card appear and the recommendations visibly cite the survey.

## User Stories

1. As a salesperson, I want the brief to automatically pull in our own proprietary research when it's relevant to the advertiser, so that I bring evidence a competitor can't.
2. As a salesperson, I want that research to appear as a clearly-labelled card showing the source and its date, so that I can see exactly where the evidence came from and cite it with confidence.
3. As a salesperson, I want the pulled findings to be tailored to *this* brief (e.g. cruise data for a cruise brand), so that they're immediately usable rather than a generic data dump.
4. As a salesperson running a brief with no relevant research, I want the brief to look completely normal (no empty or broken research box), so that the feature only ever adds value, never noise.
5. As a salesperson, I want every figure quoted from the research to carry its audience and base (e.g. "n=334 cruise intenders, late-2024"), so that I don't accidentally over-claim a survey stat in front of a client.
6. As the feature owner (Matt), I want to add a new research file by dropping a markdown file into a folder, so that growing the catalogue is zero-code.
7. As the feature owner, I want the relevance gate to be deterministic and testable, so that "P&O fires, Nike doesn't" is a guaranteed, regression-guarded behaviour I can rely on in a live demo.
8. As a demo audience member, I want to see the research card appear on a travel brief and *not* appear on a non-travel brief, so that I understand the system is selectively reasoning about relevance, not always bolting research on.

## Implementation Decisions

**Catalogue & storage**
- Files live in `data/historical_research/*.md` — consistent with `data/` holding the pipeline's other file-backed sources.
- Each file is markdown with YAML frontmatter. The travel file already has this shape; we add one field: **`match_keywords`** — a curated list of the single words a brief is likely to contain (e.g. `travel, holiday, cruise, flight, hotel, airline, tourism`). This de-risks matching against the verbose `topics` phrases.
- Loading reuses the frontmatter-parsing pattern already in `src/web_search.py` (`re.match(r"^---\n(.+?)\n---\n(.+)", raw, re.DOTALL)` + `yaml.safe_load`). `pyyaml` is already a dependency.

**Relevance gate (deterministic — the selection decision)**
- New module `src/historical_research.py`. Interface shape: `get_relevant_research(topic, advertiser, client_brief) → {relevant, files/metadata, prompt_text}`.
- Logic: concatenate `topic + advertiser + client_brief`, lowercase → for each file, test intersection against the flattened set of `topics` + `match_keywords` → **any single overlap includes the file**.
- No LLM. No ranking or top-N — at N=1, every match is simply included.

**Prompt injection (weaving)**
- New `{historical_research}` placeholder in `USER_PROMPT_TEMPLATE`. On a match it carries the **whole file body** (verbatim — no chunking/extraction at N=1). On no-match it carries a fallback string (`"No historical research matched this brief."`).
- SYSTEM_PROMPT gains a new `## Historical Research` output section instruction: when relevant research is present, produce 2–3 tailored findings bullets grounded in it; when it's the fallback, **omit the section entirely** (do not write "none found" into the prose).
- SYSTEM_PROMPT gains one **minimal claim-use sentence**, matching the existing audience-segments citation-discipline house style: name the source audience, state fieldwork date, quote the base `n=` with any percentage, present as stated intention not behaviour, never sum multi-select percentages.

**UI surfacing (the hero card)**
- Single GPT-4o call, unchanged in count. The tailored bullets ride in the parsed `## Historical Research` section (reusing the frontend's existing `parseSections()` machinery — the same path "At a Glance" and "Key Recommendations" already use).
- `generate_insights()` returns a `historical_research` object in the result dict: `{relevant: bool, ...}` and on a match `{title, organisation, fieldwork, total_respondents, matched_on}` — all pulled **verbatim from frontmatter** (deterministic, no hallucination risk).
- The frontend composes the hero card from (metadata dict object) + (parsed prose bullets). Card renders **only** when `historical_research.relevant === true` — mirroring the conditional render already used for `campaign_history`.

**Modules**
- **New:** `src/historical_research.py` (loader + deterministic gate + prompt/fallback formatting).
- **Modified:** `synthesiser` (call the gate, inject `{historical_research}`, return the dict object); `prompts` (new placeholder, `## Historical Research` section spec, claim-use sentence); frontend `/app` page (type + hero-card render, guarded on `relevant`).
- **Data:** the travel `.md` file placed in `data/historical_research/`, with `match_keywords` added to its frontmatter.

## Testing Decisions

**What makes a good test here:** the selection logic is a pure function over file metadata and brief text — no LLM, no network — so it's deterministic and exhaustively testable. The gate tests *are* the regression guard for the demo passing ("P&O fires, Nike doesn't"). LLM output (the tailored bullets and woven prose) and the UI card are **not** unit-tested — they're verified by eye in a dry run.

**Module to be tested — `src/historical_research.py`:**
1. **Loader** — globs `data/historical_research/*.md`, parses frontmatter, returns metadata + body. Cover: valid file parses; `match_keywords` read correctly; empty/missing folder returns no files gracefully.
2. **Relevance gate** (the money logic) — Cover: travel brief ("P&O Cruises" / "cruise campaign") → matches; non-travel brief ("Nike" / "running shoes") → no match; case-insensitivity; matching hits on `match_keywords` as well as `topics`; the `topic+advertiser+client_brief` concatenation (a keyword only in `client_brief` still matches).
3. **No-match fallback & contract** — returns the fallback string and a `{relevant: false}` object when nothing matches; the `historical_research` dict key is always present with the correct shape in both states.

**Prior art:** existing pytest suites in `tests/` (data-loader and synthesiser tests) — same style, exercising a module's public function over fixture files. Per `CLAUDE.md`, the `unit-test-runner` agent runs after implementation.

**Not unit-tested:** the LLM's bullets/prose (nondeterministic — eyeballed in the demo dry run) and the frontend card rendering (verified visually).

## Out of Scope (explicitly deferred to Phase 2)

- **LLM relevance classifier** — the semantic "Cunard → travel" leap. POC uses the deterministic keyword gate only.
- **Multi-file ranking / top-N selection** — the loader globs many files, but no relevance *scoring* or "best N when several match." Moot at N=1; every match is included.
- **Section-level extraction / chunking** — the whole file goes into the prompt; no per-section retrieval.
- **Vector search** — the dormant ChromaDB layer is not revived for this; it stays Phase 2 alongside the editorial vector work.
- **Upload / catalogue-management UI** — files are added by dropping a `.md` in the folder, not via any interface.
- **Token/scale handling** — no summarisation or truncation. Fine at one ~10k-token file; needs attention at ~5+ files.
- **Per-file weighting, freshness decay, or expiry** — data-staleness is handled by the claim-use prompt (the file carries its own dated-source warnings), not by code.

## Further Notes

- **Demo script (the whole point):** two-brief contrast. (1) Non-travel brief — advertiser "Nike", topic "running shoes launch" → no Historical Research card, output looks normal. (2) Travel brief — advertiser "P&O Cruises", topic "cruise campaign for over-50s", KPI "Awareness" → card appears; the synthesis cites the survey's cruise data (23% consideration, n=334 intenders, P&O top at 38%, ocean/river/adults-only split). P&O chosen because §14 of the file gives the richest, most quotable cruise-specific evidence, so the woven output looks strikingly specific rather than generic.
- **Why deterministic gate for a live demo:** the gate is keyword-based specifically so the demo has zero API dependency in the selection step — the salesperson controls the brief, and a travel keyword reliably fires the card every run.
- **Why the panel is the hero:** invisible weaving alone can't be *seen* to work. The labelled card — with verbatim source metadata proving provenance and tailored bullets proving reasoning — is the visual that makes the pull-through concept legible to a non-technical room.
- **Scaling story to tell stakeholders:** the catalogue, glob loader, and frontmatter gate are built to accept file #2 with zero code; the Phase 2 upgrades (LLM relevance, ranking, chunking, vector search) are the path from "one file, keyword gate" to "large research library, semantic retrieval."
- Related in-flight work: this follows the same "real proprietary data into the brief" thread as `PRD-audience-segments.md` and `PRD-direct-campaign-history.md`, and reuses their citation-discipline and conditional-render patterns.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
