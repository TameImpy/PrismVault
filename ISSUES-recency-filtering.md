# Issues: Recency filtering for DuckDuckGo advertiser research

Parent PRD: `PRD-recency-filtering.md`

---

## Issue 1: Add `timelimit` parameter to DuckDuckGo search

### What to build

Add time-based filtering to the DuckDuckGo search pipeline. `_run_search()` gains a `timelimit` parameter that is passed directly to `ddgs.text()`. `run_skill()` reads a `timelimit` field from the skill's YAML config, defaulting to `"y"` (past year) when omitted. All three existing skill files are updated with their `timelimit` value: Company Overview gets `null` (no filter), Strategy & Challenges gets `"y"`, and Recent News gets `"y"`.

### Acceptance criteria

- [ ] `_run_search()` accepts a `timelimit` parameter and passes it to `ddgs.text()`
- [ ] `run_skill()` reads `timelimit` from skill config, defaulting to `"y"` when omitted
- [ ] Company Overview skill has `timelimit: null` in frontmatter
- [ ] Strategy & Challenges skill has `timelimit: "y"` in frontmatter
- [ ] Recent News skill has `timelimit: "y"` in frontmatter
- [ ] `load_skills()` includes `timelimit` in parsed skill dicts
- [ ] Tests verify `timelimit` is parsed from frontmatter (including `null` and missing values)
- [ ] Tests verify default `timelimit` is `"y"` when omitted
- [ ] Tests verify `_run_search()` passes `timelimit` through to DuckDuckGo (via mock)

### Blocked by

None — can start immediately.

### User stories addressed

- User story 1, 4, 5, 6, 8, 9

---

## Issue 2: Add `{year}` dynamic placeholder to skill queries

### What to build

Add support for a `{year}` placeholder in skill query strings, populated from `datetime.now().year` at runtime. Update existing skill query strings to use `{year}` instead of hardcoded year references (e.g. `"2025 2026"`). This keeps queries current without manual maintenance.

### Acceptance criteria

- [ ] `run_skill()` substitutes `{year}` in query strings with the current year
- [ ] Strategy & Challenges queries use `{year}` instead of hardcoded `"2025 2026"`
- [ ] Recent News queries use `{year}` instead of hardcoded `"2025 2026"`
- [ ] Company Overview queries are unchanged (no year references)
- [ ] Tests verify `{year}` placeholder is recognised in skill queries
- [ ] Existing `{brand}` placeholder substitution is unaffected

### Blocked by

None — can start immediately.

### User stories addressed

- User story 3, 7

---

## Issue 3: Add recency instructions to GPT-4o skill prompts

### What to build

Update the GPT-4o processing prompts in Strategy & Challenges and Recent News skills to reinforce recency preferences. Strategy & Challenges gets an instruction to prioritise current strategic direction and flag outdated information. Recent News gets an instruction to focus on the last 6 months and deprioritise older content. Company Overview prompt is unchanged.

### Acceptance criteria

- [ ] Strategy & Challenges prompt includes instruction to prioritise current/recent strategic direction
- [ ] Recent News prompt includes instruction to focus on developments from the last 6 months
- [ ] Recent News prompt includes instruction to deprioritise or exclude older content
- [ ] Company Overview prompt is unchanged
- [ ] No code changes required — prompt text only

### Blocked by

None — can start immediately.

### User stories addressed

- User story 2, 3, 10
