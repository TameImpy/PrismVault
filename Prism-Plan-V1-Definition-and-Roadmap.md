# Prism Plan — V1 Product Definition & Roadmap

**Status:** V1 definition agreed (28 May 2026) — ready for MD sign-off
**Date:** 28 May 2026
**Owner:** Matt Rance
**Audience:** MD, Revenue Operations & Data

> **How to read this:** All scope decisions from 28 May are baked in and recorded in §14. Everything else is grounded in the working prototype as it stands today.

---

## 1. Executive summary

Prism Plan is a working prototype that turns a client brief into an evidence-backed advertising recommendation — drawing on product/format metadata, audience data, campaign history and (newly) brand-lift evidence, and synthesising it with an LLM. This document moves it from an open-ended prototype to a **scoped V1**.

**V1 in one line:** *Given a client brief and KPI, Prism Plan recommends the right Immediate products and formats — grounded in verified product metadata, two years of campaign history, clean audience segments and historical brand-lift evidence — and produces an on-brand first-draft deck the salesperson can take into a pitch.*

**Who it's for:** the salesperson, self-serve, responding to a live client brief (§3).

**What has to be true for V1 to be useful:**
- The V1 data inputs each reach their minimum readiness bar (§7).
- The product/format and brand-lift datasets share **one consistent format-naming convention**.
- The **official sales deck template is delivered** — now a hard gate on go-live (§9).
- Recommendations pass a **blind credibility review** against real past briefs.
- *Real editorial-interview data is explicitly not required for V1* — it depends on the insights team's interview programme and lands in Phase 2.

**Headline roadmap:** *Phase 0* unblocks the data inputs and the template (owners assigned); *Phase 1* wires the real data into the engine, integrates brand-lift, and rebuilds the deck on the official template; *Phase 2* adds the editorial-insight programme, audience trends (if cheap) and the case-study fast-follow; *Phase 3* puts it in front of a small, human-in-loop cohort of real users.

**Critical path to go-live:** the **official deck template** (James → Beth). Because the deck is in V1, the template's delivery date effectively sets the V1 launch date.

---

## 2. Where Prism Plan is today (prototype baseline)

The prototype is live (FastAPI backend, Next.js frontend, deployed) and already does end-to-end synthesis. Against the V1 requirements, here is the honest current state:

| V1 capability | Prototype today | Real-data gap |
|---|---|---|
| Recommend products & formats vs. a brief | Works, but off ~18 digital-display formats only | Verified metadata + print + other products |
| Draw on historical campaign activity | ~2,000 rows, **digital only**, no format detail | Ingest 2-yr print+digital set Pietro shared (26 May) |
| Incorporate audience segments + trends | Segment library powers the Assistant; **trends are dummy data** | Clean segments; decide if real trends are in scope |
| Reference brand-lift / Impact Lite | **Not in the product at all** | Net-new integration of Gosia's data |
| Generate aligned presentation output | Deck builder works on an **interim** template | Rebuild against official sales template (blocker) |
| Editorial insight grounding | Capability live, but on **placeholder/dummy** content | Real editorial interviews (insights team) — *not required for V1* |

The point: **V1 is mostly a data-readiness and integration exercise, not a rebuild.** The engine exists; it needs to be fed real, trusted data and pointed at the right deck template.

---

## 3. The core user and job-to-be-done

**Primary user:** the salesperson / account manager, **self-serve**, preparing a response to a client brief.

**Core job-to-be-done:** *"A client brief has landed. I need to come back quickly with a credible, on-brand recommendation — the right products and formats, with evidence behind them, and a deck to present — without spending hours pulling it together myself."*

**UX implication of self-serve:** because salespeople operate it directly (rather than a power-user insight team), V1 needs a guided, low-friction flow and a higher floor on output quality — there is no analyst in the loop to catch a weak recommendation before it's used. (Note: the *first controlled cohort* still has human review as a guardrail — §10 — but the V1 design target is self-serve.)

---

## 4. What V1 is — the minimum credible feature set

A salesperson enters a brief (topic, advertiser, KPI, optional brief text) and Prism Plan returns:

1. **Recommended products & formats** — ranked, with a one-line rationale each, grounded in verified metadata (objective fit, cost, creative complexity, when-to-use). Covers the products Sales actually sells: digital, print, and the key additional products (podcasts, magazines, Apple News).
2. **Supporting evidence** — relevant historical campaign activity and **brand-lift evidence** (which comparable studies have run and their benchmarks).
3. **Audience grounding** — the relevant clean segments for the brief.
4. **A written brief** — the synthesised narrative, saved to the brief library for reuse.
5. **An on-brand first-draft deck** — aligned to the official sales template (gated on template delivery, §9).

**Strategic note on editorial insight:** editorial knowledge was Prism Plan's original differentiator, but for V1 it is a **Phase-2 enrichment, not an input**. V1's evidence base is campaign history + brand-lift + product metadata. This is a deliberate sequencing call so V1 does not depend on the (slower) editorial-interview programme. **The editorial section is omitted from V1's client-facing output** (it cannot be shown on dummy data) and returns in Phase 2 once real interviews land.

---

## 5. Priority use cases

You've confirmed **all four jobs belong in the V1 experience** (with the tradeoff noted below). Mapped to readiness:

1. **Brief → product & format recommendation** — *the core; must be excellent.* "As a salesperson, given a brief and KPI, I want the right products and formats recommended, so I can respond quickly and credibly."
2. **Brief → supporting evidence & rationale** — *the differentiator.* In V1 the evidence is **campaign history + brand-lift + product metadata** (editorial is Phase 2, §4).
3. **Brief → audience & timing insight** — segments are in; timing/trends only if Permutive is low-effort (§7).
4. **Brief → client-ready deck** — in V1, but gated on the official template (§9).

> **Tradeoff to hold in view:** treating all four as must-nail ties the V1 launch date to the *slowest* dependency. With editorial taken off the V1 critical path, the binding constraint is the **deck template**. Recommendation + evidence + audience can be ready on the data being assembled; go-live waits on the template.

---

## 6. Scope: in / out / later

| In V1 | Out of V1 (deferred, with reason) | Future roadmap |
|---|---|---|
| Product/format recommendations on verified metadata (digital + print + key products) | **Real editorial-interview data** — depends on the insights team's interview programme (slow to plan/execute); V1 runs without it | Editorial-insight programme feeding real data (Phase 2) |
| Recommendations informed by ≥2 yrs campaign history | **Impressions-by-delivered-format** — campaign data has no format column; disproportionate effort (your position, 27 May) | Case-study creator agent |
| Brand-lift evidence at *reference level* (which studies ran + benchmarks), format naming reconciled | **Real audience-trend data** — in only if Permutive extraction is low-effort; else deferred | Deeper brand-lift analytics (incl. impressions-by-format) |
| Clean audience segments referenced | **Case-study creator** — confirmed fast-follow, not V1 | Real audience trends (if not in V1) |
| **Client-ready deck aligned to the official template** (gated on template delivery) | | Automated monthly data-refresh pipelines; broader rollout |

**Governing scope principle (from the thread):** include only the minimum data and functionality required for a *credible* sales-facing V1. Anything that adds disproportionate effort or delays delivery moves to the roadmap.

---

## 7. Data readiness — the heart of V1

Each input needs to clear a **minimum readiness bar** to be usable. Status reflects the prototype as it stands today.

| Dataset | Owner | Current state (in the product) | V1 minimum bar | RAG |
|---|---|---|---|---|
| **Product & format metadata** | Isabel | `format_recommendations.csv`: ~18 rows, digital display only; schema already has cost/complexity/objectives/best-for/when-to-use | Verified values (no placeholders) for products Sales sells, **incl. print + podcasts/magazines/Apple News**; core fields populated; Isabel confirms which fields are deliverable now vs. later vs. not feasible | **Amber** |
| **Campaign history** | Pietro | ~2,000 rows, digital only, no format granularity | ≥2 yrs digital (print if low-effort); ingested into the product; **monthly refresh process agreed** | **Amber** (data shared 26 May, not yet integrated) |
| **Audience — segments** | Abel / Luca | Segment library powers the Assistant | Clean segment names + definitions (AudienceProject if feasible) | **Amber** |
| **Brand lift / Impact Lite** | Gosia (+ Isabel for mapping) | **Not integrated** — no data or module in the product | Historical brand-lift campaigns + benchmarks, with format names reconciled to Isabel's taxonomy | **Red — net-new** |
| **Deck template** *(dependency)* | James (via Beth) | Interim template only | Official sales template delivered and integrated so output matches the real deck | **Red — hard gate on go-live** |
| **Audience — trends** | Abel / Luca | `audience_trends.csv` is **dummy/synthetic** | Real Permutive data **only if low-effort**; otherwise out of V1 | **Out unless cheap** |
| **Editorial insight** | Insights team (Gosia) | Capability live; content is **placeholder/dummy** | **Not a V1 dependency** — runs on existing content; real editorial interviews are a Phase-2 programme | **Phase 2** |

---

## 8. Brand-lift (Impact Lite) integration

**What it adds to V1:** the ability to say "campaigns like this have run before, and here's the brand-lift result," turning recommendations from assertion into evidence. With editorial deferred, this is now V1's primary evidence differentiator.

**The integration challenge (real, from the thread):** Impact Lite format values are entered by the planner/salesperson *at request time* and may not reflect what was actually delivered. Gosia's team can't confirm delivered formats. True delivered-format attribution would require cross-referencing each Impact Lite line against campaign data — and the campaign data currently has **no format column**, so this is disproportionate for V1.

**V1 decision (your stated position, 27 May — confirmed):** V1 references *which* brand-lift campaigns have run and their *benchmarks*; it does **not** attempt impressions-by-delivered-format. The one piece of integration work V1 *does* need is a **consistent format-naming convention** between Gosia's Impact Lite data and Isabel's recommendation taxonomy (you created an initial mapping; Gosia to review). Without this, the LLM can't reliably link a recommended format to its brand-lift evidence.

---

## 9. Deck export & template alignment

The prototype already generates a branded 5-slide deck (`deck_builder.py`), but against an **interim** template. The official sales template is expected from Beth, via James.

**Decision (28 May): the deck is core to V1; V1 waits for the official template.**

**Consequence:** the official template is now a **hard gate on V1 go-live** — Prism Plan cannot launch to the controlled cohort until it lands. This makes the template the single most important dependency in the whole plan.

**Action:** secure a *committed delivery date* from James/Beth, and escalate if it slips, since it now sets the V1 launch date. The interim template stays in use for internal Phase-1 validation so build work isn't blocked in the meantime.

---

## 10. Path to controlled use

**The first cohort (confirmed):** a **small trusted pod (2–3 account managers)** using Prism Plan on *real* live briefs, with the insight team reviewing output before it goes client-facing (human-in-loop). Positioned explicitly as a *first draft* to be edited, not an auto-pilot. The reviewer guardrail is removed as confidence grows and the tool moves toward the self-serve target (§3).

**Entry criteria — what must be true before the cohort starts:**
- All V1-critical datasets (§7) at their minimum bar.
- Official deck template delivered and integrated.
- One agreed format-naming convention live across product + brand-lift data.
- Recommendations pass a **blind credibility review**: sales rate Prism Plan's output against real past briefs as usable with light editing.
- A feedback loop in place to capture where it's wrong.

**Success signals:** sales judge the output credible and time-saving; recommendations are trusted enough to take to a client; reduced time-to-first-draft for a brief response.

---

## 11. Delivery phases

*(Sequencing-only for now — no target dates, given delivery hinges on other teams' inputs.)*

| Phase | Goal | Key work | Gate to exit |
|---|---|---|---|
| **0 — Unblock inputs** | Every input + the template hits its readiness bar | Isabel: metadata + print + products. Pietro: ingest 2-yr print+digital + agree monthly refresh. Abel/Luca: clean segments. Gosia: brand-lift + naming reconciliation. James/Beth: **deliver official template**. | Each dataset at its §7 bar; template delivered |
| **1 — V1 build** | Real data drives credible recommendations + on-brand deck | Replace dummy/partial data in the engine; integrate brand-lift at reference level; enforce one format taxonomy; **rebuild deck on the official template** | Blind credibility review passed; deck matches template |
| **2 — Enrichment + fast-follows** | Deepen the product | **Editorial-insight programme** (insights-team interviews → real data); audience trends (if feasible); **case-study creator**; automated refresh | Enrichments shipped |
| **3 — Controlled use → rollout** | Real commercial users | First cohort (2–3 AMs) on live briefs, human-in-loop; capture feedback; then broaden toward self-serve | Success signals met (§10) |

---

## 12. Dependencies & critical path

- **Critical path / hard gate on go-live:** the official sales deck template (James → Beth). Because deck is in V1, **the template's delivery date sets the V1 launch date.** Priority action: get a committed date.
- **Cross-team data dependencies (V1):** Isabel (metadata + print), Pietro (campaign history + monthly refresh), Abel/Luca (segments; trends optional), Gosia (brand-lift + mapping review). Owners assigned; status in §7.
- **Slower, non-V1 dependency:** the insights team's **editorial-interview programme** (Phase 2). Distinct from Gosia's brand-lift data, which is already shared and is in V1.
- **Connective tissue across workstreams:** a single **format-naming convention** — agree it once, early, so recommendations can link to brand-lift evidence.

---

## 13. Key risks

| Risk | Impact | Mitigation |
|---|---|---|
| Deck template not delivered | **Directly blocks V1 launch** (deck is in V1) | Secure committed date from James/Beth; escalate early — it sets go-live |
| Format naming inconsistent across teams | LLM can't link formats to evidence; weak recommendations | Agree one taxonomy now; Gosia reviews Matt's mapping |
| Product metadata is placeholder/inaccurate | Confidently wrong recommendations — worse for self-serve (no analyst to catch it) | Isabel signs off on *accuracy*, not just coverage |
| Audience-trends scope creep | Delays V1 | Hard rule: low-effort-or-out |
| Monthly refresh not owned | Data goes stale; tool loses trust | Assign owner + process in Phase 0 |
| Editorial absence weakens the pitch | V1's original USP is deferred | Lean on brand-lift as the V1 evidence differentiator; sequence editorial into Phase 2 |

---

## 14. Decisions confirmed (28 May)

1. **V1 user** — the salesperson, self-serve.
2. **Priority jobs** — all four belong in the V1 experience (recommendation, evidence, audience, deck); **editorial real-data is taken off the V1 critical path** and moved to Phase 2.
3. **Deck export** — core to V1; **V1 waits for the official template** (template = hard gate on go-live).
4. **Controlled use** — small trusted pod (2–3 AMs), human-in-loop.
5. **Roadmap** — sequencing-only (no target dates) for now.
6. **Editorial in V1** — omitted from client-facing output until real interviews land in Phase 2 (no dummy data to clients).
