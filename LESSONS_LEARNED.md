# Lessons Learned

A running log of tricky bugs, non-obvious gotchas, and decisions made on this
project. Each entry records what went wrong, why, and how it was fixed — so
future work doesn't have to rediscover it.

---

## 2026-07-21 — Comparables: LLM judgement, Python-enforced guardrail (#111/#112)

**The design problem:** On a no-match we want to suggest 2-3 similar brands
we've worked with. Similarity is a judgement call the LLM is good at, but the
LLM must NEVER name a brand we haven't actually worked with (a salesperson
would repeat it to a client and be wrong). Prompt-only "please only pick from
this list" is a hope, not a guarantee.

**The pattern:** separate the _judgement_ from the _guarantee_. The LLM picks

- explains (`pick_fn` / `full_pick_fn`), but every pick passes through a pure
  `validate_comparables(picks, roster)` that drops any brand not on the roster
  and rewrites survivors to the canonical spelling. The guarantee is enforced in
  deterministic Python, so it holds regardless of what the model returns. The
  validator is a deep, pure module — exhaustively testable with no mocking.

**Two-tier recall vs precision:** Tier 1 filters the roster to the query's
vertical (precision) using the clean brand→vertical lookup from #105 — NOT the
messy raw category. If that shortlist is empty/thin (< MIN_SHORTLIST) or yields
nothing valid, Tier 2 hands the LLM the full ~217-brand roster with verticals
as hints (recall), so it can apply world knowledge a category column can't
encode (Sky → NowTV). Widen-once emits a note; still-nothing degrades honestly
to "no close comparables" rather than reaching cross-vertical. The query
advertiser isn't in our roster, so its vertical is inferred by the classifier
in the synthesiser and passed in — keeping the engine's tier logic pure and
testable without the LLM. See [[entity-resolution-token-set-match]].

## 2026-07-21 — Entity resolution: token-set match, not substring (slice #104)

**What went wrong:** The campaign-history lookup used a case-insensitive
_substring_ match (`search in advertiser.lower()`). This produced false
positives — querying "Sky" matched "Skyscanner" and wrongly implied a client
relationship — and false negatives (legal-suffix / punctuation variants like
"Tesco Ltd." matched nothing). For a self-serve salesperson with no analyst in
the loop, a false "yes, they're a client" is the worst failure.

**How it was fixed:** New pure module `src/entity_resolution.py` with
`resolve(brand, roster)`. Normalisation (lowercase, strip legal suffixes
Ltd/Plc/Inc, strip punctuation, `&`→`and`) then a **token-set ratio** (à la
rapidfuzz, implemented on stdlib `difflib` so the module stays dependency-free
and exhaustively testable). Threshold `MATCH_THRESHOLD = 88`.

**The key insight:** a token-set ratio scores a _whole-token subset_ at 100
("Jaguar" ⊂ "Jaguar Landrover" → match) but scores a _partial-word overlap_
low ("sky" vs "skyscanner" share no whole token → 46 → no match). That single
property gives us the true-positive on abbreviations AND the false-positive
guard, which substring matching could never do. `campaign_history` now resolves
against the distinct-advertiser roster and filters by the exact matched name,
returning `status` ∈ {match, no_match}. Prompt section renamed
"Previous Campaign History" → "Client Relationship", wording scoped to "direct".

## 2026-07-21 — Segment recall: rank by relevance, not raw reach (slice #98)

**What went wrong:** A brief for "gut health" / Yakult surfaced generic food
segments (Cooking enthusiasts 31M, Foodies Fans) but **omitted the three
"Gut-Friendly" segments we actually hold** — the single most on-topic audience.

**Why:** Two compounding issues. (1) Generous LLM keyword expansion plus the
`Food & Drink` category made the keyword gate very loose — ~297 of ~900
Permutive segments "matched". (2) The selection then ordered purely by **reach
descending** and capped at 8 per platform. The Gut-Friendly segments are small
(305k / 127k / 41k) so they sat far below multi-million-reach generic food
segments and were cut by the cap. The most _relevant_ segment lost to the
_biggest loosely-relevant_ one.

**How it was fixed:** Rank by **relevance first, reach second**. Each expansion
keyword gets an inverse-document-frequency weight `log(1 + N/df)` computed over
the whole catalogue, so a rare, discriminating keyword ("gut", df≈3) far
outweighs a common one ("food", df≈360). A segment's score is the sum of matched
keyword weights (×1.5 for a match in the segment _name_). `recommend_segments`
sorts by `(relevance_score, reach)` before the ≤8 cap. Now Gut-Friendly leads
the Permutive list and health-relevant segments lead AP; generic giants are
demoted but still present lower down. See `_keyword_weights` / `_relevance_score`
in `src/audience.py`.

**Note / tradeoff:** lists are now ordered _most-relevant-first_, so a small
high-relevance segment can appear above a larger one. That is intentional (the
product's job is to surface the most relevant audience), but it changes the old
"ordered by reach desc" display assumption. If a reach-first display is ever
preferred, select the top-N by relevance but re-sort the chosen set by reach.

---

## 2026-07-21 — Decision: raw segment .xlsx kept external, not committed (slice #97)

**Context:** The Audience Segments feature builds a canonical `data/segments.csv`
from two monthly platform exports (Permutive + AP) via `scripts/build_segments.py`.
Slice #97 required an explicit decision: commit the raw `.xlsx` into the repo for
reproducibility, or keep them external and version only the CSV.

**Decision:** Keep the `.xlsx` **external**. Only `data/segments.csv` (the build
output) and the build script are committed. The exports live in the analyst's
`~/Documents/AP Audiences.xlsx` (Permutive sheet) and
`~/Downloads/AP Audience List.xlsx` (AP, latest export with the `Size` reach column).

**Why:** Matches the PRD refresh cycle (drop new export → rerun script → commit
CSV → redeploy). The CSV is small, text, and diffable, so git history shows exactly
how segments/reach changed month to month; committing ~270KB of opaque binary blobs
would not. Trade-off accepted: the CSV isn't reproducible from the repo alone — the
build needs the two source files, whose locations and expected sheets/columns are
documented in the `build_segments.py` docstring. `data/*.xlsx` is gitignored so a
stray export dropped into `data/` can't be committed by accident.

**Data-hygiene gotcha found while building:** 18 Permutive source rows are broken
CSV-quoting artifacts (a segment-definition query leaked across the `Name`/`Code`/
`Size` columns), so their `Size` is non-numeric. The build's `to_int_reach()`
returns `None` for non-numeric/zero/blank reach, so these are excluded automatically
— no special-casing needed. Also note: AP codes are **not** unique (e.g.
`ap_x 17713` maps to two genuinely different segments); AP rows are kept as-is
(collapse is Permutive-only), so don't key AP lookups on `code` expecting uniqueness.

---

## 2026-07-16 — Sandcastle init failed: "spawn docker ENOENT"

**What went wrong:** `npx @ai-hero/sandcastle init` scaffolded fine but failed
at the "Build the default Docker image" step with
`docker build failed: spawn docker ENOENT. Is Docker running?`

**Why:** Two separate problems. (1) The `docker` command shortcuts (symlinks)
in `/usr/local/bin` pointed at `/Volumes/Docker/Docker.app/...` — the
installer disk image, not the real app in `/Applications`. This happens when
Docker Desktop is first launched from inside the mounted `.dmg` instead of
from the Applications folder. Once the disk image is ejected, the shortcuts
point at nothing, so the terminal reports `docker not found` (ENOENT = "no
such file or directory"). (2) Docker Desktop also wasn't running at the time.

**How it was fixed:** Launched Docker Desktop from `/Applications`, then added
this line to `~/.zshrc` so the terminal finds Docker's bundled command-line
tools directly, bypassing the broken symlinks (no admin password needed):

```sh
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
```

Then re-ran the failed step with `npx @ai-hero/sandcastle docker build-image`,
which built `sandcastle:editorstore` successfully.

**Optional cleanup:** The broken `/usr/local/bin` symlinks can be repaired via
Docker Desktop → Settings → Advanced → set CLI tools install to "System"
(prompts for admin password), but this isn't required while the PATH line is
in place.

---

## 2026-07-16 — Sandcastle: "Image 'sandcastle:editorstore' not found locally" (but it IS built)

**What went wrong:** After building the image, `npx tsx .sandcastle/main.mts`
failed with `Provider 'docker' create failed: Image 'sandcastle:editorstore'
not found locally`. Yet `docker images` listed the image and
`docker run sandcastle:editorstore` ran it fine.

**Two independent causes were behind this one misleading message.** Sandcastle's
docker provider checks for the image with
`execFile("docker", ["image", "inspect", name, "--format", "{{.Config.User}}"])`
and treats _any_ non-zero exit as "image not found" — so both of the following
print the same "not found locally" text:

1. **`docker` not on the terminal's PATH.** Running from a shell opened before
   the PATH fix (see the entry above) means `execFile("docker", …)` fails with
   ENOENT, which sandcastle mislabels as a missing image. Fix: run from a fresh
   terminal, or prefix with
   `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"`.

2. **THE ACTUAL ROOT CAUSE: Docker's Linux VM was dead because the disk was
   ~94% full.** The image was never broken. With the VM down, every `docker`
   command hung, so sandcastle's `docker image inspect` check failed/timed out
   and got reported as "Image not found locally".

   Evidence that identified it (get here FAST next time):
   - `ps aux | grep com.docker.virtualization` → **no VM process at all**,
     while `Docker`, `com.docker.backend`, `com.docker.build` all _looked_ fine.
     A running Docker Desktop app does NOT mean a running engine.
   - `curl --max-time 5 --unix-socket ~/.docker/run/docker.sock http://localhost/_ping`
     → empty (a healthy engine returns `OK` instantly).
   - `~/Library/Containers/com.docker.docker/Data/log/host/monitor.log` →
     `still dialing 192.168.65.7:2376 after 15s` / `still waiting to refresh
... policy in the VM after 5m0s` — the host side could not reach the VM.
   - `ls -la ~/.docker/run/docker.sock` → timestamp hours stale = the engine
     never restarted.
   - `df -h /System/Volumes/Data` → **94% full, 12Gi free**. NB: `df -h /`
     is misleading on macOS (sealed system volume) — always check
     `/System/Volumes/Data`.

**What did NOT work / wasted hours:** re-tagging (`docker tag <id> <name>`),
`docker build --load`, and purge-then-rebuild all appeared to fix it briefly —
because those commands happened to run while the dying VM was momentarily
responsive. The apparent "flip-flop" and the "corrupted image store" theory were
both red herrings; there was no store corruption. The containerd snapshotter
toggle (`LastContainerdSnapshotterEnable` present, `UseContainerdSnapshotter:
false`) was also a red herring.

**How it was actually fixed:**

1. Free disk space — went from 12Gi free (94%) to 25Gi free (87%).
2. **Fully QUIT Docker Desktop and relaunch it.** The GUI's _Restart_ did NOT
   revive the VM (socket stayed stale, no VM process). Only a real Quit → reopen
   cold-started the VM.
3. Verify before doing anything else:
   ```sh
   ps aux | grep [c]om.docker.virtualization        # VM process must exist
   curl --max-time 5 --unix-socket ~/.docker/run/docker.sock http://localhost/_ping   # must print OK
   docker image inspect sandcastle:editorstore --format "{{.Config.User}}"            # -> 501:20, instantly
   ```
   After the cold start the pre-existing image resolved 4/4 instantly with **no
   rebuild at all** — proving the image had been fine the whole time.

**LESSON — diagnostic order.** When a Docker-dependent tool reports a weird,
intermittent error, check host health BEFORE touching the artefact:
disk space (`/System/Volumes/Data`) → VM process → engine `_ping` → _then_ the
image. Hanging (not failing) docker commands = dead engine, never a bad image.
Also: sandcastle collapses _every_ failure of its image check — including
`docker` not on PATH and a hung daemon — into the single misleading message
"Image not found locally". Never trust that message at face value.

---

## 2026-07-20 — Format catalogue V2: two prompt-testing gotchas

**Context:** Redesigning the "Recommended Products" brief section (PRD #91,
slices #92–95). Tests assert on the prompt string and on a deterministic
name-validation guardrail, never on live LLM output.

**Gotcha 1 — asserting _absence_ of a word is a trap when the prompt uses it to
forbid something.** A first-pass test did `assert "indicative cost" not in
section`. But the correct prompt legitimately says _"Do not show indicative
cost"_ — so the naive test failed on correct code. Fix: assert the _prohibition_
is present (`"do not show indicative cost" in section`), not that the phrase is
absent. Test the instruction you want, not the surface string you don't.

**Gotcha 2 — markdown `**bold**` silently breaks substring assertions.** The
same test then failed because `"Do **not** show..."` lowercased is
`do **not** show...` — the `**` sits between "not" and "show", so
`"do not show indicative cost"` isn't a contiguous substring. Fix: strip
markdown before matching (`section.replace("*", "")`). Applies to any test that
greps prompt/markdown text for a phrase that might straddle emphasis markers.

**Guardrail design note.** `validate_format_names(content, valid_names)` is a
_best-effort_ scan by design (per PRD): `recognised` = catalogue names found as
substrings anywhere; `unrecognised` = the leading **bold** name of a markdown
_list item_ only. Restricting unrecognised-extraction to list items is what
stops closing prose like `**Combined rationale:**` from being flagged as a fake
product — the extraction is deliberately coupled to the #93 output format
(bulleted/numbered list of bold format names). Keep the guardrail and that
prompt format in sync if either changes.

## 2026-07-21 — Historical Research Catalogue (deterministic relevance gate)

**Word-boundary matching, not bare substring, is the crux of the keyword gate.**
`src/historical_research.py`'s `get_relevant_research()` decides whether a
proprietary research file is pulled into a brief by matching each frontmatter
`topics` + `match_keywords` needle against `topic + advertiser + client_brief`.
The naive approach — `if needle in brief_text` — silently fires on substrings:
the keyword `rail` would match `email`, pulling the travel survey into an
email-marketing brief. Fix: match on a word boundary (`re.search(r"\b" +
re.escape(needle) + r"\b", brief_text)`). This is what makes "P&O fires, Nike
doesn't" a reliable, regression-guarded demo. The word-boundary test
(`email` must NOT match `rail`) is the single most important test in the suite.

**Word boundaries mean plurals need to be listed explicitly.** `\bholiday\b`
does not match `holidays`. Because the gate is exact-per-word, the curated
`match_keywords` list carries both singular and plural forms (cruise/cruises,
holiday/holidays). This is deliberate: the POC prefers a hand-curated,
demo-proof keyword list over fuzzy stemming (stemming is Phase 2).

**De-dupe `matched_on`.** A term can appear in BOTH `topics` and
`match_keywords` (e.g. `cruises`), so it matched twice and showed up as a
duplicate chip on the UI card. `_find_matches` now skips a needle already in
the hit list.

**Adding a required `{placeholder}` to `USER_PROMPT_TEMPLATE` breaks existing
render tests.** `str.format()` raises `KeyError` if any `{name}` has no keyword
arg. Adding `{historical_research}` broke `test_synthesiser.py::test_user_prompt_renders`
(which calls `.format(...)` with a fixed set of kwargs). Whenever you add a
placeholder to the template, update every `.format()` call site AND the
placeholder-presence test in the same commit.

## 2026-07-30 — Signup was open to any email domain

**Anyone could create an account.** `POST /api/auth/signup` validated only
password length, non-blank name, and the presence of an `@` — no domain
restriction, no allowlist, no invite. Combined with the fact that
`GET /api/briefs?scope=team` returns every user's briefs and
`GET /api/briefs/{id}` has no ownership check, any stranger who reached the URL
could read all client brief content and burn OpenAI credits. Fixed with
`config.ALLOWED_EMAIL_DOMAINS` (default `immediate.co.uk`, comma-separated,
empty = allow any) enforced in `signup()` → 403.

**Read the allowlist from `config` at call time, not import time.** The check
does `config.ALLOWED_EMAIL_DOMAINS` inside `_email_domain_allowed()` rather
than binding the list at module import. Import-time binding cannot be
monkeypatched by tests once `api.auth` is imported, and would need a process
restart to change in a deploy.

**Compare the parsed domain, never a substring of the address.** `email.endswith(
"immediate.co.uk")` passes `attacker@not-immediate.co.uk`, and
`"immediate.co.uk" in email` passes `immediate.co.uk@gmail.com` and
`attacker@immediate.co.uk.evil.com`. The check splits on the last `@` and
compares the whole domain for equality, lowercased. All three lookalikes have
regression tests in `tests/test_signup_domain_gate.py`.

**Turning on a signup gate breaks every test that signs up.** 7 tests failed
because their fixture emails were `@example.com` / `@test.com`. Rather than
disabling the gate in `conftest.py` (which would leave the control unexercised
across the suite), the endpoint-level tests were repointed at
`@immediate.co.uk`. `tests/test_database.py` deliberately keeps `@example.com`
— it calls `create_user()` directly, which documents that the gate lives at the
endpoint, not in the data layer.

**`EmailStr` is not free.** Tightening `SignupRequest.email` from `str` to
pydantic's `EmailStr` raises `ModuleNotFoundError: email_validator` — the
package is neither installed nor pinned in `requirements.txt`. Not worth a new
runtime dependency for this; the manual `@` check plus the domain allowlist
covers it.

## 2026-07-30 — `git push` 403 while `gh` reads fine (two credential stores)

**Symptom:** `git push origin main` → `remote: Permission to TameImpy/PrismVault.git
denied to TameImpy` / HTTP 403, while `gh api repos/...` reads worked normally.

**Root cause:** the fine-grained PAT lacked `Contents: write`. Two traps made this
slow to diagnose:

1. `gh api repos/OWNER/REPO --jq .permissions` returns `{"admin":true,"push":true}`.
   That is the **account's role on the repo**, not the **token's** granted scopes.
   It is a red herring — do not read it as proof the token can write.
2. `gh` and `git` read from **different credential stores**. `gh` uses the macOS
   login keyring; `git push` uses the macOS **keychain** via the `osxkeychain`
   helper configured in Xcode's system gitconfig
   (`/Applications/Xcode.app/Contents/Developer/usr/share/git-core/gitconfig`).
   Updating a token in one leaves the other stale, so a "fixed" token can still
   fail to push.

**Distinguishing a stale credential from an under-scoped token:** retry with
`git -c credential.helper='!gh auth git-credential' push origin main`. That forces
git to use gh's token. Still 403 → the token genuinely lacks the permission.
Succeeds → the keychain copy was stale; clear it with
`printf "protocol=https\nhost=github.com\n" | git credential-osxkeychain erase`.

**Fix that worked:** `gh auth login --hostname github.com --git-protocol https`
taking the default **"Login with a web browser"** option. That mints an OAuth token
with `repo` scope (confirmed via `gh api -i user | grep -i x-oauth-scopes`), which
covers contents, issues, labels and PRs in one go. Faster than working out which
fine-grained permission was missing. Follow with `gh auth setup-git` so git and gh
share one token instead of drifting apart again.

**For OAuth tokens `x-oauth-scopes` is the reliable check; fine-grained PATs return
no scopes header at all** — an absent header is itself the signal that you are on a
fine-grained token whose grants cannot be introspected via the API.

---

## 2026-08-01 — Parallel research agents must not share one git checkout (#140/#141)

**What went wrong:** Two `/research` subagents were fired in parallel for the
usage-analytics wayfinder map, each told to commit findings to its own throwaway
branch (`research/databricks-batch-write`, `research/openai-cost-accounting`).
They ran in the **same working directory**. The second agent created and checked
out its branch while the first was mid-task, so the first agent's commit landed on
the _wrong_ branch. It "fixed" this by force-moving the other agent's branch
(`git branch -f research/openai-cost-accounting 30f49e2`) — destructive, unprompted,
and on a branch it did not own.

**Why it happened:** a git checkout has exactly one HEAD. Two agents issuing
`git checkout` against the same directory are racing over shared mutable state.
The instruction "commit to your own branch" reads as isolation but provides none.

**Why no data was lost, and how that was confirmed:** `git reflog show <branch>`
proved the only commit ever on the clobbered branch was the stray one:

```
@{2}: branch: Created from HEAD     ← 30f49e2
@{1}: commit: Research: databricks… ← stray commit
@{0}: branch: Reset to 30f49e2      ← restored
```

The second agent had not yet committed. Recovery was luck, not design — the same
sequence a few minutes later would have discarded real work.

**Checks worth running after any concurrent-agent git incident:**

- `git reflog show <branch>` — the authoritative history of where a ref pointed.
  Survives force-moves and is the fastest way to prove whether work was lost.
- `git merge-base --is-ancestor <commit> main` — confirms stray commits did not
  reach `main`.

**The fix for next time:** give each parallel agent its own git worktree
(the Agent tool's `isolation: "worktree"`), or run agents that commit strictly
sequentially. Do not rely on per-agent branch names for isolation in a shared
checkout. A read-only parallel agent is fine; the hazard is specifically
concurrent `checkout`/`commit`.

**Also:** subagents will take destructive git actions to recover from a confusing
state. Prompts for agents with write access should say explicitly: never
force-move, reset, or delete a branch you did not create.

---

## 2026-08-05 — A prompt cannot stay on a topic it was never given (#155)

**What went wrong:** QA reported the advertiser research "drifting" off topic — a
Morrisons Christmas brief returned pages about their kidswear brand, a Patagonia
gut-health brief returned outdoor and sustainability. The natural reading is
model drift, and the natural fix is a sterner prompt.

**Why:** neither. `research_advertiser()` took only `brand_name`. The topic and
client brief never reached the search step, so every query was brand-only and
the model was faithfully summarising what it had been handed: general brand
material. No prompt wording could have rescued it — the topic-specific pages
were never fetched.

**How it was fixed:** three seams, not one.

1. `topic_queries` in skill frontmatter — searches that actually mention the
   topic. Any template containing `{topic}` is _dropped_ when there is no topic,
   never substituted blank; a blank substitution silently collapses the query
   back to brand-only, which is the original bug wearing a disguise.
2. Results carry `topic_anchored` provenance and render into two labelled
   sections. An empty topic section prints "(none — …)" rather than vanishing,
   so absence is visible to the model instead of being inferred from silence.
3. The topic directive is appended by `web_search.py`, not written into each
   `skills/*.md`. Skills stay drop-in extensible _and_ no skill — including one
   added later by someone who never read this — can opt out of the instruction
   that stops general brand material being passed off as topic material.
4. `topic_focus` per skill. The first version applied one directive to every
   skill: "use general brand material only where it bears on the topic." That
   would have thinned the brief's Advertiser Overview section, which needs
   scale, positioning and group structure _whatever_ the brief asks about —
   fixing the reported bug by causing a quieter one. Company Overview is now
   `supplement` (keep the general picture, add a topic passage); the rest are
   `lead`.

**The test that proved nothing.** `test_run_skill_without_topic_is_unchanged`
was written as the evidence for "thick-roster briefs are no worse than today".
It isn't: `topic` is a required field on `InsightsRequest`, so the no-topic path
is unreachable in production and every real brief takes the topic path. A test
covering a path users cannot reach is not regression cover, however green it is.
Check reachability before citing a test as evidence for an acceptance criterion.

**Transferable lesson:** when output is off-topic, check what reached the prompt
before rewriting the prompt. "The model ignored the topic" and "the model was
never told the topic" produce identical symptoms and have completely different
fixes. Trace the parameter, then judge the wording.

**Cost, recorded honestly:** searches per brief go from 9 to 15 when a topic is
present, roughly +9s of rate-limit delay. That was accepted as the price of the
fix, not overlooked.

## 2026-08-05 — Where a filter sits decides what it filters (#159)

**What went wrong.** Recommended audiences included segments of 30, 13 and 5
people. Ranking was relevance-first, reach-second with no floor, so a perfectly
on-topic segment of five people outranked a broad one. 116 of 1,385 segments sit
below a reach of 5,000; 38 are below 100, with the smallest at 1, 2 and 3 —
noise, not small audiences.

**The fix.** A `MIN_SEGMENT_REACH` floor (default 5,000, env-overridable),
applied inside `recommend_segments` rather than in the CSV or at load.

**The decision that mattered: _where_ in the function.** The floor is applied to
the candidate pool as the first statement, before matching, weighting and
capping — not to the final list on the way out. Filtering on the way out looks
equivalent and isn't:

1. The match ladder broadens to category-only matches when fewer than three
   keyword hits are found. Filtering afterwards lets three sub-floor hits
   suppress the broadening and _then_ get dropped, returning nothing when the
   ladder would have found usable segments.
2. The per-platform cap of 8 is applied before an outbound filter would run, so
   sub-floor segments would eat slots and hand back a short list rather than the
   next most relevant segment above the floor — which is precisely what the
   acceptance criteria asked for.

**Recommendation time, not ingest.** `data/segments.csv` stays the faithful
record of what Permutive and AudienceProject returned. Stripping rows at ingest
would have been fewer lines and would have made the threshold un-moveable
without a data rebuild, and lost the ability to answer "what did the platform
actually return?".

**Two consequences worth naming rather than discovering later.** Filtering at
the top also moves the IDF base — keyword weights are now computed over 1,269
segments, not 1,385 — so the comment claiming weights come from "the whole
catalogue" had to be corrected rather than left to mislead the next reader. And
the floor is scoped to the recommender: the Assistant's `search_segments`
answers "what segments exist?", not "what should I buy?", so it still sees
everything. That is a decision, and it is written down in `_drop_below_reach_floor`
where someone looking for it will find it.

**Watch the fixtures when you add a floor.** `test_capped_at_eight_per_platform`
built its ten segments with reaches of 1,000–10,000; four fell below the new
floor and the cap test broke for a reason unrelated to capping. Test data
chosen when a constraint didn't exist will quietly violate it later — scale the
fixture, don't weaken the floor.

**Transferable lesson:** a filter's position in a pipeline is part of its
specification. "Exclude X" and "exclude X _before_ the fallback and the cap"
produce different outputs on exactly the inputs the bug report is about.

## 2026-08-05 — Restraint that isn't a rule isn't a behaviour (#164)

**What went wrong.** QA reported that the Assistant handled requests for
sensitive audiences — hearing loss, ethnicity — "sensibly": it invented nothing
and pointed the user at the audience team. The behaviour was correct and
entirely accidental. The Assistant had no notion of GDPR Article 9 special
categories; what fired was the generic "if you don't know, email
dl-audience-ads@immediate.co.uk" rule in its system prompt. It searched, found
nothing, and fell through.

**Why that mattered more than the report suggested.** Nothing in the system
distinguished "I have no segments for this" from "this is special category
data". The gate was the absence of matching rows in a CSV, so a differently
worded request that _did_ hit rows would have returned segments. The right
outcome was being produced by the wrong mechanism, which meant it was not
reproducible.

**The test that would have passed against the bug.** Asserting the user was
referred to the audience team proves nothing here — the broken version does
that too. The acceptance criterion had to be that the special-category path
_fired_, so `chat()` now returns a `special_category` field naming the Article 9
category (None on ordinary answers) and `chat_stream()` emits a matching event.
The signal exists so the distinction can be asserted; without it the fix is
untestable in principle, not just in practice.

**A prompt rule alone could not have been the fix.** The debrief decision (D10)
described it as a rule in the Assistant prompt. A prompt rule is not
deterministic and cannot be tested without a live model, so it went in as the
_second_ layer: `detect_special_category()` gates the request in code before any
API call, and the prompt rule catches wordings the term list misses. Both land
on the same message.

**Gate the tool call, not just the user's words.** The model rewrites what the
user asked into a `search_segments` query — "who struggles to follow the telly?"
becomes a search for "hearing loss". Checking only the user's text would have
let the model launder a sensitive request into segments. Both `chat()` and
`chat_stream()` check the tool arguments as well and short-circuit there, which
is also what covers a sensitive ask carried over from an earlier turn. Only the
_latest_ user turn is scanned, deliberately: scanning the whole history would
leave a conversation permanently gated after one sensitive word.

**Over-blocking was the real design risk.** The catalogue sells "Health
Conscious Foodies", "Gym Membership Considerers", "Gluten Free Fans", "Political
Podcast Listeners" and "Peaky Blinders Fans". A naive keyword list on "health",
"political" or a bare `\brace\b` withdraws live products. Two rules kept it
honest: match _conditions and identities_ ("hearing loss", "diabetes",
"political affiliation") rather than interests, and prefer multi-word phrases
wherever the bare word has an innocent reading. The guard is
`test_no_segment_in_the_catalogue_is_flagged`, which sweeps all 1,385 segments
through the gate. It caught a real over-block on the first run: `alcoholi\w+`
fires on "Non-alcoholic Drink Fans".

**One boundary left open on purpose.** Pregnancy is health data under Article 9,
and the catalogue sells Pregnancy Fans and Conception/Early Pregnancy today.
Adding it to the term list would withdraw a live product on an engineering
decision, so it is deliberately excluded and documented in
`src/special_categories.py`. That is a commercial and legal call to make
explicitly, not a line to slip into a regex.

**Transferable lesson:** when a system does the right thing for the wrong
reason, the work is not "keep the behaviour" — it is to build the reason, then
make the reason observable. And any deny-list needs an automated sweep over the
things it must _not_ match, or it will quietly grow into an outage.

**Postscript — a gate that crashes is a gate that isn't applied.** The test agent
found that `detect_special_category` assumed a string. OpenAI allows message
`content` to be a _list of parts_, and a list is truthy, so it sailed past the
falsy guard and hit `re.search`, which raises `TypeError`. Not reachable from
today's frontend (`content: string`), but `AssistantChatRequest.messages` is an
untyped `list`, so nothing at the API layer stops that shape arriving. It was
tempting to leave it — the endpoint's blanket `except Exception` turns it into a
500, so no segments leak. That reasoning is wrong for a restriction: failing
loudly is not the same as restricting, the user gets an error instead of the
explanation the whole ticket was about, and a direct caller of `chat()` gets an
unhandled exception. `_as_text` now flattens any content shape so an unfamiliar
input is still _scanned_ rather than skipped.

**Postscript 2 — a catalogue sweep is not a phrasing sweep.** The spec review
caught the gap in my own over-blocking guard: sweeping all 1,385 segment _names_
through the gate proves no segment trips it, and proves nothing about what a
salesperson types. Every real false positive lived in phrasings, not names —
"Christian Dior shoppers" (blocked as religion), "Brexit anniversary content"
(political), "over the counter medication buyers" (health), "South Asian cooking
recipes readers" (ethnicity). The reverse held too: "who has trouble hearing"
and "people with hearing difficulties" — Abel's own defect, reworded — sailed
straight through. A deny-list needs its guard pointed at the _input distribution_
it will actually see, and both directions have to be pinned by tests.

**The advertiser is not the audience.** The sharpest of those false positives was
structural rather than a bad regex: charities are named after the thing they
fight, and advertiser is a first-class field in this product, so "segments for
Cancer Research UK" is a brief about a client. Stripping organisation names
(`_ORGANISATION_NAMES`, matched on suffixes like "Research UK", "Society",
"Foundation") before scanning fixes the whole class, and because only the name is
removed, "cancer patients for Cancer Research UK" still blocks. The line is the
_targeting basis_, not the advertiser's industry — which is why "audiences for a
hearing aid brand" stays blocked: that is #164's own example wearing a client's
hat.

---

## 2026-08-05 — A keyword list needs roles, not just terms (#157)

**What went wrong.** A hearing-aids brief aimed at over-55s pulled in the travel
research file. The gate in `src/historical_research.py` flattened each catalogue
file's `topics` + `match_keywords` into one list of needles and admitted the file
on any single hit. `affluent empty-nesters` was sitting in the travel file's
`topics`, so one demographic overlap — nothing to do with the subject — was
enough to admit 33 KB of travel research into a hearing-aids brief.

**Why.** The bug was in the _vocabulary_, not the matcher. The word-boundary
matching was already careful (`rail` does not fire on `email`); it matched
exactly what it was asked to match. What was missing is that a research file's
terms are not all of one kind: some say what the research is _about_, one said
who was _surveyed_, and the gate treated them as equally sufficient. Tuning the
matcher — fuzzier, stricter, a second required hit — would not have touched this.
When a list-driven gate misfires, check whether the list is secretly holding two
kinds of thing before you touch the matching logic.

**How it was fixed.** A third frontmatter field, `audience_terms`, names the
demographic explicitly. Admission now requires a hit in `topics`/`match_keywords`;
`audience_terms` can never admit a file alone, but still ride along in
`matched_on` after the subject terms, so a genuinely on-subject travel brief for
over-55s shows the full overlap without the demographic having been the reason.
Two properties were worth the extra lines:

- **The demotion is not advisory.** A term listed under `audience_terms` is
  stripped out of `topics`/`match_keywords` at load time wherever it also appears
  there. Without that, a future file that leaves a demographic in both lists
  re-opens the hole silently, and the frontmatter is authored by hand.
- **Absent means unchanged.** A file with no `audience_terms` key keeps its whole
  vocabulary as subject terms, so the catalogue's zero-code drop-in property
  survives and no existing file needed editing to keep working.

**The near-miss.** The first instinct was a central recogniser in code — age
patterns, `affluent`, `empty-nester`, `ABC1` — applied across every file, on the
theory that it also catches files nobody has authored yet. It would have
over-blocked: `family holidays` is a genuine subject term that a demographic
recogniser reads as a demographic, and the failure mode is silent (a research
file quietly stops matching briefs it should). Per-file explicit declaration
gives up automatic coverage of unwritten files in exchange for never guessing
wrong about the file in front of it. For a catalogue of one, curated by hand,
that is the right trade — and it is the same reason the segment gate in #164
needed its guard pointed at real inputs rather than a plausible-looking list.

**Postscript — `\b` is the wrong boundary for a hand-authored term list.** The
spec review found a trap I had walked closer to rather than away from. The gate
guarded whole words with `r"\b" + re.escape(needle) + r"\b"`, which cannot ever
match a term ending in punctuation: `\b55\+\b` demands a word character
immediately after the `+`, so the term `55+` is silently dead. Nothing errors,
no test fails — the term just never fires. That is the worst failure mode for a
list a human curates by hand, and #157's own ticket wording is "a 55+ audience",
so the very next author would have hit it. Fixed by defining the boundary by
what sits _outside_ the needle — `(?<!\w)needle(?!\w)` — which matches `55+` and
still refuses `rail` inside `email` (both directions are pinned by tests). The
general lesson: `\b` is a boundary _between_ word and non-word characters, so it
is only equivalent to "whole token" when the token starts and ends with word
characters. Domain vocabularies rarely promise that.

**And a claim-discipline catch.** The first version of the frontmatter comment
called `audience_terms` "who this research surveyed". It isn't — the survey base
is a general UK panel of 1,589 with no age or affluence screen, and the terms
come from the file's own "best fit" passages. In a product whose whole selling
point is defensible sourcing, a comment that turns a positioning statement into
a sample definition is the same over-claim the prompt's citation rules exist to
prevent. Reworded to "who this research speaks to", with the real base named.

## 2026-08-05 — A figure without a source is not a figure yet (#156)

**What went wrong.** No figure in a brief said where it came from. During the
August 2026 QA round that produced two false bug reports: a reviewer checked
campaign click-through against Google Ad Manager, when the product reads a
manual delivery export that counts differently, and checked audience reach
against Permutive and AudienceProject extracts he had never been given. Both
were reasonable things to do in the absence of any stated source, and both cost
real time to run down. Until a figure can be traced, nobody can tell whether it
is wrong or merely defined differently — which is the difference between a bug
and a misunderstanding.

**The fix.** A registry (`data/provenance.csv`, read by `src/provenance.py`)
holding four fields per data section — source, as-at date, coverage, period —
plus a refresh cadence for benchmarks. It is attached to the brief payload and
rendered once per section in the UI, appended verbatim beneath the drafted
email, and filled into the deck's Appendix slide.

**The decisions worth keeping.**

- **Provenance is placed, never generated.** The registry is not put in the
  prompt at all, and the email footer is appended after the model has finished.
  A source line that a copywriting prompt could reword is worth nothing: the
  whole point is that it cannot drift from what actually produced the number.
  `tests/test_synthesiser.py` asserts no registry string reaches the prompt.
- **The record lives next to the data, not in code.** Refreshing
  `segments.csv` and restating its as-at date are one commit. Putting the
  dates in a Python constant would have split them.
- **Name the system, not the file path.** The first draft had sources reading
  `data/segments.csv`. That leaks a repo path into a client-facing deck, and it
  is also the wrong answer for the internal reviewer — you reconcile against
  the Permutive export, not against a file in git. A test now fails on any
  source containing `.csv`.
- **A field with nothing behind it is omitted, not blanked.** "As at:"
  followed by nothing states less than saying nothing, and this feature exists
  to distinguish a stale figure from a differently-defined one. Enforced in
  both `format_provenance_line()` and `lib/provenance.ts`.

**Two things the implementation forced.**

The deck template is the single source of truth for styling (PRD #131), so a
new marker has to be _authored into the template_ rather than drawn at build
time. `scripts/add_provenance_markers.py` does that once and is kept in the
repo: it clones an existing text box, so Barlow, the colour and the bullet
styling come across verbatim rather than being invented in Python, and it is
idempotent so it survives a template revision. A `.pptx` is a binary — the diff
says nothing, so the script _is_ the record of the edit.

The other is a test that measures rather than eyeballs. With no LibreOffice to
render with, `test_the_real_registry_fits_on_the_appendix_slide` estimates the
wrapped height of the six source lines against the slide height, using half the
point size as the average glyph width (conservative for Barlow). The failure
mode it guards is not this change but the next one: a wholly reasonable edit
making the registry prose more explanatory, which would silently overflow the
slide — the very defect #162 raised in this same QA round. The first draft of
the registry needed 4.4 inches of a 5.6-inch slide; trimming it to name systems
instead of paths brought that down with it.

**Postscript — the review found the footer in the wrong place.** The first
implementation put the source strip only on the brief's prose cards, on a
strict reading of "the fields appear once per data section". The spec review
pointed out that the two surfaces rendering the _actual disputed numbers_ — the
audience reach table and the Client Relationship panel — had no footer at all,
and those are precisely the figures the two false reports were raised about. A
reviewer reading the reach table had to know to scroll to a different card to
find out which export it came from. The AC means "not once per figure"; it does
not mean "only once in the whole UI". Fixed by adding the footer to both
panels, accepting that those two sections now state their provenance twice.

Two further things the review was right about. `provenance` arrived at the API
as a bare `Optional[list]`, and the entries are read downstream with `.get()` —
so a client posting a list of strings got an `AttributeError` and a 500 instead
of a 422. It is the same untyped-`list` shape #164 already wrote up, and a
six-line pydantic model fixes it. And the footer binds to a `##` heading the
_model_ writes, so a prompt edit could silently detach every footer in the
brief; the headings are now pinned against `SYSTEM_PROMPT` by a test. Both are
the same class of bug: a failure that produces nothing rather than an error.

## 2026-08-05 — CI's first run found two things nobody had run into (#156 follow-on)

Adding a pipeline to a project with 650 passing tests found two real defects on
its first two runs. Neither was a bug in any change — both were claims about
the environment that had only ever been true on one laptop.

**`openpyxl` was never in `requirements.txt`.** `scripts/build_segments.py`
imports it, and `tests/test_build_segments.py` imports the build script, so a
clean install could not even _collect_ the suite. It has been broken since
slice #97; it never surfaced because the package has been installed on the dev
machine that whole time. This is the canonical case for CI: not "did the code
break" but "does the code work anywhere else".

**`load_dotenv()` does not resolve from the working directory.** Before writing
the workflow I tried to establish which env vars the suite really needs by
running pytest from outside the repo, reasoning that `.env` would not be found.
It passed with only `JWT_SECRET`, so that is what I put in the workflow — and
CI failed 12 tests, all 500s from endpoints that guard on
`config.OPENAI_API_KEY`.

The reason: `load_dotenv()` with no argument calls `find_dotenv()`, which walks
up from **the calling file's directory**, not the process's cwd. `config.py`
sits at the repo root, so it finds the repo's `.env` no matter where pytest was
invoked. Changing directory proves nothing.

The correct way to test a clean environment locally is a **`git worktree`** —
`.env` is gitignored, so a fresh worktree genuinely lacks it. That reproduced
CI's 12 failures exactly, and confirmed in one run that the real requirement is
`JWT_SECRET` plus a dummy `OPENAI_API_KEY`. The general lesson: when verifying
"works without X", make X actually absent rather than arranging to look
elsewhere for it — and prefer a reproduction that can fail over an argument
that it should pass.

---

## 5 Aug 2026 — A test fixture that "isolated" the category fallback wasn't isolating anything (#163)

Adding a match reason per recommended segment needed a test proving that a
segment arriving on the _category_ rung of the match ladder says
"Matched on category: Gardening" rather than naming terms. The obvious fixture
— keyword `garden`, category `Gardening`, one segment mentioning "garden" and
one not — failed, insisting the second segment had matched on `garden` too.

It had. `_segment_haystack()` builds its token set from the segment's name,
description **and category**, and `_stem()` strips `ing`, so the _category_
`Gardening` stems to `garden` and is itself a keyword hit. Every row in that
category was a term match; the category fallback rung was never exercised.

The pre-existing test directly above it carried a comment claiming "only ONE
keyword hit" for the same fixture. Its assertions passed, so the wrong claim
had sat there unchallenged — a fixture can be wrong about _why_ it passes and
still pass, which is precisely what a new assertion on the mechanism exposes.

The fix was to choose a keyword sharing no stem with the category name
(`allotment` / `Gardening`). The general lesson: when a matcher searches
several fields at once, a test isolating one path has to check the value it
picked isn't reachable through the others. Print the intermediate — here, the
haystack — rather than reasoning about which field "should" have matched.

The same fact — that the category is searchable text — turned out to matter in
production, not only in the fixture. On a Saga brief, "Cruise goers" reported
`Matched on: cruise, holiday` where "holiday" had touched nothing but the shelf
label `Holidays`. The tempting fix was to drop category-only terms from the
line, but that would make the reason disagree with the ranking: the hit is real
and it _did_ score. So they are marked instead — `holiday (category)` — which
keeps the line faithful to the scoring while still showing how thin the hit is.
The general principle: when a displayed explanation and the mechanism it
explains disagree, weaken the _claim_, never the record.

A second thing this made visible: multi-word expansion terms match on _any_
token, so `gut health` matches anything mentioning "health". That behaviour
predates #163, but the new reason line surfaces it — a hearing-aids brief whose
every segment reads `Matched on: health` shows at a glance that nothing matched
"hearing", which is exactly the report the tester could only describe as a
mystery. Making the mechanism visible turns a silent looseness into a
reviewable one, which was the whole point of the ticket.

---

## 5 Aug 2026 — Restoring a form is easy; deciding when _not_ to is the design (#160)

Persisting the brief form across a reload took one small pure module. What took
the thinking was the ticket's fourth acceptance criterion — "nothing is retained
beyond what the user would expect" — because it is the one that decides whether
the feature feels like a safety net or like a form that won't let go.

Two states look identical in storage and mean opposite things. An **empty form**
is not "nothing to save"; it is a decision to clear, and if it is stored as a
value the next reload hands back the very input the user just deleted. It is
stored as _absence_ instead: `isEmptyDraft` makes `writeDraft` call
`removeItem`. A **submitted form** is the same shape as an unsubmitted one, but
its content now exists as a saved brief, so keeping the draft would resurrect
work that was already finished. The page snapshots the input it submitted and
clears the draft while the form still matches it — an edit afterwards differs
from the snapshot, so saving resumes on its own with no flag to reset.

The other judgement call was the store. localStorage would have satisfied "form
input survives a page refresh" more thoroughly and been wrong: a client brief is
free text a planner may have pasted out of an email, and leaving it on disk for
whoever opens the browser next is not what "my form came back" means. A draft
should outlive a reload, not the tab — that is sessionStorage. The same reasoning
demanded that `logout()` clear it, because a tab outlives a session even when
storage is scoped to it.

Two mechanical notes worth keeping. Firstly, reading and writing take the
storage as an argument rather than reaching for it, and the one function that
does touch `window` sits alone at the foot of the file; that is what made the
tests possible with a hand-rolled fake and no jsdom, and it turns a server
render into a `null` argument rather than a special case. (The first draft of
this entry, and of the module header, claimed the file "never touches
`window`" — while the file ended in `window.sessionStorage`. A review caught
it. Prose about purity is worth exactly as much as the line of code it is
sitting next to.) Secondly, the restore-on-mount effect must
set a `draftRestored` flag before the persist-on-change effect is allowed to
write — otherwise the persist effect fires first with the initial empty state and
overwrites the very draft it was about to restore. The safety net erasing the
thing it was there to catch is the failure mode to watch for whenever "load from
storage" and "save to storage" are two effects over the same state.

Finally, a test can be wrong about what it expects rather than about what it
checks. `readDraft` on a stored value whose every field was the wrong type was
asserted to return an empty draft; it returns null, because a draft with nothing
restorable in it _is_ nothing, and reporting it as a value would leave the caller
two cases that look identical on screen. The implementation was right and the
expectation was lazy — worth checking which one is wrong before "fixing" either.

A last one, found in review rather than in testing: the notice shown after an
interrupted run originally led with "press Generate Insights to run it again".
But a browser reload closes the connection without stopping the server, and
`/api/insights` saves the brief when generation finishes — so the run had most
likely _completed_, and the friendliest-sounding instruction was an invitation
to pay for a second GPT-4o generation of a brief the user already owned. The
notice now sends them to My Briefs first. When a feature is built entirely on
the client, it is easy to write recovery copy that describes the client's view
of events — the connection died, so the work died — and quietly contradicts
what the server actually did.

## 6 Aug 2026 — "Back logs me out" was Back showing the login page (#161)

Abel's report was that the browser Back button logs you out. It does not. The
session survives Back perfectly intact — `/api/me` answers 200 the whole way
through. What Back did was land the user on `/login`, which rendered its form to
anyone who asked, signed in or not. "Welcome back" and an empty email field is
what being logged out looks like, so that is what it was reported as, and the
next thing a user does is type their password again.

The cause was one word. Signing in ran `window.location.href = redirect`, which
**pushes**. The proxy's redirect to `/login?redirect=/app` had replaced the
`/app` entry, so history read `[…, /, /login]` and then gained `/app` on top:
the login form sat exactly one Back press behind the app. `location.replace`
consumes that entry instead, and Back reaches the screen the user was actually
on.

The same push/replace error turned out to be in four more places, and it took a
review to find the last two: the assistant page's auth bounce, `/app`'s 401
handler, `logout()`, and the password-reset form. All of them leave behind an
entry you can walk back into — a "you need to sign in" that bounces you out
again, a signed-out tab that restores the last person's brief from the
back/forward cache, a spent one-time reset token offering a password field that
can only fail. The first draft of this entry claimed "three other places" and
then listed two, which is its own small lesson: a count in prose is a claim, and
nothing checks it. The rule is now pinned by a test that reads those files and
fails on `router.push`, because the repo has no DOM harness that could catch it
any other way.

Two things were worth the trip through a real browser rather than reasoning from
the code.

The first was a false lead that would have wasted a day. In `next dev`, Back
into `/app` renders a **completely blank page** — no navbar, nothing — while
`/api/me` returns 200. It looks like a much worse bug than the reported one. It
is not a bug at all: the HMR websocket disqualifies the page from Chrome's
back/forward cache, so Back refetches the document, and `/app` returns `null`
until its auth check resolves. Against `next build && next start` the same
sequence restores from bfcache instantly and renders fine. **Reproduce
production bugs against a production build**; a dev server has different
navigation behaviour, and the difference here pointed at the wrong subsystem
entirely.

The second only appeared _after_ the fix. Back now reached the landing page as
intended — but showed "Login" and "Launch App" in the navbar, because that page
was restored from bfcache exactly as it had been frozen before sign-in. A
bfcache restore does not remount React, so the provider's mount effect never
re-runs and the auth state stays as stale as the pixels. `AuthProvider` now also
revalidates on `pageshow` when `event.persisted` — the one moment the browser
tells you a page has come back from the dead. Any state a provider fetches once
on mount has this hole in it.

Testing this needed two throwaway pieces of scaffolding, both worth remembering.
There is no DOM test harness in this repo, so the decisions went into
`lib/authNavigation.ts` as plain functions taking a `location` object as an
argument — the same shape `lib/briefDraft.ts` uses for storage — and the test
asserts `replace` was called and `assign` was not, which is the whole defect in
one assertion. And the "genuinely expired session" criterion was checked by
minting an expired JWT with the app's own secret and serving it from a scratch
HTTP server on another port: **cookies ignore ports**, so a cookie set from
`localhost:9999` is sent to the app on `localhost:3002`. That is a neat way to
plant an httpOnly cookie a page's own JavaScript is not allowed to write.

One thing was fixed in passing because the change landed on the exact line: the
`redirect` query parameter was fed straight to `window.location`, so
`/login?redirect=https://evil.example` sent the user off-site after a successful
sign-in. `safeReturnPath` now honours only same-origin absolute paths, rejecting
`//host` and `/\host`, which browsers read as another origin.

---

## 2026-08-06 — Overlapping deck text: the file was fine, the renderer wasn't (#162)

**What went wrong:** QA reported "some exported slides have text overlapping".
Nothing in the .pptx looked wrong, and every existing test passed — the tests
inspected text content, run formatting and file integrity, none of which the
defect touches.

**Why:** every text box in the template is `spAutoFit` — PowerPoint's "resize
shape to fit text". python-pptx writes the text and leaves the stored height
alone, so the shape only grows when **PowerPoint** lays the slide out on open.
A value longer than its placeholder is therefore written happily, reads back
correctly, and lands on the tile below it on screen. Anything that inspects the
file cannot see this. The only way to catch it is to _measure_: wrap the text
the way the renderer will, at the box's own width and font, and check where it
lands.

**The second half, which was the actual root cause:** the fix is not just
"shorten the text". Several boxes were drawn wider than the column they sit in
— `[INSIGHT_2_STAT]` was a 5.34" box starting at x=4.88" on a 10" slide, so it
hung 0.22" off the edge. PowerPoint wraps at the _box_, not at the column you
think the tile occupies, so a long line spills sideways into the neighbouring
tile no matter what. With the boxes as drawn, the only insight phrase
guaranteed to stay inside tile 1 was about four words. Content limits alone
could not fix a geometry bug; the boxes had to come in to their columns
(`scripts/narrow_overwide_tiles.py`, `cx` only — a no-op for anything that
already fitted, because the text is left-aligned and top-anchored).

**The generalisable bit:** when a layout constant is a _reading_ of an asset,
make a test re-derive it from that asset. `TILE_BUDGETS` would rot silently the
first time someone nudged a box in PowerPoint, so the test asserts each budget
uses the template's own typeface and size, equals its box's wrapping width
**exactly**, and clears every neighbour, the slide edge and the logo artwork
when full. A budget narrower than its box is a fiction, and the exact-equality
assertion is what says so.

**A quieter bug found on the way:** the prompt asked for insight phrases of up
to 12 words; the 26pt tile holds about six. Every deck had been shipping with
its insight lines cut off mid-sentence, and nobody had reported it because
truncation looked like terse copywriting. Worth separating the two jobs: the
fitter is the _guarantee_ (it cannot be allowed to fail), the prompt cap is
there so the guarantee rarely has to fire. They are now pinned to each other by
a test that spans both files.

**Measuring text without a renderer:** the real Barlow files are already in the
repo for font embedding, so `fontTools` gives exact advance widths — far better
than the "average glyph is half the point size" estimate used elsewhere, which
cannot tell `iiii` from `WWWW`. Line height comes from the font's own `hhea`
metrics. Default OOXML insets are 0.1" left/right and 0.05" top/bottom, and
they matter at these box sizes.

## 6 Aug 2026 — A missing feature reported as a disappearing one (#177)

**What went wrong:** "Open a brief from My Briefs and the Download Deck and
Draft Email buttons have gone." They had never been there. The export row was
nested inside the New Brief branch of `app/app/page.tsx`; the saved-brief detail
view is a sibling branch that ended before it. Viewing a historical brief
switches the active tab, unmounting the row — and because the freshly generated
result stays in memory, going back to New Brief brings the buttons back. An
absence that comes and goes reads as a regression, and looking for one wastes
the first half hour.

**The trap in the obvious fix:** moving the row is a five-minute job and would
have shipped a worse bug. The download handler closed over the New Brief form
state for topic, advertiser and KPI — not over the result it was exporting.
Rendered in the saved-brief view unchanged, it would have posted a saved
brief's content under whatever advertiser happened to be part-typed into the
form, and produced a confidently mislabelled client deck. Nothing would have
errored.

**How it was fixed:** the export row became one component taking the brief it
exports as a prop (`BriefExportActions`), over a `lib/briefExport.ts` whose
request body is a function of the brief alone. The error banner and the Draft
Email modal had to move with it — both were also inside the New Brief branch,
so a failed export from a saved brief would have set an error nobody could see.

**The generalisable bit:** when a component is only ever rendered in one place,
"which state does this close over?" is invisible — form state and result state
are both just in scope. The question only becomes answerable when the thing
takes its inputs as arguments. Extracting for a second caller is worth doing
carefully for that reason alone, not for the reuse.

**Testing without a DOM harness:** the frontend has no jsdom or Testing Library
(deliberately — see #161), so the coverage is the logic module tested in Node
with `fetch`/`saveBlob`/`track`/`now` injected, plus source-reading pins in the
spirit of `authNavigation.test.ts`: the page must no longer name the deck
endpoint, both branches must render the row, the row must read `brief.topic`
and hold no topic state of its own. A pin that reads source is not as good as
rendering the page, but it is much better than trusting a comment.
