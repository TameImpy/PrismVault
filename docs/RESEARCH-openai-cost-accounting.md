# Research: authoritative OpenAI cost accounting per request

**Ticket:** TameImpy/PrismVault#141
**Date:** 1 August 2026
**Branch:** `research/openai-cost-accounting` (throwaway — not for merge)
**Status:** Research only. No application code changed.

---

## The question

How do we derive a trustworthy per-request cost figure from the OpenAI API, so that a Prism
brief can be shown to leadership with a credible "this cost £X" attached, and so cost spikes
are diagnosable by model?

## Conventions used in this document

- **[DOCUMENTED]** — stated verbatim in an official OpenAI source, quoted or linked below.
- **[VERIFIED LOCALLY]** — I checked it against the installed SDK or this repo, and say how.
- **[INFERENCE]** — my reasoning, not an OpenAI statement. Treat as a working assumption.
- **[UNKNOWN]** — I could not establish it from primary sources. Listed again in
  [What I could not determine](#what-i-could-not-determine).

### A note on source URLs

`platform.openai.com/docs/*` now 301-redirects to `developers.openai.com/api/docs/*`, and
`openai.com/api/pricing/` returns HTTP 403 to non-browser clients. The canonical primary
sources for this document are therefore on `developers.openai.com`. Every documentation page
serves a raw-Markdown twin by appending `.md` to the URL, and there is an index at
[`/llms.txt`](https://developers.openai.com/llms.txt) — this matters for question 5 and is
called out there.

---

## TL;DR recommendation

Compute cost **client-side, per call, from `response.usage`, against a version-stamped price
table held in the repo**. Persist one row per LLM call with model, the raw token counts, the
price-table version, and the derived cost; roll up to a per-brief total. Reconcile the monthly
sum against the Costs API and treat any drift as a signal that the price table is stale.

There is no alternative. OpenAI publishes **no per-request cost**, and **no pricing API of any
kind** — the only OpenAI-authoritative dollar figure available programmatically is daily,
per-project, per-billing-line-item, and it _cannot be grouped by model_. Since model attribution
is a hard requirement for this ticket, the Costs API cannot be the primary source. It can only
be an audit check.

Full recommendation with the proposed schema and the biggest accuracy risk is in
[Recommendation](#recommendation) at the end.

---

## 1. What `response.usage` returns on Chat Completions

### Field names

**[VERIFIED LOCALLY]** — introspected against the installed SDK (`openai 2.29.0`) rather than
trusting docs prose:

```
CompletionUsage:        completion_tokens, prompt_tokens, total_tokens,
                        completion_tokens_details, prompt_tokens_details
PromptTokensDetails:    audio_tokens, cached_tokens
CompletionTokensDetails: accepted_prediction_tokens, audio_tokens,
                        reasoning_tokens, rejected_prediction_tokens
```

**[DOCUMENTED]** The same shape appears in the official streaming-events reference, which
documents `CompletionUsage` as having exactly the five properties above
([Chat Completions streaming events reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events.md)).
The OpenAPI spec's `required` list for `CompletionUsage` is exactly
`[prompt_tokens, completion_tokens, total_tokens]` — **both `*_details` objects are optional and
can be `None`**, as can every field inside them. Every read of a nested field needs
`getattr(...) or 0`.

Newer SDKs (2.45.0+) add `prompt_tokens_details.cache_write_tokens`. It is absent from the 2.29.0
install here, and it is only ever non-zero on GPT-5.6+ models, so it is irrelevant to gpt-4o
today — but a cost function should tolerate its presence rather than assume the field set is fixed.

Field docstrings, quoted verbatim from that reference:

| Field                                 | Docstring                                                           |
| ------------------------------------- | ------------------------------------------------------------------- |
| `prompt_tokens`                       | "Number of tokens in the prompt."                                   |
| `completion_tokens`                   | "Number of tokens in the generated completion."                     |
| `total_tokens`                        | "Total number of tokens used in the request (prompt + completion)." |
| `prompt_tokens_details.cached_tokens` | "Cached tokens present in the prompt."                              |

### Is there a cached-input breakdown? Yes.

`usage.prompt_tokens_details.cached_tokens` **[DOCUMENTED]** — this exact path is given in the
[prompt caching guide](https://developers.openai.com/api/docs/guides/prompt-caching.md) as the
way to observe a cache hit on Chat Completions. (The Responses API uses a different path,
`usage.input_tokens_details.cached_tokens` — not relevant here, this app is Chat Completions only.)

The guide states that the field is always present: _"All requests, including those with fewer
than 1,024 tokens, display a `cached_tokens` field... For requests under 1,024 tokens,
`cached_tokens` is zero."_

### The critical fact for the cost formula: `cached_tokens` is a SUBSET of `prompt_tokens`

This is the single easiest thing to get wrong, and getting it wrong double-counts the cached
portion.

**[DOCUMENTED]** The docstring — "Cached tokens present in the prompt" — says _present in_, not
_in addition to_. The worked example in the prompt caching guide settles it arithmetically:

```json
"usage": {
  "prompt_tokens": 2006,
  "completion_tokens": 300,
  "total_tokens": 2306,
  "prompt_tokens_details": { "cached_tokens": 1920, "cache_write_tokens": 0 }
}
```

`total_tokens` (2306) = `prompt_tokens` (2006) + `completion_tokens` (300). The 1,920 cached
tokens are _inside_ the 2,006, not added to them.

**Therefore the uncached input count is `prompt_tokens - cached_tokens`, and the correct formula is:**

```
cost = (prompt_tokens - cached_tokens) * input_rate
     + cached_tokens                   * cached_input_rate
     + completion_tokens               * output_rate
```

**The same non-additive rule applies on the output side.** **[DOCUMENTED]** the spec says of
`rejected_prediction_tokens`: _"like reasoning tokens, these tokens are still counted in the total
completion tokens for purposes of billing, output, and context window limits."_ So
`reasoning_tokens` and `rejected_prediction_tokens` are **inside** `completion_tokens` and must
never be added to it. Neither is relevant to gpt-4o or gpt-4o-mini (no reasoning tokens, no
predicted outputs in use here), but the rule matters if a reasoning model is ever adopted.

### Naming: Chat Completions vs Responses API

**[DOCUMENTED]** Chat Completions uses `prompt_tokens` / `completion_tokens`. The Responses API
uses `input_tokens` / `output_tokens` with `input_tokens_details` / `output_tokens_details`
(see [`response_usage.py`](https://github.com/openai/openai-python/blob/main/src/openai/types/responses/response_usage.py)).
Any code we write must not assume the Responses naming — and if this app ever migrates to the
Responses API, the cost function needs a second branch.

### When is `usage` absent?

- **Non-streaming, successful call:** `usage` is populated in practice, but **it is not
  contractually guaranteed** — **[DOCUMENTED]** the spec's `required` list for
  `CreateChatCompletionResponse` is `[choices, created, id, model, object]`, and `usage` is not in
  it. No documented condition describes it being omitted on a successful call, so treat it as
  "always present in practice, optional by contract" and null-guard it.
- **Streaming without `stream_options`:** absent — see section 2.
- **Request raises an exception** (network error, 429, 5xx, timeout): there is no response
  object at all, so there is no usage. **[INFERENCE]** — the practical consequence is that
  cost capture must live inside a `try` and must not break the call path.
- **`finish_reason: "length"` or content filtering:** `finish_reason` is a property of
  `choices[i]` and is orthogonal to `usage`; nothing in the spec conditions one on the other.
  **[INFERENCE]** a truncated non-streaming completion returns normal usage and is billed
  normally. Not stated explicitly in docs.
  One genuinely documented edge: the SDK's `LengthFinishReasonError.completion` docstring says
  _"this will **not** be a complete `ChatCompletion` object when streaming as `usage` will not be
  included"_ — i.e. a length-truncation raised by the `.parse()`/`.stream()` helpers fires before
  the usage chunk arrives.

### Are `usage` token counts authoritative for billing?

**[UNKNOWN].** OpenAI does not publish a statement that "billed tokens equals usage-reported
tokens". What _is_ documented is that the org-level Usage API reports the same token vocabulary
(`input_tokens`, `output_tokens`, `input_cached_tokens`, `input_uncached_tokens`) and that the
Costs API is derived from org usage. **[INFERENCE]** The two agree, and the standard industry
practice of pricing from `usage` is sound — but this is precisely why the reconciliation step
in the recommendation is not optional.

---

## 2. Streaming: `stream_options={"include_usage": True}`

This section is the most directly actionable, because **this app currently gets zero usage data
from its two streaming calls.**

### The requirement is real and the docs are unambiguous

**[DOCUMENTED]** From the [Chat Completions streaming events reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events.md),
the `usage` property on `chat_completion_chunk`, quoted verbatim:

> "An optional field that will only be present when you set `stream_options: {"include_usage": true}`
> in your request. When present, it contains a null value **except for the last chunk** which
> contains the token usage statistics for the entire request.
>
> **NOTE:** If the stream is interrupted or cancelled, you may not receive the final usage chunk
> which contains the total token usage for the request."

And the `stream_options.include_usage` request parameter itself, quoted verbatim from the spec
(mirrored in [`chat_completion_stream_options_param.py`](https://github.com/openai/openai-python/blob/main/src/openai/types/chat/chat_completion_stream_options_param.py)):

> "If set, an additional chunk will be streamed before the `data: [DONE]` message. The `usage`
> field on this chunk shows the token usage statistics for the entire request, and the `choices`
> field will **always be an empty array**.
>
> All other chunks will also include a `usage` field, but with a null value. **NOTE:** If the
> stream is interrupted, you may not receive the final usage chunk which contains the total token
> usage for the request."

The container is documented as _"Options for streaming response. Only set this when you set
`stream: true`."_ It also accepts an `include_obfuscation` boolean; both keys may be set together.

Those two quotes answer four of the sub-questions:

1. **Without the flag:** no usage on any chunk. It is absent entirely.
2. **With the flag:** every chunk carries `usage: null` _except the last_, which carries the
   full `CompletionUsage` for the whole request.
3. **Which chunk:** the final one. You must iterate to the end.
4. **Gotcha:** an interrupted or cancelled stream may never deliver it. Usage capture on a
   streamed call is therefore **best-effort, not guaranteed** — cost for an abandoned stream is
   unrecoverable from the API.

**A specific trap worth naming:** `finish_reason` arrives on the _second-to-last_ chunk. So the
common pattern of breaking out of the loop once `finish_reason` is set will discard the usage
chunk that follows it. If you need cost data, you must drain the iterator to the end.

### The `choices` array on the usage chunk is EMPTY — and this will crash the current code

**[DOCUMENTED]** From the same reference, the `choices` property docstring, verbatim:

> "A list of chat completion choices. Can contain more than one elements if `n` is greater than 1.
> **Can also be empty for the last chunk if you set `stream_options: {"include_usage": true}`.**"

**[VERIFIED LOCALLY]** `src/assistant.py` iterates both of its streams with an unguarded
`chunk.choices[0]`:

- `src/assistant.py:239` — `delta = chunk.choices[0].delta`
- `src/assistant.py:298` — `delta = chunk.choices[0].delta`

If someone adds `stream_options={"include_usage": True}` to the two `create()` calls at
`src/assistant.py:224` and `src/assistant.py:289` **without also guarding the loop body**, the
final chunk will have `choices == []` and both loops will raise `IndexError` — breaking the
assistant chat _after_ the user has already seen the full answer stream. This is the single
most likely way to ship a regression off the back of this ticket.

The guard is one line at the top of each loop:

```python
if not chunk.choices:
    if chunk.usage:
        record_usage(chunk.usage, model=config.CHAT_MODEL)
    continue
```

### SDK version floor — the current pin is too low

**[VERIFIED LOCALLY]** `requirements.txt` pins `openai>=1.10.0`. Using the GitHub API against
the SDK repo:

- `stream_options` was added in **openai-python v1.26.0** (2024-05-06), release note:
  _"feat(api): add usage metadata when streaming (#1395)"_.
- `cached_tokens` first appears in `src/openai/types/completion_usage.py` at tag **v1.51.0**
  (2024-10-01) — confirmed by fetching the file at v1.50.0 (absent) and v1.51.0 (present).

So `openai>=1.10.0` permits a resolved version in which `stream_options` does not exist and
`cached_tokens` cannot be read. The locally installed version is 2.29.0, so it works _here_ —
which is exactly the kind of drift that passes locally and breaks in a fresh deploy.
**The pin should be raised to `openai>=1.51.0` at minimum** as part of implementing this.

### Async client, helpers, tool calls, `n>1`

- **Async client:** identical — `AsyncOpenAI` uses the same generated `ChatCompletionChunk` type
  with the same `usage` field. `stream_options` is a request-body parameter, not a client-side
  feature.
- **The `client.chat.completions.stream()` helper** exists (sync and async) and is the safer
  ergonomic route: `stream.get_final_completion().usage` is populated because
  `get_final_completion()` internally drains to done. **But it does not set `include_usage` for
  you** — `stream_options` is passed straight through, so you must still supply it explicitly.
  This app does not currently use the helper; it iterates the raw stream.
- **Tool calls:** no documented interaction. This app's streaming calls do use tools
  (`SEARCH_SEGMENTS_TOOL`), and the tool-call path fires a _second_ streaming request
  (`src/assistant.py:289`), so an assistant turn that uses the tool produces **two** usage
  payloads that must both be captured and summed.
- **`n>1`:** the `choices` docstring notes multiple elements when `n>1`, but usage is documented
  as being "for the entire request", so it is a single total. This app does not set `n`.

---

## 3. Is there an OpenAI Usage / Costs API?

Yes — two of them, and neither solves the per-request problem.

### Endpoints

**[DOCUMENTED]** (official OpenAPI spec + Administration API reference). Base
`https://api.openai.com/v1`, all `GET`, all declaring `security: - AdminApiKeyAuth: []`.

- **Costs:** `GET /v1/organization/costs`
- **Usage:** `GET /v1/organization/usage/completions`, `/usage/embeddings`, plus nine more
  product-specific surfaces (moderations, images, audio, vector stores, etc.).

Note the asymmetry: costs sits at `/organization/costs`, _not_ under `/usage/`.

### Granularity — this is where it falls down

|                       | Usage API                                                                   | Costs API                                            |
| --------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------- |
| **Returns**           | token counts only, **no dollars**                                           | **real dollars** (`amount.value`, `amount.currency`) |
| **Min bucket**        | `1m` (also `1h`, `1d`)                                                      | **`1d` only**                                        |
| **`group_by`**        | `project_id`, `user_id`, `api_key_id`, **`model`**, `batch`, `service_tier` | `project_id`, `line_item`, `api_key_id`              |
| **Model attribution** | yes                                                                         | **no**                                               |

**[DOCUMENTED]** Costs `bucket_width`: _"Currently only `1d` is supported, default to `1d`."_
Costs `group_by` does **not** include `model`, and there is no `models[]` filter.

**This is the finding that determines the architecture.** The only API that returns money cannot
tell you which model spent it. `line_item` is a _billing category_ string (the official example
is `"Image models"`), not a model ID. Since model attribution is a stated hard requirement of
this ticket, **the Costs API cannot be the source of truth.**

Conversely the Usage API _does_ group by model but returns only token counts — so you would
still have to apply your own price table to it. It buys you nothing over reading `usage` inline,
and costs you an admin key.

### Can it be reconciled to an individual request?

**No.** **[DOCUMENTED]** by absence: there is no `request_id`-keyed cost or usage lookup anywhere
in the OpenAPI spec.

The only attribution dimensions the cost APIs honour are **project** and **API key**. So the only
way to split _OpenAI-authoritative dollars_ by feature is to run one project or one API key per
feature. Things that look like attribution levers but do **not** reach the cost APIs:

- `metadata` — filterable on stored completions, but not a `group_by` on usage or costs.
- `user` — deprecated, being replaced by `safety_identifier` / `prompt_cache_key`.
- `safety_identifier` — abuse detection only.
- `prompt_cache_key` — cache routing only.

**[INFERENCE]** The Usage API's `user_id` is the _organisation member_ who owns the key, not the
application's end user — so it cannot be used to attribute cost to a Prism user. Not stated
explicitly in docs; flagged.

Given that per-call-site attribution has already been ruled out as over-built for this ticket,
none of this changes the plan — but it does mean that if per-feature dollars are ever wanted from
OpenAI directly, the answer is _separate projects_, and that is a decision to take early because
it is a key-topology change.

### Admin key, latency, limits

- **Auth:** **[DOCUMENTED]** an Admin API key is required (`Authorization: Bearer $OPENAI_ADMIN_KEY`).
  Admin keys are created in the dashboard only. **[DOCUMENTED]** the
  [Admin APIs guide](https://developers.openai.com/api/docs/guides/admin-apis.md) states Python
  SDK admin support arrived in **`2.34.0`** — the version installed here is 2.29.0, so admin
  endpoints are not reachable via the SDK on the current install without an upgrade (raw HTTP
  would still work).
- **Scopes:** the strings `api.usage.read` / `api.costs.read` could **not** be verified. The RBAC
  guide describes a permission _category_ named "Usage" and has no "Costs" category. **[UNKNOWN]**
- **Latency before data appears:** **[UNKNOWN]** — genuinely undocumented for both APIs.
  **[INFERENCE]** costs settle materially slower than usage, given daily bucketing and billing
  line items. Must be measured empirically before anyone builds a dashboard that depends on it.
- **Pagination:** cursor-based, `has_more` + `next_page`. `limit` counts **buckets**, not rows —
  costs 1–180 (default 7); usage `1d` max 31, `1h` max 168, `1m` max 1440.
- **Rate limits on `/v1/organization/*`:** **[UNKNOWN]** — not mentioned in the rate limits guide.
- **Caveat:** **[DOCUMENTED]** if you omit `group_by`, dimension fields such as `project_id` and
  `model` come back `null`. Always send it.

---

## 4. Current list pricing

**Source:** [developers.openai.com/api/docs/pricing](https://developers.openai.com/api/docs/pricing)
(raw: [`pricing.md`](https://developers.openai.com/api/docs/pricing.md)). Independently fetched
twice, by two separate routes, with matching results.

**[DOCUMENTED]** The unit is stated verbatim on the page as **"Prices per 1M tokens."** — not per
1K. Getting this wrong is a 1000× error.

### Standard tier — the models this app uses

| Model                    | Input     | Cached input | Output     |
| ------------------------ | --------- | ------------ | ---------- |
| `gpt-4o`                 | **$2.50** | **$1.25**    | **$10.00** |
| `gpt-4o-mini`            | **$0.15** | **$0.075**   | **$0.60**  |
| `text-embedding-3-small` | **$0.02** | –            | –          |

- `gpt-4o` the alias resolves to snapshot **`gpt-4o-2024-08-06`**
  ([model page](https://developers.openai.com/api/docs/models/gpt-4o.md)). The alias is what this
  app sends, and the alias is what the table above prices.
- `gpt-4o-mini` has a single snapshot, `gpt-4o-mini-2024-07-18`.
- `text-embedding-3-small` has one rate, labelled "Cost", with no cached or output rate. It is
  only used by `ingest.py`, which runs offline and is not part of per-brief cost.
- **[DOCUMENTED]** The pricing page states verbatim: _"Responses API, Chat Completions API,
  Realtime API, Batch API, and Assistants API are not priced separately. Tokens are billed at the
  chosen model's input and output rates."_ So the price table can be keyed purely on
  `(model, service_tier)` — the API surface is not a pricing dimension.

### The cached-input discount for these models is 50%, not 90%

**This is the most consequential pricing finding.** $2.50 → $1.25 and $0.15 → $0.075 are both
exactly **50% off**. The widely-repeated "90% cache discount" figure applies to the GPT-5.x
family (e.g. $1.25 → $0.125), **not** to gpt-4o or gpt-4o-mini. Any ROI model for caching built
on the 90% number would overstate the saving by a factor of five.

### Tiers, and recent changes to flag

- **Batch API:** 50% discount, **[DOCUMENTED]** verbatim in the batch guide. gpt-4o $1.25/$5.00,
  gpt-4o-mini $0.075/$0.30. Not used by this app. No published batch rate for
  `text-embedding-3-small` **[UNKNOWN]** despite the model page listing `v1/batch` as supported.
- **Flex tier:** gpt-4o and gpt-4o-mini are **absent from the Flex table entirely**. No flex
  pricing for our models.
- **Fast mode (renamed from Priority):** **[DOCUMENTED]** verbatim — _"Priority processing was
  renamed Fast mode on July 30, 2026. You can use either `service_tier: "priority"` or
  `service_tier: "fast"` in your API requests."_ That rename is **two days old** at time of
  writing. Fast rates: gpt-4o $4.25/$2.125/$17.00; gpt-4o-mini $0.25/$0.125/$1.00. This app does
  not set `service_tier`, so standard rates apply — **but a price table must key on tier, or it
  will silently mis-price the day someone sets `service_tier` for latency.**
- **Regional processing** carries a 10% uplift, but only for _"models released on or after
  March 5, 2026"_ — gpt-4o and gpt-4o-mini predate that, so unaffected.

### Deprecation status

**[DOCUMENTED]** `gpt-4o` and `gpt-4o-mini` are **not** deprecated and **not** marked legacy —
both sit under "Flagship models → Our latest models". However, per the
[deprecations page](https://developers.openai.com/api/docs/deprecations.md), the single snapshot
**`gpt-4o-2024-05-13` shuts down on 23 October 2026** (substitute `gpt-5.6-sol`). That snapshot is
priced at 2× ($5.00/$15.00) and has no cached-input rate. This app sends the bare `gpt-4o` alias,
so it is not exposed — but a price table should carry the dated snapshots with their _own_ rates
rather than assuming all `gpt-4o*` strings cost the same, because they do not.

---

## 5. Stopping a hardcoded price table from silently drifting

### Is there a pricing API? No.

**[DOCUMENTED] by exhaustive absence.** `GET /v1/models` and `/v1/models/{model}` return exactly
four fields — `id`, `created`, `object`, `owned_by`
([`model.py`](https://github.com/openai/openai-python/blob/main/src/openai/types/model.py)).
No price, rate, or cost field. A grep of the entire official OpenAPI spec for
`pricing|price|billing` returns only prose in descriptions and links to the marketing page.
There is no endpoint, no schema, and no field anywhere that returns a price.

**A hardcoded table is therefore unavoidable.**

### The least-bad pattern

The failure mode to design against is not "the table is wrong" — it is "the table is wrong and
nobody notices for six months, so every number we showed leadership was wrong." So the design
goal is **loud failure**, not accuracy.

Four mechanisms, in order of value:

1. **Version and date-stamp the table, and persist the version on every cost row.**
   Give the table a `PRICE_TABLE_VERSION` and a `source_checked_on` date. Write that version into
   each persisted cost record. This makes historical costs _reproducible and correctable_: if the
   table turns out to have been wrong from March, you can find exactly which rows used it and
   recompute them. Without this, a pricing error is permanently baked into the history and there
   is no way to tell good rows from bad.

2. **Fail loudly on an unknown model — never silently price at zero.**
   **[VERIFIED LOCALLY]** `CHAT_MODEL` is environment-overridable (`config.py:22`,
   `.env.example:6`), so an ops change can put a model into production that the table has never
   seen. If the lookup misses, it must record the call with a null cost and an explicit
   `unpriced` marker, and log a warning — never default to `0.0`, which would quietly understate
   spend and look like a cost _saving_. Key the table on `(model, service_tier)`, not model alone.

3. **Reconcile against the Costs API monthly.**
   This is the only genuinely authoritative check available. Sum your computed costs for a
   calendar month and compare to `GET /v1/organization/costs` for the same window. A drift beyond
   a small tolerance means either the price table is stale or usage capture is dropping calls.
   Both are things you want to know. This is the payoff for capturing an admin key.

4. **Automated staleness check against the published price page.**
   Because every OpenAI docs page serves a raw-Markdown twin at `<url>.md`, the pricing page is
   machine-readable at
   [`https://developers.openai.com/api/docs/pricing.md`](https://developers.openai.com/api/docs/pricing.md),
   indexed by [`/llms.txt`](https://developers.openai.com/llms.txt), and the page's own header
   documents this convention. This is _not_ a JSON pricing API — there is none (tested:
   `/api/docs/pricing.json`, `/api/pricing.json`, `/_next/data/pricing.json`,
   `api.openai.com/v1/pricing` all 404) — but it is a stable, officially-sanctioned parseable
   source. A scheduled CI job can fetch it, extract the rows for our models, and open an issue
   if they differ from the committed table.

   **[INFERENCE]** Treat this as a _tripwire_, not a live feed. Never let it rewrite prices
   automatically: a docs-layout change or a bad parse would silently corrupt the cost history,
   which is worse than the drift it was meant to prevent. Alert a human; let the human commit
   the change.

---

## 6. Does prompt caching apply automatically, and would it materially change cost?

### It is automatic

**[DOCUMENTED]** verbatim from the
[prompt caching guide](https://developers.openai.com/api/docs/guides/prompt-caching.md):
_"Prompt Caching works automatically for eligible requests, with no code changes required. It is
enabled for all recent models, `gpt-4o` and newer."_

So caching is **already happening or already failing to happen** today — we just cannot see which,
because nothing captures `cached_tokens`. Instrumenting usage is therefore also the instrument
that tells us whether caching works at all.

### The rules that decide whether we get hits

- **Minimum prefix:** **[DOCUMENTED]** _"GPT-5.5 and earlier models: The minimum cacheable prefix
  length varies by model and can range from 1,024 to 2,048 tokens. Prompts just above 1,024
  tokens may not be cached consistently."_ gpt-4o is in this bucket — so plan for **~2,048 tokens**
  of stable prefix, not 1,024.
- **Exact prefix match, and order matters:** **[DOCUMENTED]** verbatim — _"Cache hits are only
  possible for exact prefix matches within a prompt. To realize caching benefits, place static
  content like instructions and examples at the beginning of your prompt, and put variable
  content, such as user-specific information, at the end."_
- **Lifetime:** **[DOCUMENTED]** _"cached prefixes generally remain active for 5 to 10 minutes of
  inactivity, up to a maximum of one hour."_ Extended 24h retention via `prompt_cache_retention`
  is limited to a listed set of GPT-5.x/4.1 models that **does not include gpt-4o**.
- **Cost of a cache write:** **[DOCUMENTED]** _"Cache writes have no additional fee on models
  before the GPT-5.6 family."_ So caching on gpt-4o is free upside.
- **`prompt_cache_key`:** **[DOCUMENTED]** exists and applies — _"it is combined with the prefix
  hash, allowing you to influence routing and improve cache hit rates."_ With an operational
  ceiling: _"Keep the total traffic across all prefixes for each key to approximately 15 requests
  per minute."_
- **Do not send GPT-5.6+ cache params to gpt-4o:** **[DOCUMENTED]** _"Older models also reject
  `prompt_cache_options` and `prompt_cache_breakpoint`."_ These would error.
- **Rate limits:** **[DOCUMENTED]** _"Do cached prompts contribute to TPM rate limits? Yes, as
  caching does not affect rate limits."_ Caching saves money, not headroom.
- **Streaming:** **[UNKNOWN]** — the caching guide says nothing either way about `stream: true`.
  Not a documented exclusion, but not a documented guarantee either.

### What this actually means for Prism — measured, not assumed

I measured the real prompts in this repo with `tiktoken` (`o200k_base`, the gpt-4o encoding):

| Prompt                                      | Tokens    | Position                                  |
| ------------------------------------------- | --------- | ----------------------------------------- |
| `src/assistant.py` `_build_system_prompt()` | **6,168** | prefix (system message)                   |
| `src/prompts.py` `SYSTEM_PROMPT` (brief)    | **1,904** | prefix (system message)                   |
| `src/formats.py` `load_format_data()` block | **5,253** | 8th of 10 placeholders in the user prompt |

Two very different verdicts:

**The assistant (`src/assistant.py`) — strong caching candidate.**
The 6,168-token system prompt is comfortably over the ~2,048 reliable threshold, is genuinely
static, and sits first. Multi-turn conversations resend it every turn, and turns within a session
land inside the 5–10 minute idle window. This should already be getting cache hits today. At the
50% cached rate on gpt-4o, a cached 6,168-token prefix costs $0.0077 instead of $0.0154 —
about **$0.0077 saved per assistant turn**, and an assistant turn that uses the segment-search
tool makes **two** calls, both carrying the prefix.

**The brief (`src/synthesiser.py`) — cannot cache the big block, by construction.**

> **Superseded in part, 6 Aug 2026 (#176):** `google_trends` has since been removed
> from `USER_PROMPT_TEMPLATE`. The measurement below is left as it was taken rather
> than restated, because it is the record of what was true on 1 August. The
> conclusion is unaffected: `advertiser_research` and `audience_segments` still
> precede the static format block and still change on every brief.

**[VERIFIED LOCALLY]** the placeholders in `USER_PROMPT_TEMPLATE` resolve in this order:

```
topic, advertiser, advertiser_kpi, client_brief, advertiser_research,
audience_segments, google_trends, format_recommendations, campaign_history,
historical_research
```

The 5,253-token static format block is **eighth**, sitting behind `advertiser_research`,
`audience_segments` and `google_trends` — all of which change on every single brief. Under exact
**prefix** matching, everything after the first variable byte is uncacheable. So that 5,253-token
block, despite being perfectly static, **can never be cached where it currently sits.**

The only cacheable prefix on the brief path is the 1,904-token `SYSTEM_PROMPT` — which falls in
the 1,024–2,048 "may not be cached consistently" band for gpt-4o. So brief caching today is
somewhere between zero and unreliable.

**[INFERENCE]** Moving the static format block to the front of the user prompt (or into the
system message, immediately after `SYSTEM_PROMPT`) would create a ~7,157-token stable prefix,
well clear of the threshold, and make it reliably cacheable — saving ~$0.0066 per brief on that
block alone and simultaneously fixing the unreliable-prefix problem for `SYSTEM_PROMPT`.
**This is a prompt-ordering change with cost consequences and possible output consequences, so it
is out of scope for this ticket** — but it is a concrete, measured follow-up, and it is only
visible _because_ we are about to start capturing `cached_tokens`. Worth filing separately.

The honest summary on materiality: per-call savings are fractions of a cent. At current volumes
caching is **not** a meaningful cost lever. Its real value here is diagnostic — `cached_tokens`
is the metric that proves whether the prompt structure is sane, and it becomes material only if
brief volume grows by an order of magnitude.

---

## Recommendation

**Compute cost in the app, per call, from `response.usage`, against a version-stamped price table
in the repo. Persist per call; roll up per brief. Reconcile monthly against the Costs API.**

### The formula

```python
# rates are USD per 1,000,000 tokens
uncached_input = usage.prompt_tokens - cached
cost = (uncached_input * rate.input
        + cached      * rate.cached_input
        + usage.completion_tokens * rate.output) / 1_000_000
```

where `cached = getattr(usage.prompt_tokens_details, "cached_tokens", 0) or 0`, defensively — the
details object can be absent on older SDKs and the value can be `None`.

### What to persist

One row per LLM call, in a new `llm_calls` table alongside the existing `briefs` table
(`api/database.py:78`), foreign-keyed to `briefs.id` so a brief total is a `SUM`:

```
id, brief_id (nullable), model, service_tier,
prompt_tokens, cached_tokens, completion_tokens,
cost_usd (nullable), price_table_version, unpriced (bool), created_at
```

Model is a column, not a derived field — that satisfies the "cost spikes must be diagnosable by
model" requirement without per-call-site attribution. `brief_id` is nullable so assistant turns
and email drafts, which are not part of a brief, still get recorded.

### How to capture it

**[VERIFIED LOCALLY]** there are **13 `client.chat.completions.create(...)` call sites across 11
modules**, and **12 separate `OpenAI(api_key=...)` constructions** — there is no shared client
wrapper today. Rather than editing 13 call sites, introduce one thin module that wraps
`create()`, records usage, and returns the response unchanged. That is a single seam, it is
testable in isolation, and it makes the two streaming call sites impossible to forget.

### The four things that must not be skipped

1. **Add `stream_options={"include_usage": True}`** to `src/assistant.py:224` and
   `src/assistant.py:289` — **and add the `if not chunk.choices: continue` guard** to the loops at
   lines 239 and 298 at the same time, in the same commit. Doing the first without the second
   ships an `IndexError`.
2. **Raise the SDK pin** from `openai>=1.10.0` to `openai>=1.51.0`.
3. **Never price an unknown model at zero.** Record it, flag it `unpriced`, warn.
4. **Stamp `price_table_version` on every row**, so a future pricing correction is recomputable.

### The biggest accuracy risk

**Silent price-table drift.** Every other risk here is loud — a missing usage payload is a null,
an unknown model is a flagged row, a crash is a crash. But a stale price table produces numbers
that look perfectly reasonable and are quietly wrong, in a system whose _primary_ purpose is
proving value to leadership. A 20% price change we fail to notice means every figure in the deck
is 20% off, with nothing anywhere to indicate it. There is no pricing API to protect us, so the
only defences are the version stamp (makes it _correctable_ after the fact), the monthly Costs
API reconciliation (makes it _detectable_), and the CI tripwire against `pricing.md` (makes it
detectable _sooner_). Of these, the reconciliation is the one that actually closes the loop
against OpenAI's own numbers, and it is the piece most likely to get dropped for being
unglamorous.

**Runner-up risk:** streamed assistant turns that the user abandons mid-answer. OpenAI documents
that the final usage chunk _"may not"_ arrive if a stream is interrupted, so that cost is
genuinely unrecoverable — it will show as a null-cost row and slightly understate true spend.
An estimated-token fallback for those rows is possible but should be marked as estimated, never
mixed silently into the authoritative figures.

---

## What I could not determine

1. **Whether OpenAI bills exactly the tokens reported in `usage`.** Never stated. This is the
   entire reason the reconciliation step exists.
2. **Data freshness / lag for the Usage and Costs APIs.** Undocumented for both. Must be measured
   empirically before anything depends on it.
3. **Whether prompt caching applies to streaming requests.** The caching guide is silent — neither
   a documented exclusion nor a documented guarantee. Once `cached_tokens` capture is live on the
   assistant's streaming calls, this answers itself empirically.
4. **Exact admin scope strings** (`api.usage.read`, `api.costs.read`). The RBAC guide names a
   "Usage" permission category and has no "Costs" category. Help Center pages return 403 to
   automated fetching.
5. **Rate limits on `/v1/organization/*`.** Not mentioned in the rate limits guide.
6. **Usage behaviour when `finish_reason: "length"` or content is filtered.** Not addressed.
7. **Batch API rate for `text-embedding-3-small`.** No published row, despite the model page
   listing batch as supported.
8. **Cache granularity/increment for gpt-4o.** The old "128-token increments" language is gone
   from the current docs; do not rely on it. (What _is_ documented is a 256-token _routing_ hash,
   which is a different mechanism.)
9. **Whether Usage API `user_id` is the org member or the request `user` param.** Inferred to be
   the org member; never stated.

---

## Primary sources

- [Pricing](https://developers.openai.com/api/docs/pricing) · [raw `.md`](https://developers.openai.com/api/docs/pricing.md)
- [Prompt caching guide](https://developers.openai.com/api/docs/guides/prompt-caching) · [raw `.md`](https://developers.openai.com/api/docs/guides/prompt-caching.md)
- [Chat Completions streaming events reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events.md) — source of the verbatim `usage` and `choices` docstrings
- [Admin APIs guide](https://developers.openai.com/api/docs/guides/admin-apis.md)
- [Administration API reference](https://developers.openai.com/api/reference/administration/overview)
- [Deprecations](https://developers.openai.com/api/docs/deprecations.md)
- [Batch guide](https://developers.openai.com/api/docs/guides/batch.md) · [Fast mode guide](https://developers.openai.com/api/docs/guides/fast-mode)
- [Model pages](https://developers.openai.com/api/docs/models/gpt-4o.md) — gpt-4o, gpt-4o-mini, text-embedding-3-small
- [Official OpenAPI spec](https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml)
- [openai-python](https://github.com/openai/openai-python) — [`completion_usage.py`](https://github.com/openai/openai-python/blob/main/src/openai/types/completion_usage.py), [`model.py`](https://github.com/openai/openai-python/blob/main/src/openai/types/model.py)
- [docs index `/llms.txt`](https://developers.openai.com/llms.txt)
