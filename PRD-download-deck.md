## Problem Statement

Sales users generate strategic insights briefs on the `/app` page, then must manually build a PowerPoint deck to present to advertisers. This is slow, error-prone (slides often drift from the brand template), and creates inconsistency across the team. The insights brief already contains everything needed for a compelling pitch deck, but translating analytical prose into concise, branded slides is tedious and time-consuming — especially when the internal template must be followed exactly.

## Solution

Add a "Download Deck" button alongside the existing "Draft Email" button that appears after insights are generated. One click produces a branded 5-slide PowerPoint deck adhering strictly to the internal Prism template — correct backgrounds, logos, Barlow fonts, and layout structure. The content is condensed from the full insights brief by GPT-4o-mini into slide-ready bullet points, then populated into a pre-built content template using python-pptx.

The deck is a first draft: sales can open it in PowerPoint, make tweaks, and send to the client. The template adherence is enforced through three layers: strict LLM prompt constraints on word/character counts, auto-fit text settings with minimum font size floors in the template placeholders, and post-processing validation that truncates any overlong content before it reaches the slide.

## User Stories

1. As a salesperson, I want to download a branded PowerPoint deck from my insights brief with one click, so that I can prepare client presentations faster.
2. As a salesperson, I want the deck to strictly follow our internal Prism template (backgrounds, fonts, logos, layout), so that it looks professional and on-brand without manual reformatting.
3. As a salesperson, I want the deck content to be concise slide-ready bullet points, not full paragraphs from the brief, so that the slides are presentation-ready.
4. As a salesperson, I want the deck to include the advertiser name, topic, and KPI on the title slide, so that the presentation is clearly identified.
5. As a salesperson, I want the At a Glance data presented as big numbers with labels on a stats slide, so that key data points have visual impact.
6. As a salesperson, I want the Advertiser Overview and Editorial Insights on a two-column slide, so that I can present the opportunity narrative early in the deck.
7. As a salesperson, I want Messaging & Tone Recommendations on their own slide, so that I can showcase our creative direction to the client.
8. As a salesperson, I want Recommended Products and Next Steps on a closing slide, so that the deck ends with a clear call to action.
9. As a salesperson, I want the downloaded file named with the advertiser and topic (e.g. Prism_Plan_Yakult_Gut_Health.pptx), so that I can find it easily in my downloads folder.
10. As a salesperson, I want a loading spinner on the button while the deck is generating, so that I know the system is working.
11. As a salesperson, I want the download to trigger automatically when ready (no modal or preview), so that the experience is fast and frictionless.
12. As a salesperson, I want the "Download Deck" button to only appear after insights have been generated, so that the UI isn't cluttered before there is content.
13. As a salesperson, I want the deck to always have exactly 5 slides in a consistent order, so that I know what to expect and can quickly navigate to the slide I want to tweak.
14. As a salesperson, I want the slide content to never overflow or clip, so that the deck looks polished without me having to fix formatting.
15. As an unauthenticated user, I should not be able to access the download deck endpoint, so that the feature is protected.
16. As a salesperson, I want the "Download Deck" button to sit alongside "Draft Email" with equal prominence, so that both export options are easily discoverable.

## Implementation Decisions

### Content template creation (one-time)
- A simplified content template `.pptx` is created with 5 reusable slide layouts, each with proper named placeholders
- Background images and brand logos are extracted from the existing Prism Story Deck Master template and embedded into the new layouts
- Font family: Barlow (Regular, Medium, SemiBold, ExtraBold) — matching the existing deck
- Slide dimensions: 10" x 5.62" (widescreen, matching the master)
- Template stored in the project data directory as a static asset
- All text placeholders configured with shrink-on-overflow and a minimum font size floor to handle edge cases gracefully

### Slide layout definitions

**Layout 1 — Title**: Topic, advertiser name, and KPI displayed prominently. Branded background, logo in corner.

**Layout 2 — Stats**: 6 data points from the At a Glance section, each as a large value (max 5 characters) with a short label (max 8 words). Grid arrangement matching the visual style of the master template's stats slides.

**Layout 3 — Two-Column Body**: Left column: Advertiser Overview (heading + 3-4 bullets). Right column: Editorial Insights & Strategic Alignment (heading + 3-4 bullets). Max 15 words per bullet.

**Layout 4 — Body**: Messaging & Tone Recommendations. 3-4 recommendations, each with a short headline (max 6 words) and a detail line (max 20 words).

**Layout 5 — Closing/CTA**: Top 2-3 recommended ad formats with key metrics. "Next Steps" section with a CTA to book a meeting.

### Slide content generator module
- Single function: accepts the full brief content, topic, advertiser, and KPI
- Calls GPT-4o-mini with a structured prompt that specifies exact field names, word/character limits, and output format (JSON)
- Three-layer content enforcement:
  1. **Prompt constraints**: explicit limits per field (e.g. "value: max 5 characters", "bullet: max 15 words")
  2. **Auto-fit text**: template placeholders shrink text on overflow with a minimum font size floor
  3. **Post-processing validation**: JSON response validated against expected schema, fields truncated to hard limits before reaching the deck builder
- Model configured via a constant in config (default: gpt-4o-mini), consistent with the email drafter pattern

### Deck builder module
- Single function: accepts the validated slide content dict, topic, and advertiser; returns a BytesIO buffer containing the .pptx
- Opens the content template, creates one slide per layout, populates placeholders with content
- Handles text formatting: applies correct Barlow font variants, sizes, colours, and alignment per placeholder
- Purely deterministic — no LLM calls, no network, no side effects. Given the same input dict, always produces the same output.
- Returns bytes buffer ready to stream as an HTTP response

### API endpoint
- `POST /api/download-deck` accepts `{ content: string, topic: string, advertiser: string, kpi: string }`
- Protected by the existing `get_current_user` JWT dependency
- Calls slide content generator, then deck builder
- Returns a `StreamingResponse` with:
  - Content type: `application/vnd.openxmlformats-officedocument.presentationml.presentation`
  - Content-Disposition header: `attachment; filename="Prism_Plan_{Advertiser}_{Topic}.pptx"` (spaces replaced with underscores)

### Frontend integration
- "Download Deck" button rendered next to "Draft Email" in the same row, equal prominence
- Button shows loading spinner during generation (replaces button text with "Generating...")
- On response: creates a blob URL from the response, triggers a browser download via a temporary anchor element
- On error: shows an inline error message (same pattern as insights error handling)
- Only visible when `result` is set (insights have been generated)

### Analytics
- `"Download Deck Clicked"` — with `{ topic, advertiser, kpi }`
- `"Deck Generated"` — with `{ topic, advertiser, kpi, duration_ms }`
- `"Deck Download Failed"` — with `{ error_message }`

## Testing Decisions

Tests should verify external behaviour through the module's public interface, not implementation details. Mock external dependencies (OpenAI API) at the boundary. The deck builder is deterministic and should be tested without mocks.

**Modules to test:**

1. **Slide content generator** (pytest, mocked OpenAI)
   - Prompt includes topic, advertiser, KPI, and brief content
   - Model is GPT-4o-mini
   - Post-processing truncates overlong fields to hard limits
   - Missing fields in LLM response are handled gracefully (defaults or errors)
   - *Prior art*: follows the same mocked OpenAI pattern as the email drafter tests

2. **Deck builder** (pytest, no mocks)
   - Given a valid content dict, output is a valid .pptx file (parseable by python-pptx)
   - Output has exactly 5 slides
   - Each slide contains the expected text content in the correct placeholders
   - Fonts are Barlow family
   - This is the most valuable test — catches template and layout regressions
   - *Prior art*: similar to format validation tests, but using python-pptx to inspect output

3. **API endpoint** (pytest, FastAPI TestClient)
   - Returns 401 without auth
   - Returns correct content type and content-disposition headers
   - Response body is a valid .pptx file
   - Mock the slide content generator and deck builder to avoid real LLM calls
   - *Prior art*: same TestClient + auth pattern as email samples and email drafter API tests

## Out of Scope

- **Slide selection or customisation before download** — the deck always produces the same 5 slides in the same order. Customisation happens in PowerPoint after download.
- **In-browser preview of slides** — PowerPoint files can only be properly viewed in PowerPoint. No preview modal.
- **Editable content before download** — the brief is already the input; the LLM condenses it. No intermediate editing step.
- **Custom images per deck** — all decks use the same branded backgrounds and logos from the template. Per-advertiser images are not in scope.
- **Audience Timing and Key Recommendations sections** — these are detail for the meeting itself, not the teaser deck.
- **Slide animations or transitions** — static slides only.

## Further Notes

- The content template is a static asset created once and stored in the project. If the brand template changes, the content template needs to be regenerated — but this is a rare event and can be done manually.
- Barlow fonts must be installed on the machine opening the deck for correct rendering. If not installed, PowerPoint will substitute a fallback font. This is standard behaviour and acceptable — sales team machines will have Barlow installed.
- The "variety comes from content, not layout" principle is critical: every deck has the same 5 layouts in the same order. This is a feature, not a limitation — sales people want consistency and predictability. The content (numbers, bullets, recommendations) is what changes per brief.
- `python-pptx` is already installed in the project (added during initial setup). It should be added to `requirements.txt` if not already present.
- The dynamic filename sanitises the advertiser and topic strings (replaces spaces with underscores, removes special characters) to ensure valid filenames across operating systems.
