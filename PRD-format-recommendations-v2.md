## Problem Statement

When a salesperson generates a brief in Prism Data Vault, the "Recommended Products" section is powered by a small, unverified catalogue of ~18 ad formats. As a self-serve user with no analyst in the loop, the salesperson needs the recommendations to reflect the **actual confirmed products we sell** — and to give them enough detail to act on without going elsewhere. Two problems today:

1. **The catalogue is incomplete and unverified.** It covers only digital display/video formats and omits the large body of print, podcast, email, newsletter, content/native, experiential, and sponsorship products the business actually sells. A recommendation can only ever be as good as the catalogue behind it.
2. **The output is thin and the raw data is noisy.** The response gives light per-format reasoning, and the UI additionally dumps the entire raw format catalogue as an unstyled wall of text — unhelpful for a salesperson who just wants the shortlist and a clear rationale.

## Solution

Replace the format catalogue with the confirmed, business-verified V2 list (72 products spanning every channel we sell), and redesign the "Recommended Products" section of the generated brief so it:

- Recommends **3–5 formats** best matched to the advertiser's brief and KPI (aim for 5; never fewer than 3; never padded with weak fits).
- Presents, for **each** recommended format: the format name, its CTR-average and viewability benchmarks (where available), and its primary objective. Where a product has no digital benchmarks (print, podcast, email, sponsorship, etc.), it shows a plain-English note that benchmarks are not currently available for that format instead of a raw blank/"N/A".
- Closes with **one combined rationale** — a brief-aware paragraph that ties the chosen set together against *this* advertiser and KPI, amalgamating the chosen formats' `best_for_brief` and `best_for_advertiser_type` guidance plus editorial/audience context.

A lightweight guardrail ensures every recommended format name genuinely exists in the catalogue (no hallucinated or renamed products), and the redundant raw-catalogue UI panel is removed so the enriched recommendation is the single source of truth.

## User Stories

1. As a salesperson, I want the recommended formats to be drawn only from products we actually sell, so that I never pitch a client something we can't deliver.
2. As a salesperson, I want up to five recommended formats per brief, so that I have a genuine shortlist to choose from rather than a single suggestion.
3. As a salesperson, I want no fewer than three recommendations even for a narrow brief, so that I always have options to present.
4. As a salesperson, I want the recommendations capped at five, so that the shortlist stays focused and I'm not overwhelmed.
5. As a salesperson, I want each recommended format to show its click-through and viewability benchmarks, so that I can speak to expected performance with the client.
6. As a salesperson, I want each recommended format to show its primary objective, so that I can confirm it matches what the client is trying to achieve.
7. As a salesperson, I want products without digital benchmarks to say so in plain English, so that I understand a blank isn't an error and can still recommend print/podcast/sponsorship products confidently.
8. As a salesperson, I want a single combined rationale explaining why these formats fit *this* advertiser and KPI, so that I can articulate the strategic story in front of a client.
9. As a salesperson, I want the rationale to reflect the specific advertiser and brief rather than boilerplate, so that it feels tailored and credible.
10. As a salesperson, I want the recommendations to respect the campaign's KPI (awareness, consideration, viewability, clicks), so that the formats shown are fit for the stated goal.
11. As a salesperson, I want the full range of products — print, podcast, email, newsletter, content, experiential, sponsorship, and digital — to be eligible for recommendation, so that briefs suited to non-digital channels get relevant suggestions.
12. As a salesperson, I want a clean recommendation section without a wall of raw catalogue text, so that I can read and act on the output quickly.
13. As a salesperson, I want confidence that a recommended format name is exactly a real product, so that I don't misname a product to a client.
14. As a product owner, I want the confirmed catalogue to live in a single maintainable data file, so that Isabel (the product/format metadata owner) can update it without code changes.
15. As a product owner, I want the recommendation logic to fail safe when a format name can't be verified, so that quality issues are surfaced rather than silently shipped.
16. As a developer, I want the format catalogue exposed through a simple, testable interface, so that both the prompt assembly and the guardrail can rely on it.
17. As a developer, I want the name-validation guardrail to be a pure function testable without calling OpenAI, so that I can assert its behaviour deterministically.
18. As a salesperson, I want the recommendation quality to be consistent across digital and non-digital products, so that a print or sponsorship brief reads as well as a display brief.

## Implementation Decisions

**Data**
- Replace the format catalogue data file with the confirmed **V2 list (72 products)** spanning digital display/video, print, podcast, email, newsletter, content/native, experiential, and sponsorship.
- V2's schema **drops two columns** present in the previous file: `When to use this` and `avoid_when`. All other columns are retained, so the loader maps cleanly onto the existing shape minus those two.
- Roughly 50 of the 72 rows have **blank CTR/viewability benchmarks** (all non-digital products) — this is expected and normal, not a data error.
- Before load, the fragment-style `best_for_brief` / `best_for_advertiser_type` values in the print/sponsorship rows (which currently hold terse tags like "Thought leadership" / "Education" rather than the full-sentence form used by digital rows) will be **normalised into consistent sentence form** so the combined rationale reads evenly across all products. A trailing-space data-hygiene issue in one format name (`Masthead `) will be fixed.

**Catalogue module (format loader)**
- The catalogue loader gains a second interface that returns the **exact list of confirmed format names**, alongside the existing prompt-string builder. This is the deep, pure, file-in→data-out interface the guardrail and prompt assembly both depend on.
- The loader stops referencing the two removed columns. Indicative cost is retained in the data feed for model context but is **not surfaced in the user-facing output** (enforced via the prompt).

**Prompt ("Recommended Products" section)**
- Instruct the model to select **3–5** formats (aim 5, floor 3, no padding) using the existing KPI→objective mapping (awareness/consideration/viewability/clicks).
- Per-format output = **name + CTR average + viewability + primary objective**. **No indicative cost. No per-format "when to use" line** (its source column was removed).
- For any format missing a benchmark, render *"benchmarks not currently available for this specific format"* rather than a blank or "N/A".
- Add a **single combined rationale** paragraph that is brief-aware: it ties the chosen set to the specific advertiser and KPI, amalgamating the chosen formats' `best_for_brief` + `best_for_advertiser_type` guidance and available editorial/audience context.
- Instruct the model to use **exact catalogue names only**.

**Guardrail (name validation)**
- A **pure, deterministic function** takes the generated recommendation content plus the set of valid catalogue names and returns which recommended names are recognised vs unrecognised.
- Approach is **best-effort scan + server-side log**: unrecognised, format-like names are flagged and logged server-side (non-blocking) so drift/hallucination is surfaced without blocking the user's response. This is right-sized for V1; a stricter structured-output approach is explicitly out of scope for now.
- Wired into the synthesiser after the model call.

**Frontend**
- **Remove the raw full-catalogue "Format Recommendations" dump panel** (it renders the entire catalogue string as pre-wrapped text, in both the saved-brief and freshly-generated views). The enriched "Recommended Products" section within the synthesis becomes the single source of format information.

**Constraints**
- Python 3.9 compatibility (no `X | None` union syntax).
- Next.js 16 conventions (Turbopack; `proxy.ts`, not `middleware.ts`).

## Testing Decisions

Good tests here assert **external behaviour**, not implementation details — given a catalogue file (or fixture content), what does the interface return? They must not call OpenAI; existing synthesiser tests mock the client, and the format tests build a temp CSV and assert on the returned string. That prior art is followed.

- **Priority — catalogue loader** (user-selected focus): test the name-returning interface yields the exact confirmed names; test the prompt-string builder against the **V2 schema**, including that **blank-benchmark rows render the "benchmarks not currently available" wording** rather than a blank/"N/A"; test the missing-CSV fallback still holds.
- **Recommended (secondary) — guardrail validation**: with fixture recommendation content, assert in-catalogue names are recognised and off-catalogue/renamed names are flagged as unrecognised. It's the safety-critical piece, so tests are advisable even though it wasn't the selected focus.
- Existing format tests must be updated to the new schema (they currently assert on the now-dropped `When to use this` column and on indicative-cost display).
- Prior art: `tests/test_formats.py` (temp-CSV pattern) and `tests/test_synthesiser.py` (mocked OpenAI).

## Out of Scope

- **Deterministic/code-based format selection** — the LLM remains the selector; we are not moving to code-scored top-N.
- **Structured-output rework** of the recommendation into validated JSON — deferred; the guardrail is a best-effort scan for now.
- **Reintroducing `avoid_when`** or any new columns — the guardrail is name-validation only.
- **Restructuring other brief sections** (editorial, audience, campaign history, messaging) — only "Recommended Products" and its data/UI are in scope.
- **A structured card UI** for the five recommendations — the output stays as prose within the synthesis; only the raw dump panel is removed.
- **Editorial insight / vector-DB work** — Phase 2 per the V1 plan.

## Further Notes

- This is **Prism Plan V1-scope** work. The V1 user is a self-serve salesperson with no analyst in the loop, which raises the output-quality bar; format/product recommendation is one of V1's four core jobs. Source-of-truth doc: `Prism-Plan-V1-Definition-and-Roadmap.md` at repo root.
- **Data ownership:** the confirmed product/format metadata is owned by Isabel; the catalogue file is the maintainable handoff point for future updates.
- **Follow-up flagged:** the fragment-style values in the print/sponsorship rows are being normalised by hand for this change; a durable fix is for the data owner to standardise `best_for_brief` / `best_for_advertiser_type` at source in future refreshes.
- Decisions in this PRD were resolved through a `grill-me` session prior to drafting; they are settled inputs, not open questions.
