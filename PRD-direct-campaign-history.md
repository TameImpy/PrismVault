# PRD: Direct Campaign History + Comparable Brands

## Problem Statement

When a salesperson generates a brief for an advertiser, they need to know one thing up front that the tool currently answers poorly: **"Have we worked with this brand before?"** — and if not, **"Who like them *have* we worked with?"**

Today the brief has a "Previous Campaign History" section backed by `campaign_history.csv`, but it has three problems:

1. **The data is dummy/stale.** It can't be trusted or shown in a client-facing context.
2. **The match is crude.** A case-insensitive *substring* match produces false positives ("Sky" matches "Skyscanner", implying a relationship that doesn't exist) and false negatives (legal-suffix or abbreviation variants match nothing, telling a salesperson "new brand" about an existing client).
3. **There's no fallback.** When there's no match, the section just says "No previous campaign data found" — a dead end. It never surfaces the *comparable* brands we have worked with, which is exactly what a salesperson needs to build credibility ("we haven't run with you, but we've run with three brands just like you").

This matters acutely because the V1 user is a **self-serve salesperson with no analyst in the loop** to catch a wrong answer. A false "yes, they're a client" is reputationally the worst failure — the salesperson repeats it to the client and is wrong.

## Solution

Refresh the dataset with real, current, **direct-only** campaign data (programmatic excluded), and rebuild the section around an accurate, honest relationship signal with a useful fallback:

- **Have we worked with them?** — answered by a **deterministic** entity-resolution step (no LLM), producing a three-way outcome: **match**, **possible match**, or **no match**. The factual claim is never left to the LLM, so it cannot hallucinate a relationship.
- **Who's similar?** — on a genuine no-match, an LLM-driven **comparable brands** engine surfaces 2–3 brands we *have* worked with, each with a one-line reason and their best-performing format. The LLM's picks are **validated in Python against the real roster**, so it can never name a brand we haven't actually worked with.

The output section becomes a single "Client Relationship" section with three states, and all wording is scoped to **"direct"** so it never over-claims beyond what the direct-only data supports.

## User Stories

1. As a salesperson, I want the brief to tell me whether we've run a **direct** campaign with this advertiser before, so that I know if I'm talking to an existing client or a new prospect.
2. As a salesperson, I want that answer to be **accurate**, so that I never walk into a meeting and wrongly claim (or deny) a prior relationship.
3. As a salesperson, when the advertiser *is* an existing client, I want to see the relationship summary (how many campaigns, categories, performance, recency), so that I can reference our track record.
4. As a salesperson, when the brand name is **ambiguous** (e.g. "Virgin" → Virgin Media / Virgin Atlantic), I want the brief to flag the possible matches for me to verify rather than guess, so that I'm not handed a confident-but-wrong answer.
5. As a salesperson, when we have **no direct history** with the advertiser, I want the brief to name 2–3 **similar brands we have worked with**, so that I can still demonstrate relevant experience.
6. As a salesperson, I want each comparable brand to come with a **one-line reason** it's similar and its **best-performing format**, so that I can immediately use it in conversation ("Monzo — similar challenger-finance — ran homepage takeovers at 0.4% CTR").
7. As a salesperson, I want to trust that every "similar brand" named is a **real client** of ours, so that I never cite a brand we've never worked with.
8. As a salesperson, I want the brief to say **"no direct campaign history"** rather than "we've never advertised with this brand," so that I'm not blindsided if the client ran programmatic with us.
9. As a salesperson, when there are **no genuinely comparable** brands in our history, I want the brief to say so honestly rather than reach for an irrelevant brand, so that I don't make a nonsensical comparison in front of a client.
10. As a salesperson working in a niche vertical, I want the tool to **widen** to adjacent verticals (and tell me it did) when there are no close comparables, so that I still get a useful, clearly-caveated suggestion.
11. As a data owner (Pietro), I want the monthly data refresh to slot straight into the existing pipeline, so that keeping the tool current is low-effort.
12. As the feature maintainer (Matt), I want **new brands** in each monthly refresh to be auto-classified into a vertical and flagged for my review, so that the tool doesn't silently degrade as the roster grows.
13. As the feature maintainer, I want a **log of unmatched/near-matched brands**, so that I can grow the alias table from real misses rather than guesswork and understand where entity resolution is failing.
14. As the feature maintainer, I want the factual match logic to be **deterministic and testable**, so that I can reason about and verify its behaviour without depending on model output.
15. As a reader of the brief, I want the relationship section to be a **single coherent section** with one clear state, so that I'm never shown an empty or contradictory block.

## Implementation Decisions

**Data**
- The dataset is a **refresh in place** of the existing `campaign_history.csv` with real, current, **direct-only** data — *not* a new data source. Same schema, same pipeline slot, same injection point in the synthesis prompt.
- "Direct-only" is **pre-filtered at source** by the data owner; no channel/booking-type column is required for now. Output wording is scoped to "direct" regardless, so the claim stays precise.

**Entity resolution (deterministic — the factual yes/no)**
- Extracted as a **deep, pure module** with no LLM dependency. Interface shape: `resolve(brand, roster) → {status, matched_name, candidates}` where `status ∈ {match, possible_match, no_match}`.
- Logic: name **normalisation** (lowercase; strip legal suffixes such as Ltd/Plc/Inc; strip punctuation; normalise `&`/`and`) → **token-set fuzzy match** against the normalised roster → **threshold** producing the three-way outcome (confident match / ambiguous "possible" band / genuine no-match).
- A small, **manually-maintained, reactive alias table** handles parent/subsidiary and known aliases (e.g. "Coke" → Coca-Cola). It is *not* pre-populated; entries are added in response to observed misses.
- The LLM is kept **entirely out** of the factual yes/no.

**Section behaviour (one section, three states)**
- Single section (e.g. "Client Relationship") driven by the resolver's status:
  - **match** → relationship + performance summary (existing behaviour).
  - **possible_match** → a flagged *"⚠ verify"* callout naming the candidate(s) with their history shown, asserting nothing; **comparables suppressed**.
  - **no_match** → "No **direct** campaign history" + 2–3 comparables.

**Comparables engine (LLM judgement, Python-guarded)**
- **Two-tier selection:**
  - **Tier 1 (precision):** Python filters the roster to a **vertical-matched shortlist** → LLM picks 2–3 and explains.
  - **Tier 2 (recall):** when the Tier-1 shortlist is empty or thin, the LLM is given the **full roster** (~217 brands + verticals as hints) so it can apply world knowledge that a category column cannot encode (e.g. Sky → NowTV).
- **Separate structured LLM call, no-match path only** — returns JSON `[{brand, why_similar}]`. Matched/possible-match paths make no extra call.
- **Python post-validation (the guardrail):** extracted as a **deep, pure module**. Every returned brand is validated against the real roster; any name not present is **dropped**. This makes "the LLM can never name a brand we haven't worked with" an enforced guarantee, not a hope.
- **Thin-roster behaviour:** widen **once** to adjacent verticals (with an explicit note in the output); if still nothing, output "no close comparables" rather than reach across unrelated verticals.
- Each surviving comparable is rendered as **name + why-similar + that brand's best-performing format** (drawn from existing campaign-history aggregation logic).
- **Accepted residual limitation:** validation guarantees each comparable is a *real client*, not that the *similarity reasoning* is strong — Tier 2 in particular can produce softer reaches. This is the accepted price of recall.

**Vertical normalisation & maintenance**
- The raw `category` column is treated as **permanently messy** and is *not* reasoned on directly. A clean, controlled **vertical taxonomy** is derived and cached at ingest.
- **Vertical classification** at ingest: diff distinct brands against the cached lookup; **LLM-classifies new brands** into the taxonomy, appends to the cache, and **flags additions for review**.
- **Unmatched/near-matched brands are logged** to grow the alias table from real misses and to feed a limitations review.

**Artefacts**
- Lookup tables (brand→vertical, aliases) and the unmatched-brand log live as **files under `data/`**, versioned in git.
- The structured comparables call uses the same configured chat model as the rest of the pipeline.

**Modules**
- **New (deep, pure):** entity resolution; comparables validator.
- **New (orchestrator):** comparables engine (two-tier + structured call + validator); vertical classifier (classify + new-brand diff).
- **Modified:** `campaign_history` (return `status`, branch to comparables on no-match); `synthesiser` (inject validated result); `prompts` (scoped "direct" wording, three-state section); ingest (run classification + new-brand flagging).

## Testing Decisions

**What makes a good test here:** tests assert **external behaviour** through a module's public interface, not internal implementation. The two deep modules are pure functions over data (no LLM, no I/O), which makes them deterministic and exhaustively testable. LLM calls are **mocked/stubbed** — we test the Python logic around them, never the model's output.

**Modules to be tested:**
1. **Entity resolution** (pure) — the highest-risk logic. Cover: confident match; false-positive guard (e.g. "Sky" must **not** match "Skyscanner"); legal-suffix/punctuation normalisation; alias-table hit (e.g. "Coke" → Coca-Cola); ambiguous "possible_match" band; genuine no-match.
2. **Comparables validator** (pure) — the trust guardrail. Cover: an LLM pick that exists in the roster survives; a pick that does **not** exist is dropped; empty input; all-invalid input.
3. **Comparables engine tier logic** (LLM mocked) — Tier 1 shortlist path; empty/thin shortlist falls through to Tier 2 full-roster path; thin-roster widen-once behaviour; still-nothing → "no close comparables".

**Prior art:** existing Python tests in `tests/` (e.g. the synthesiser and data-loader tests) — same pytest style, same approach of exercising a module's public function over fixture data.

**Not unit-tested:** the raw LLM calls themselves, and the thin wiring in `synthesiser`/`prompts`/`ingest` (covered by existing pipeline tests, plus the `unit-test-runner` agent after implementation).

*(Open: whether the vertical classifier's new-brand diff logic also gets dedicated unit tests — recommended but not yet confirmed.)*

## Out of Scope

- **Programmatic campaign data** — the dataset is deliberately direct-only. The tool never claims to know about programmatic activity.
- **Comparables for existing clients** — comparables fire **only** on a genuine no-match. Cross-sell/expansion suggestions for existing clients are a separate job, not in this PRD.
- **Impressions-by-delivered-format attribution** — out of V1 scope per the Prism Plan V1 definition (campaign data has no format column).
- **Interactive "did you mean?" confirmation** — the brief is a single generated artefact; the possible-match state renders as static, human-judgeable text, not an interactive prompt.
- **A dedicated ML/embeddings similarity engine** — similarity is handled by LLM reasoning over the small roster, guarded by Python validation. Embeddings are unnecessary at this scale (~217 brands).
- **Automated/pre-populated alias table** — the alias table is manual and reactive.

## Further Notes

- The roster is small (~217 distinct advertisers), which is what makes the two-tier approach viable: the full roster fits comfortably in a prompt, so Tier 2 recall is cheap, and post-validation against the full list is trivial.
- Design context: V1 user is a **self-serve salesperson with no analyst in the loop**, which is *why* the factual yes/no is deterministic and the comparables are Python-validated — the cost of a wrong factual claim is high and unmitigated by human review.
- A follow-up session task exists to walk through the entity-resolution logic and its limitations against the real implementation, and to understand where it will fail (threshold tuning, parent/subsidiary gaps, alias coverage).
- Related in-flight work: the Audience Segments & Reach feature (`PRD-audience-segments.md`), which similarly replaces dummy data with real data in the brief.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
