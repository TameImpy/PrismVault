# PRD: Recency filtering for DuckDuckGo advertiser research

## Problem Statement

The advertiser research feature (powered by DuckDuckGo search via the skills system) frequently returns outdated results — news articles and information from years ago surface alongside current data. This makes the Advertiser Overview section of generated briefs unreliable, as sales teams may present stale information to clients. The tool needs to bias strongly toward recent, commercially relevant information.

## Solution

Add time-based filtering at two levels: the DuckDuckGo API level (to prevent old results from being fetched) and the GPT-4o processing level (to instruct the LLM to prioritise recency). Make this configurable per skill via the existing YAML frontmatter system, with a sensible default. Also add a dynamic `{year}` placeholder to keep skill query strings from going stale over time.

## User Stories

1. As a sales user generating a brief, I want the Advertiser Overview to reflect the brand's current situation, so that I don't present outdated information to clients.
2. As a sales user, I want Recent News results to focus on the last 6 months, so that I'm aware of the brand's latest campaigns, launches, and announcements.
3. As a sales user, I want Strategy & Challenges to reflect the brand's current priorities, so that I can align our proposition with what matters to them now.
4. As a sales user, I want Company Overview to still include foundational/evergreen information, so that I understand what the company does even if that information isn't recent.
5. As a skill author, I want to control recency filtering per skill via a simple YAML field, so that I can tune each research dimension independently.
6. As a skill author, I want a sensible default recency filter applied when I don't specify one, so that new skills are biased toward freshness without extra configuration.
7. As a skill author, I want to use a `{year}` placeholder in my query strings, so that year references stay current automatically without manual updates.
8. As a skill author, I want to opt out of time filtering entirely by setting `timelimit: null`, so that evergreen skills like Company Overview aren't artificially constrained.
9. As a developer, I want the time filter passed through to the DuckDuckGo API, so that irrelevant old results are excluded before they reach GPT-4o processing.
10. As a developer, I want GPT-4o prompts to reinforce recency preferences as a backstop, so that any old results that slip through the API filter are deprioritised in the summary.

## Implementation Decisions

- **Dual-layer filtering**: Time filtering is applied at both the DuckDuckGo API level (`timelimit` parameter) and the GPT-4o prompt level (recency instructions in skill prompts). The API filter is the primary mechanism; the prompt instruction is a backstop.
- **Per-skill `timelimit` in YAML frontmatter**: Each skill can specify a `timelimit` value in its frontmatter. Valid values are DuckDuckGo's native options: `"d"` (day), `"w"` (week), `"m"` (month), `"y"` (year), or `null` (no filter).
- **Default `timelimit` is `"y"`**: When a skill omits the `timelimit` field, it defaults to `"y"` (past year). This biases new skills toward freshness. A skill author must explicitly set `timelimit: null` to disable filtering.
- **Skill-specific settings**:
  - Company Overview: `timelimit: null` (evergreen information is valuable)
  - Strategy & Challenges: `timelimit: "y"` (strategies shift annually)
  - Recent News: `timelimit: "y"` at API level, with GPT-4o prompt instructing focus on last 6 months (DuckDuckGo has no native 6-month option)
- **Dynamic `{year}` placeholder**: A new `{year}` placeholder is supported in skill query strings, populated from `datetime.now().year` at runtime. This replaces hardcoded year references (e.g. `"2025 2026"`) so queries stay current without manual maintenance.
- **`_run_search()` interface change**: The function gains a `timelimit` parameter that is passed directly to `ddgs.text()`.
- **`run_skill()` changes**: Reads `timelimit` from the skill config (with `"y"` default), passes it to `_run_search()`, and substitutes `{year}` in query strings alongside `{brand}`.
- **Prompt updates**: Strategy & Challenges prompt gains a line instructing GPT-4o to prioritise the most current strategic direction. Recent News prompt gains a line instructing focus on the last 6 months and deprioritising older content.

## Testing Decisions

- Tests should verify external behaviour (skill loading, config parsing, placeholder substitution) rather than internal implementation details.
- Existing tests in `test_web_search.py` validate skill structure and placeholders — these will be extended.
- New tests to add:
  - `timelimit` is correctly parsed from skill frontmatter (including `null` and missing values)
  - Default `timelimit` is `"y"` when omitted from a skill
  - `{year}` placeholder is supported in skill queries
  - `_run_search()` passes `timelimit` through to DuckDuckGo (via mock)
- Prior art: `tests/test_web_search.py` — same pattern of loading skills and asserting structure/content.

## Out of Scope

- Changing the search provider (e.g. replacing DuckDuckGo with another API)
- Adding date-based post-filtering of raw results (unreliable date metadata from DuckDuckGo)
- Modifying how results are displayed in the frontend
- Changes to the synthesiser prompt or other pipeline stages
- Adding new skills (this PRD only modifies existing ones)

## Further Notes

- DuckDuckGo's `timelimit` parameter only supports `"d"`, `"w"`, `"m"`, and `"y"`. There is no native 6-month option, which is why Recent News uses `"y"` at the API level combined with a GPT-4o prompt instruction for 6-month focus.
- The `{year}` placeholder follows the same substitution pattern as the existing `{brand}` placeholder, keeping the skills system consistent and simple.
