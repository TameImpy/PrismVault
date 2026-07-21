# Lessons Learned

A running log of tricky bugs, non-obvious gotchas, and decisions made on this
project. Each entry records what went wrong, why, and how it was fixed — so
future work doesn't have to rediscover it.

---

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
