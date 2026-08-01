# Research: lightest supported batch-write path into Databricks from a Railway-hosted app

**Issue:** [TameImpy/PrismVault#140](https://github.com/TameImpy/PrismVault/issues/140) (part of #138, Wayfinder Map: Usage & Cost Analytics)
**Date:** 1 August 2026
**Branch:** `research/databricks-batch-write` — throwaway, not for merge
**Status:** Research only. No implementation, no dependency added.

---

## The question

What is the lightest **supported** way for a Railway-hosted FastAPI/Python app to push rows into
Databricks on a schedule?

### Constraints taken as given (from #138 and #140)

| Constraint                                                                                        | Consequence for this research                                                   |
| ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| FastAPI on Railway; Python 3.11 in prod (`runtime.txt`), macOS system Python **3.9** locally      | Python version floors are a first-class selection criterion                     |
| Databricks is an **existing** instance owned by the eng/data-platform team; we are **not** admins | Every "the admin must do X" step is an organisational dependency with lead time |
| Only **outbound** network access from the container                                               | Anything needing inbound to Railway is dead                                     |
| Lakehouse Federation / JDBC-read **rejected**                                                     | Not revisited below                                                             |
| Synchronous write from the HTTP request path **rejected**                                         | All options assessed as scheduled batch only                                    |
| Volume: **hundreds to low thousands of rows/day**                                                 | "Correct at scale" is worth nothing here; "few moving parts" is worth a lot     |

---

## TL;DR recommendation

**Rank 1 — Statement Execution API (REST) over plain `httpx`, writing into a staging table, then `MERGE INTO` on a batch key.**
Zero new Python dependencies, no Python-version floor at all, pure outbound HTTPS, and the
smallest possible ask of the data-platform team (one service principal, four `GRANT`s, `CAN USE`
on a warehouse).

**Biggest risk of the top choice:** there is **no idempotency token** on the Statement Execution
API. If the app loses the HTTP response before reading the `statement_id`, it cannot determine
whether the statement committed, and a blind retry double-writes. This is designed around, not
eliminated — see [Idempotency](#idempotency-the-cross-cutting-problem).

Full ranking and rationale in [Recommendation](#recommendation).

---

## Option 1 — `databricks-sql-connector` (Python) → SQL warehouse

### Dependency weight — heaviest of the realistic options

Verified directly from the PyPI JSON API (`https://pypi.org/pypi/databricks-sql-connector/json`,
fetched 1 Aug 2026):

- Current version **4.4.0** (released 2026-07-22)
- **`requires_python = "<4.0,>=3.10"`**
- Mandatory direct deps: `thrift`, **`pandas`**, `lz4`, `requests`, `oauthlib`, `openpyxl`,
  `urllib3`, `python-dateutil`, `pyjwt`, `pybreaker`
- `pyarrow` is **not** installed by default — gated behind the `[pyarrow]` extra

**Pandas is mandatory, not optional.** That pulls numpy transitively. This repo already depends on
pandas (`requirements.txt`), so the marginal cost is smaller here than it would be elsewhere — but
`thrift`, `openpyxl`, `lz4`, `oauthlib`, `pybreaker` and `pyjwt` would all be new.

**Python 3.9 problem (documented fact):** the [CHANGELOG for 4.4.0](https://github.com/databricks/databricks-sql-python/blob/main/CHANGELOG.md)
states _"Raised the minimum supported Python version to 3.10, dropping the end-of-life 3.8/3.9."_
Per-version PyPI metadata confirms `4.3.0` and earlier declare `>=3.8.0`. So **the last version
installable on the local 3.9 dev environment is 4.3.0**, and we would be pinning to a
deliberately-superseded release to keep local dev working. Prod (3.11) is unaffected.

### Auth model

Documented at [Databricks SQL Connector for Python](https://docs.databricks.com/aws/en/dev-tools/python-sql-connector):

- **PAT** — `sql.connect(server_hostname=..., http_path=..., access_token=...)`
- **OAuth U2M** — browser-based; unusable headless
- **OAuth M2M (service principal)** — the correct choice; built by passing a
  `databricks.sdk.core.Config` + `oauth_service_principal` as a `credentials_provider`

Note the sting: **the documented OAuth M2M path for this connector routes through `databricks-sdk`**,
which itself declares `requires_python = ">=3.10"` (verified on PyPI, v0.123.0). Its CHANGELOG
records the drop at v0.103.0 (2026-04-20): _"Drop support for Python 3.8 and 3.9. The minimum
supported Python version is now 3.10."_ So the "lighter" 3.9-compatible pin has to be applied to
two packages, not one.

### Outbound-only? Yes

Connection is **Thrift over HTTP on port 443 with SSL** ([ODBC compute settings](https://docs.databricks.com/aws/en/integrations/odbc/compute)
documents `ThriftTransport=2`, same transport layer). The connector docs describe it as _"a
Thrift-based client with no dependencies on ODBC or JDBC"_ and require only `server_hostname` and
`http_path` of the form `/sql/1.0/warehouses/<warehouse-id>`. Outbound HTTPS is sufficient.

### Bulk insert — a documented trap

`Cursor.executemany()` **is not a batching optimisation**. From the connector source
([`client.py`](https://raw.githubusercontent.com/databricks/databricks-sql-python/main/src/databricks/sql/client.py)),
its own docstring:

> "This will issue N sequential request[s] to the database where N is the length of the provided
> sequence. No optimizations of the query (like batching) will be performed."

For a thousand rows that is a thousand round-trips to a SQL warehouse. The correct shape is one
`cursor.execute()` with a multi-row `INSERT ... VALUES (...),(...),...`.

Databricks' own guidance on that same connector docs page:

> "For large amounts of data, you should first upload the data to cloud storage and then execute
> the COPY INTO command."

### Idempotency — the connector actively worries about this

From [`auth/retry.py`](https://raw.githubusercontent.com/databricks/databricks-sql-python/main/src/databricks/sql/auth/retry.py)
(`DatabricksRetryPolicy`, extending `urllib3.Retry`). The connector auto-retries HTTP failures, but
classifies commands and **deliberately narrows retries for `ExecuteStatement`**:

> `"ExecuteStatement command can only be retried for codes 429 and 503"`

and, on the `respect_server_retry_after_header` option:

> _"only retry when the server explicitly signals it's safe via a Retry-After header, preventing
> duplicate side effects for non-idempotent operations."_

**Inference (not a doc statement):** the library treats a plain INSERT as non-idempotent by design
and narrows — but does not eliminate — double-write risk. A 429/503 retry on an INSERT that
committed server-side but whose response was lost can still duplicate. Application-level
idempotency is required regardless.

### Bonus capability: `PUT INTO` staging

The connector (uniquely among these options) can upload a local file straight into a Unity Catalog
volume. Set `staging_allowed_local_path` on `connect()`, then:

```sql
PUT '/tmp/my-data.csv' INTO '/Volumes/main/default/my-volume/my-data.csv' OVERWRITE
```

Documented at [PUT INTO](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-connector-put-into)
and [REMOVE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-connector-remove).
These statements are _only_ available via a driver/connector, not from the SQL UI.

### Operational burden

Moderate. A persistent-ish connection object, a heavier dependency tree, a version pin fight
between local 3.9 and current releases, and a documented `executemany` footgun.

---

## Option 2 — Statement Execution API (REST)

### What it is

`POST https://<host>/api/2.0/sql/statements/` — documented at
[Statement Execution API tutorial](https://docs.databricks.com/aws/en/dev-tools/sql-execution-tutorial)
and the [API reference](https://docs.databricks.com/api/workspace/statementexecution).

Companion endpoints: `GET /api/2.0/sql/statements/{statement_id}` (status),
`GET .../result/chunks/{chunk_index}`, `POST .../cancel`.

Request fields: `statement`, `warehouse_id`, `catalog`, `schema`, `parameters`, `disposition`,
`format`, `byte_limit`, `row_limit`, `wait_timeout`, `on_wait_timeout`.

### Documented limits (verified verbatim)

| Limit                            | Value                                       | Source                                                                                                    |
| -------------------------------- | ------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Max query text size              | **16 MiB**                                  | _"The maximum query text size is 16 MiB."_                                                                |
| `disposition=INLINE` result cap  | **25 MiB**                                  | _"Statements with `disposition=INLINE` are limited to 25 MiB and will fail when this limit is exceeded."_ |
| `disposition=EXTERNAL_LINKS` cap | **100 GiB**                                 | _"...limited to 100 GiB. Result sets larger than this limit will be truncated."_                          |
| `wait_timeout`                   | `0s`, or **5–50s** inclusive; default `10s` | _"When set between 5 and 50 seconds, the call will behave synchronously up to this timeout..."_           |
| Result availability              | **1 hour** after success                    | _"The results are only available for one hour after success; polling does not extend this."_              |

(Quotes from the SDK-generated reference at
[databricks-sdk-py.readthedocs.io — statement_execution](https://databricks-sdk-py.readthedocs.io/en/stable/workspace/sql/statement_execution.html),
which is generated from the same OpenAPI spec as the REST reference.)

`wait_timeout=0s` → fully async, returns `statement_id` immediately.
`on_wait_timeout` → `CONTINUE` (default, statement keeps running) or `CANCEL`.

**The 16 MiB statement-text limit is the practical bound on a multi-row INSERT.** There is no
documented row-count ceiling. A few thousand narrow rows is nowhere near 16 MiB. _(Inference: the
row ceiling is derived from the text limit, not stated as a row count anywhere.)_

> ⚠️ A "16 MB" figure also circulates in search results referring to **Model Serving payloads**.
> That is a different limit. Don't conflate them.

### Parameterised statements — documented and recommended

Named parameters use a mandatory `:name` prefix:

```json
{
  "statement": "INSERT INTO t (a, b) VALUES (:a, :b)",
  "parameters": [
    { "name": "a", "value": "x" },
    { "name": "b", "value": "2026-01-01", "type": "DATE" }
  ]
}
```

Positional `?` markers are also supported (DBR 13.3+), but **named and positional cannot be mixed
in one statement**. Type defaults to `STRING` if omitted. Databricks _"strongly recommends"_
parameters to prevent SQL injection.
Source: [Parameter markers](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-parameter-marker).

No documented limit on parameter count was found.

### Dependency weight — zero

The tutorial's own examples are `curl`. This is REST-over-HTTPS with a bearer token and JSON
bodies. **This repo already depends on `httpx>=0.28.0` and `requests>=2.31.0`** — no new package,
no Python-version floor, nothing to pin for 3.9.

If you _wanted_ the SDK instead: `databricks-sdk` 0.123.0 declares `requires_python = ">=3.10"`
(verified on PyPI) with deps `requests`, `google-auth`, `protobuf`, `urllib3`. **It will not
install on the local 3.9 environment.** Using raw HTTP sidesteps this entirely.

### Auth

Either a **PAT belonging to a service principal** (the tutorial explicitly notes a PAT _"that maps
to a user who has the entitlement to use Databricks SQL"_ and _"CAN USE access for the specific SQL
warehouse"_), or **OAuth M2M** — see [Auth and grants](#auth-and-grants-common-to-all-options).

### Outbound-only? Yes

Standard client → HTTPS 443. The only caveat is workspace-side: see
[IP access lists](#the-risk-nobody-mentions-workspace-ip-access-lists).

### Idempotency — the weak point

**There is no idempotency token.** `statement_id` is server-generated per POST; there is no
client-supplied key and no documented replay-safe retry.

Databricks has published first-party guidance for exactly the "did it commit?" scenario —
[KB: Query timeout due to inactivity](https://kb.databricks.com/dbsql/query-timeout-due-to-inactivity-error-when-using-the-sql-execution-api):

> "If you close the POST API call's connection without obtaining a status (succeeded or failed),
> the query remains active and is in a waiting state. If no further calls are made against the
> query, the query fails with the timeout error."

Recommended handling: capture the `statement_id` from the pending POST response and poll
`GET /api/2.0/sql/statements/{statement_id}` until a terminal state. The SDK docs add:
_"Cancelation might silently fail... Polling for status until a terminal state is reached is
reliable."_

Statement lifecycle states: `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELED`, `CLOSED`.

**Inference:** the recoverable failure mode is "we have a `statement_id` but haven't confirmed a
terminal state" — poll it. The _unrecoverable_ one is "the connection died before we read the
response body", where the `statement_id` is lost and you cannot tell whether the write landed. The
mitigation is application-level, not protocol-level: see
[Idempotency](#idempotency-the-cross-cutting-problem).

### Operational burden

Lowest. A cron entrypoint, an `httpx.post`, a poll loop, and a token refresh.

---

## Option 3 — stage a file, then `COPY INTO`

### `COPY INTO` idempotency — the strongest guarantee available

From the [COPY INTO SQL reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-copy-into):

> "Loads data from a file location into a Delta table. This is a retryable and idempotent
> operation. Files in the source location that have already been loaded are skipped."
> "This is true even if the files have been modified since they were loaded."

And the `force` copy option:

> "`force`: boolean, default `false`. If set to `true`, idempotency is disabled and files are
> loaded regardless of whether they've been loaded before."

The [Load data with COPY INTO](https://docs.databricks.com/aws/en/ingestion/copy-into/) overview
lists as a capability: _"Exactly-once (idempotent) file processing by default."_

**This is the only option here with a documented exactly-once story that does not require us to
build one.** The idempotency key is the file identity — write one file per batch with a
deterministic name and re-running `COPY INTO` is a no-op.

### Where the file lives — two sub-paths

**(a) Unity Catalog volume + Files API — the only outbound-only-friendly variant.**

An external app can `PUT` a file into a UC volume over plain HTTPS:

```
curl --request PUT \
  "https://${DATABRICKS_HOST}/api/2.0/fs/files/Volumes/main/default/my-volume/data.csv?overwrite=true" \
  --header "Authorization: Bearer ${TOKEN}" \
  --data-binary @data.csv
```

Documented at [Upload files to a Unity Catalog volume](https://docs.databricks.com/aws/en/ingestion/file-upload/upload-to-volume)
and the [Files API reference](https://docs.databricks.com/api/workspace/files/upload). The body is
raw bytes (_"an octet stream; do not encode or otherwise modify the bytes before sending"_).

`COPY INTO` sources directly from the volume path — documented at
[Load data using COPY INTO with Unity Catalog volumes or external locations](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/copy-into/unity-catalog):

```sql
COPY INTO landing_table
FROM '/Volumes/quickstart_catalog/quickstart_schema/quickstart_volume/raw_data'
FILEFORMAT = PARQUET;
```

Path form: `/Volumes/<catalog>/<schema>/<volume>/<path>/<file_name>`.

Files API upload cap is documented at **5 GiB** — irrelevant at our volume. _(Confidence note: the
API reference page is JS-rendered and did not fetch cleanly; the 5 GiB figure was corroborated
across two docs.databricks.com search results rather than a direct HTML quote.)_

**(b) Our own S3/ADLS/GCS bucket + UC external location + storage credential.**

Supported (`COPY INTO` accepts a registered external location, a named storage credential, or
inline temporary credentials), but it means **standing up a cloud bucket we don't currently have**
and asking the data-platform team for `CREATE EXTERNAL LOCATION` / `CREATE STORAGE CREDENTIAL`
work. Per [Manage external locations](https://docs.databricks.com/aws/en/connect/unity-catalog/cloud-storage/manage-external-locations):

> "The `CREATE EXTERNAL LOCATION` privilege on both the metastore and the storage credential
> referenced in the external location or the `MANAGE` privilege on the external location. Metastore
> admins have `CREATE EXTERNAL LOCATION` on the metastore by default."

That is a metastore-admin-level ask. **Sub-path (b) reintroduces exactly the kind of slow
organisational dependency that got Lakehouse Federation rejected**, and adds a second cloud account
to own. Not recommended.

### Grants needed (volume variant)

- To stage: `USE CATALOG` + `USE SCHEMA` + `READ VOLUME` + `WRITE VOLUME`
- To load: `USE CATALOG` + `USE SCHEMA` + `READ VOLUME` + `MODIFY` (+ `SELECT`) on the target table

From [Privileges for Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes/privileges):
creating, deleting or updating files requires **both** `READ VOLUME` and `WRITE VOLUME`.

### Runs on a SQL warehouse?

The reference page's "Applies to" scope is **"Databricks SQL and Databricks Runtime"**, and there
is a [tutorial running COPY INTO against a SQL warehouse](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/copy-into/tutorial-dbsql).
_(Inference: no doc was found enumerating serverless vs pro vs classic support specifically for
`COPY INTO`; the "Databricks SQL" scope tag is the basis for saying yes.)_

### Is it overkill at our scale? No — this is squarely the documented sweet spot

From [Ingest data from cloud object storage](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage):

> "If you're going to ingest files in the order of thousands over time, you can use `COPY INTO`. If
> you are expecting files in the order of millions or more over time, use Auto Loader."
> "Auto Loader requires fewer total operations to discover files compared to `COPY INTO`... less
> expensive and more efficient at scale."

One file per daily batch = ~365 files/year. Several years in we are at low thousands — inside the
documented `COPY INTO` band, nowhere near the Auto Loader threshold.

**No documented hard limit** was found on how many files `COPY INTO`'s skip-list can track. The
"thousands vs millions" guidance is Databricks' own scaling boundary and is framed as a
discovery-cost efficiency issue, not a ceiling. Community claims that the tracking state lives in
the Delta transaction log could not be verified against primary docs — **treat as unverified**.

### Operational burden

Highest of the three realistic options: two moving parts (upload, then load), a file-naming
convention that _is_ the idempotency key, and volume housekeeping. Buys the best correctness story.

---

## Option 4 — Databricks Connect

**Verdict: not relevant to this use case. Do not pursue.**

[Databricks Connect](https://docs.databricks.com/aws/en/dev-tools/databricks-connect/) is framed
throughout its documentation around IDE work — _"connect popular IDEs such as Visual Studio Code,
PyCharm, IntelliJ IDEA, notebook servers, and other custom applications to Databricks clusters"_
(PyPI), _"Interactively develop and debug from any IDE"_ (overview). It is a Spark Connect client
(gRPC over HTTP/2 + Arrow).

Disqualifying requirements, all from
[Databricks Connect usage requirements](https://docs.databricks.com/aws/en/dev-tools/databricks-connect/requirements):

> "The Databricks Runtime version of your compute must be greater than or equal to the Databricks
> Connect package version."

> "If you are using user-defined functions (UDFs), the local minor version of Python matches the
> minor version of Python of the Databricks Runtime version of the cluster or serverless compute."

Plus: Unity Catalog must be enabled; cluster access mode must be Assigned or Shared; and
[installation](https://docs.databricks.com/aws/en/dev-tools/databricks-connect/python/install)
requires uninstalling PySpark first because _"the `databricks-connect` package conflicts with
PySpark."_ The current release (19.0.0, 31 Jul 2026) targets **Python 3.12 only** and ships under a
_"Databricks Proprietary License."_

**Inference:** version lock-step between our app's Python and a runtime the data-platform team
controls and upgrades on their own schedule is precisely the coupling we are trying to avoid. Our
prod is 3.11 and local is 3.9; neither matches 3.12. A Spark session client to insert a thousand
rows a day is the wrong instrument by an order of magnitude.

_Not found in docs: any explicit statement that Databricks Connect is unsuitable for production
services, or that it is outbound-only. Both are inferences — the first from framing, the second
from the connection-string direction (`sc://<workspace>:443/`)._

---

## Option 5 — Zerobus Ingest (not in the original ticket, but worth knowing about)

A newer first-party option the ticket predates: a **push-based ingestion API that writes directly
into Unity Catalog Delta tables**, no message bus, no warehouse.
[Overview](https://docs.databricks.com/aws/en/ingestion/zerobus-overview) ·
[Usage](https://docs.databricks.com/aws/en/ingestion/zerobus-ingest) ·
[Limitations](https://docs.databricks.com/aws/en/ingestion/zerobus-limits)

- **Python SDK:** `pip install databricks-zerobus-ingest-sdk`, documented as **Python 3.9+** — the
  only Databricks package here that still supports our local 3.9
- **Auth:** OAuth 2.0 M2M, client ID + secret, `all-apis` scope
- **Grants:** exactly three statements, documented verbatim:
  ```sql
  GRANT USE CATALOG ON CATALOG <catalog> TO `<UUID>`;
  GRANT USE SCHEMA ON SCHEMA <catalog.schema> TO `<UUID>`;
  GRANT MODIFY, SELECT ON TABLE <catalog.schema.table_name> TO `<UUID>`;
  ```
- **Endpoint:** `<workspace-id>.zerobus.<region>.cloud.databricks.com`; gRPC (production) and REST
- **Latency:** durability ack P50 ≤ 150 ms; materialisation to Delta P50 ≤ 5 s

### Why it is nonetheless the wrong fit here

- **Delivery semantics are documented as "At-least-once guarantees."** We would still have to build
  dedup — with none of `COPY INTO`'s file-level exactly-once help.
- **"The connector supports writing only to managed Delta tables."** We don't control the target
  table's type.
- **"Both the workspace and the target table need to be in one of the available regions, and both
  in the same region"** — limited regional availability we cannot verify without workspace access.
- **"Zerobus Ingest will never auto-evolve your target table."**
- It is engineered for streaming throughput (100 MB/s per stream, 10 GB/s per table). A Databricks
  blog reports a workload moving from ~689 DBU/GB on the SQL Statement API path to ~0.29 DBU/GB on
  Zerobus — a real argument at GB scale, and irrelevant at ours. Billed against the **Jobs
  Serverless** SKU.
- Adds a proprietary SDK and a second network endpoint for a batch job that runs once a day.

**Worth a sentence in the spec so the data-platform team knows we considered it**, but a streaming
ingest API for a nightly export of a few hundred rows is overkill.

---

## Auth and grants (common to all options)

### OAuth M2M is the right model

From [Authorize service principal access to Databricks with OAuth](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m):

- Token endpoint (workspace-level): `https://<databricks-instance>/oidc/v1/token`
- Request: `POST` with basic auth `client_id:client_secret`, body
  `grant_type=client_credentials&scope=all-apis`
- Response: `{"access_token": "...", "token_type": "Bearer", "expires_in": 3600}` — **1 hour**
- Environment variables read by Databricks tooling: `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`,
  `DATABRICKS_CLIENT_SECRET`
- **OAuth secret max lifetime: 730 days** (two years), shown once at creation; up to 5 secrets per
  service principal. An expired secret produces 401s.

A daily cron job fetches a fresh token each run — no refresh-token machinery needed.

### What the data-platform team must actually do

Confirmed against [Service principals](https://docs.databricks.com/aws/en/admin/users-groups/service-principals),
the [Unity Catalog privileges reference](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control/privileges-reference),
and [Access control lists](https://docs.databricks.com/aws/en/security/auth/access-control/):

1. **Create a service principal** — account admin or workspace admin only. **A non-admin cannot do
   this.** (Non-admins can at most be granted the "Service Principal User" role on an existing SP.)
2. **Generate an OAuth secret** on its Secrets tab — also admin-only.
3. **Grant `CAN USE` on a SQL warehouse.** `CAN USE` covers "Run queries", "Start the warehouse",
   "View warehouse details". Databricks' own guidance: _"Grant minimal permissions... unless your
   app specifically needs to perform administrative tasks on the warehouse."_
4. **Grant Unity Catalog privileges.** The privileges reference is explicit that `MODIFY` alone is
   not enough — under `MODIFY`: _"The user must also have `SELECT` on the table, `USE SCHEMA` on
   the parent schema, and `USE CATALOG` on the parent catalog."_

   ```sql
   GRANT USE CATALOG ON CATALOG <catalog>          TO `<sp-application-id>`;
   GRANT USE SCHEMA  ON SCHEMA  <catalog>.<schema> TO `<sp-application-id>`;
   GRANT SELECT, MODIFY ON TABLE <catalog>.<schema>.<table> TO `<sp-application-id>`;
   ```

   There is **no separate INSERT privilege in Unity Catalog** — INSERT and MERGE both fall under
   `MODIFY`.

### Scoping the blast radius to one schema

Unity Catalog supports transferring object ownership: _"You can transfer object ownership if you
are the current owner, a metastore admin, the owner of the container (the catalog for a schema, the
schema for a table), or a user with the `MANAGE` privilege on the object"_
([Manage privileges](https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/)).

**Inference (composed from documented primitives, not a single named doc recipe):** the cleanest
ask is _"create a dedicated schema, make our service principal its owner, grant `CAN USE` on a
warehouse."_ That gives us full control inside one blast radius and requires no further grants when
we add tables — likely an easier conversation than table-by-table `MODIFY` grants on a schema the
platform team owns.

Documented caveat: `EXTERNAL USE SCHEMA` is excluded from `ALL PRIVILEGES` and is **not** granted
to schema owners by default. It only matters for external-table/credential-vending scenarios, not
managed-table INSERT/MERGE — so it shouldn't bite us.

---

## The risk nobody mentions: workspace IP access lists

Every option above assumes we can reach the workspace from Railway. That may not be true, and it is
not our decision.

From [Configure IP access lists for workspaces](https://docs.databricks.com/aws/en/security/network/front-end/ip-access-list-workspace):

> "Workspace IP access lists cover web application and REST API access to the workspace, including
> the Jobs API, the SQL Statement Execution API, Unity Catalog, the SDK, and the CLI."

And on evaluation order ([Manage IP access lists](https://docs.databricks.com/aws/en/security/network/front-end/ip-access-list)):

> "If there is at least one allow list, the connection is allowed only if the IP address matches an
> allow list."

[Context-based ingress control](https://docs.databricks.com/aws/en/security/network/front-end/context-based-ingress)
extends comparable controls to SQL endpoints (JDBC/ODBC) too — so this affects **Options 1, 2 and
3 alike**. IP access lists require the **Enterprise pricing tier**.

**Railway side:** [Static Outbound IPs](https://docs.railway.com/networking/static-outbound-ips) are
a **Pro plan** feature. A service gets **three** IPv4 addresses with outbound traffic load-balanced
across them. Critically: _"There is no guarantee that the IPv4 addresses assigned to your service
are dedicated. They may be shared with other customers"_, and they change if the service moves
region.

**Inference — flag this early in the spec:** if the workspace has an IP allowlist, we need Railway
Pro static IPs _and_ the data-platform team must allowlist three addresses that Railway does not
guarantee are exclusively ours. A security-conscious platform team may reject allowlisting shared
IPs. **This should be the first question asked of them**, ahead of any option choice — it can
invalidate the whole approach independently of which write path we pick.

---

## Idempotency: the cross-cutting problem

Ranked by how much the platform does for us:

| Mechanism                            | Applies to              | Strength                                                 |
| ------------------------------------ | ----------------------- | -------------------------------------------------------- |
| `COPY INTO` file-skip                | Option 3                | **Documented exactly-once** by file identity, default-on |
| Zerobus                              | Option 5                | Documented **at-least-once** — dedup still ours          |
| `MERGE INTO` on a batch/business key | Options 1, 2            | Ours to build, but robust                                |
| Connector retry policy               | Option 1                | Narrows risk; does not remove it                         |
| `txnAppId` / `txnVersion`            | **Not available to us** | See below                                                |

### `txnAppId`/`txnVersion` does not apply

Delta's idempotent-write mechanism is documented at
[Delta Lake table streaming reads and writes](https://docs.databricks.com/aws/en/structured-streaming/delta-lake):

> "Delta Lake tables support the following `DataFrameWriter` options to make writes to multiple
> tables within `foreachBatch` idempotent:
>
> - `txnAppId`: A unique string that you can pass on each DataFrame write.
> - `txnVersion`: A monotonically increasing number that acts as transaction version."

This is scoped to **`DataFrameWriter` inside `foreachBatch`** — a Spark/DataFrame API feature. The
docs make no mention of a plain SQL `INSERT` equivalent. **A FastAPI service writing over
SQL/REST cannot reach it.** (Documented scope limitation, not inference.)

### `MERGE INTO` — the pattern that actually works for Options 1 and 2

[MERGE INTO reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-merge-into),
quoted:

> "`MERGE` operations fail with a [DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE] error if
> more than one row in the source table matches the same row in the target table based on the
> conditions specified in the `ON` and `WHEN MATCHED` clauses."

The docs' recommended fix is to pre-deduplicate the source — _"retain only the latest change for
each key before applying that change into the target Delta table."_

Note this fails **loudly** rather than corrupting data — a useful property.

Also relevant: Unity Catalog `PRIMARY KEY` constraints are **informational and NOT ENFORCED**. They
inform the optimiser; they will not stop a duplicate. _(High confidence but not re-fetched verbatim
in this pass — verify before relying on it.)_

### Recommended shape for Option 2

1. Give every exported row a **deterministic natural key** — e.g. `(source_table, row_id)` or a
   hash of the immutable columns. Not a UUID generated at export time.
2. Dedupe the batch **client-side** before sending (MERGE will hard-fail otherwise).
3. `INSERT` the batch into a **staging table**, then `MERGE INTO` the target on that key in a
   second statement. Two statements, both individually ACID; a replayed batch updates rather than
   duplicates.
4. Alternatively, if the export is strictly append-only and the source has a monotonic cursor
   (an autoincrement id or `created_at`), record the high-water mark **in the app's own Postgres**
   after a confirmed `SUCCEEDED` and select `WHERE id > watermark` next run. Simplest correct
   design; a lost response causes at most a replayed batch, which the MERGE absorbs.
5. Always read the POST response body before giving up, so `statement_id` is captured and the
   documented poll-to-terminal-state recovery is available.

---

## Recommendation

### Ranking for _this_ use case

**1. Statement Execution API over `httpx`, staging table + `MERGE INTO`.**
Zero new dependencies (`httpx` is already in `requirements.txt`). **No Python-version floor at all**
— sidesteps the 3.9-vs-3.10 problem that afflicts `databricks-sql-connector` (≥3.10 since 4.4.0)
and `databricks-sdk` (≥3.10 since 0.103.0). Pure outbound HTTPS. Smallest organisational ask: one
service principal, one `CAN USE`, four `GRANT`s. Debuggable with `curl`. Testable against a fake
HTTP server with no Databricks-specific test doubles. At a few hundred to a few thousand narrow
rows/day we are orders of magnitude below the documented 16 MiB statement-text limit.

**2. `COPY INTO` from a Unity Catalog volume via the Files API.**
The only option with a documented exactly-once guarantee we don't have to build, and Databricks'
own "thousands of files" guidance puts our volume squarely in its band. Loses to #1 only on moving
parts — two operations, a file-naming convention that _is_ the correctness mechanism, and volume
housekeeping. **Promote this to #1 if the eventual row shape turns out to be wide/messy, if volume
grows beyond a few thousand rows per run, or if the team wants the ingest audit trail a landing
volume gives.** Note it needs `READ VOLUME` + `WRITE VOLUME` on top of the table grants.

**3. `databricks-sql-connector`.**
Works, and is the documented path if we ever want `PUT INTO` staging. But it is the heaviest
dependency (mandatory pandas, plus thrift/openpyxl/lz4/oauthlib/pybreaker/pyjwt), forces a pin to
the superseded 4.3.0 for local 3.9 dev, carries the `executemany` footgun, and buys nothing over
#1 for issuing SQL against a warehouse.

**4. Zerobus Ingest.**
Genuinely good technology, wrong shape. At-least-once delivery, managed-tables-only, regional
constraints, proprietary SDK, engineered for GB/s. Overkill.

**5. Databricks Connect.** Disqualified — Spark runtime version lock-step.

**Not ranked: staging to our own S3/ADLS/GCS.** Reintroduces the metastore-admin dependency and a
cloud bucket to own — the same class of blocker that killed Lakehouse Federation.

### The single biggest risk of the top choice

**No idempotency token on the Statement Execution API.** `statement_id` is server-generated; if the
connection dies before the app reads the POST response, there is no documented way to determine
whether the statement committed, and a blind retry double-writes.

The mitigation is entirely ours to build and must be treated as **in scope for the implementation
spec, not an afterthought**: a deterministic natural key on every row, client-side batch dedup, and
a staging-table + `MERGE INTO` write (or a watermark held in the app's Postgres, committed only
after a confirmed `SUCCEEDED`). This is not exotic, but it is real work, and it is precisely the
work `COPY INTO` would do for us — which is why Option 2 sits so close behind.

**Second-order risk, independent of option:** a workspace IP access list. Ask the data-platform team
about this _before_ choosing anything.

---

## What could not be determined from documentation

1. **Whether this specific workspace has an IP access list** (or context-based ingress control)
   configured, and whether it would accept Railway's shared static outbound IPs. Requires asking
   the data-platform team.
2. **Which SQL warehouse type is available to us.** Materially affects operational feel: serverless
   startup is _"typically between 2 and 6 seconds"_, whereas pro and classic take _"several minutes
   to start up (typically approximately 4 minutes)"_
   ([warehouse types](https://docs.databricks.com/aws/en/admin/sql/warehouse-types)). A nightly job
   against a cold pro warehouse pays ~4 minutes every run. **Auto-stop default idle timeout and
   minimum billing granularity per type were not found in the docs** and should be asked directly.
3. **No explicit first-party guidance recommending any specific option for "small periodic appends
   from an external app."** The
   [Statement Execution API announcement blog](https://www.databricks.com/blog/2023/03/07/databricks-sql-statement-execution-api-announcing-public-preview.html)
   positions it generically ("connect traditional and Cloud-based applications, services and
   devices to Databricks SQL") with a Google Sheets example, but says nothing about volume or
   external-app INSERTs. The closest thing to scale guidance is the `COPY INTO` vs Auto Loader
   "thousands vs millions of files" line — **treat "the Statement Execution API is the recommended
   low-volume path" as our engineering judgement, not a Databricks recommendation.**
4. **No documented hard limit on `COPY INTO`'s tracked-file skip-list.** Absence of evidence after
   checking the reference, the ingestion overview and the cloud-object-storage landing page — not
   evidence of absence.
5. **No documented row-count ceiling for a multi-row `INSERT ... VALUES`.** The 16 MiB
   statement-text limit is the only stated bound; the row figure is inferred and should be
   validated empirically before settling on a batch size.
6. **No documented restriction confirming `COPY INTO` runs on serverless vs pro vs classic
   warehouses specifically.** Inferred from the "Databricks SQL" applies-to scope tag.
7. **Zerobus regional availability** — the docs say workspace and table must be in the same
   supported region, but which regions, and whether ours qualifies, needs workspace access.
8. **Whether the target table already exists, its type (managed vs external), and who owns it.**
   Determines whether the dedicated-schema-ownership ask is viable.

---

## Source index

**Databricks — connectors and APIs**

- [Databricks SQL Connector for Python](https://docs.databricks.com/aws/en/dev-tools/python-sql-connector)
- [Statement Execution API tutorial](https://docs.databricks.com/aws/en/dev-tools/sql-execution-tutorial) · [API reference](https://docs.databricks.com/api/workspace/statementexecution) · [SDK-generated reference](https://databricks-sdk-py.readthedocs.io/en/stable/workspace/sql/statement_execution.html)
- [KB: Query timeout due to inactivity](https://kb.databricks.com/dbsql/query-timeout-due-to-inactivity-error-when-using-the-sql-execution-api)
- [Parameter markers](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-parameter-marker)
- [Databricks Connect overview](https://docs.databricks.com/aws/en/dev-tools/databricks-connect/) · [requirements](https://docs.databricks.com/aws/en/dev-tools/databricks-connect/requirements) · [Python install](https://docs.databricks.com/aws/en/dev-tools/databricks-connect/python/install)
- [Zerobus overview](https://docs.databricks.com/aws/en/ingestion/zerobus-overview) · [usage](https://docs.databricks.com/aws/en/ingestion/zerobus-ingest) · [limitations](https://docs.databricks.com/aws/en/ingestion/zerobus-limits)

**Databricks — ingestion**

- [COPY INTO SQL reference](https://docs.databricks.com/aws/en/sql/language-manual/delta-copy-into) · [Load data with COPY INTO](https://docs.databricks.com/aws/en/ingestion/copy-into/) · [with UC volumes/external locations](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/copy-into/unity-catalog) · [SQL warehouse tutorial](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/copy-into/tutorial-dbsql)
- [Ingest data from cloud object storage](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage) (COPY INTO vs Auto Loader guidance)
- [Upload files to a Unity Catalog volume](https://docs.databricks.com/aws/en/ingestion/file-upload/upload-to-volume) · [Files API reference](https://docs.databricks.com/api/workspace/files/upload)
- [PUT INTO](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-connector-put-into) · [REMOVE](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-aux-connector-remove)
- [MERGE INTO](https://docs.databricks.com/aws/en/sql/language-manual/delta-merge-into) · [Delta streaming reads/writes (txnAppId)](https://docs.databricks.com/aws/en/structured-streaming/delta-lake)

**Databricks — auth, governance, network**

- [OAuth M2M for service principals](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m) · [PAT auth](https://docs.databricks.com/aws/en/dev-tools/auth/pat)
- [Service principals](https://docs.databricks.com/aws/en/admin/users-groups/service-principals) · [Manage service principals](https://docs.databricks.com/aws/en/admin/users-groups/manage-service-principals)
- [Unity Catalog privileges reference](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control/privileges-reference) · [Manage privileges](https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/) · [Volume privileges](https://docs.databricks.com/aws/en/volumes/privileges) · [What are UC volumes](https://docs.databricks.com/aws/en/volumes/)
- [Manage external locations](https://docs.databricks.com/aws/en/connect/unity-catalog/cloud-storage/manage-external-locations) · [GRANT](https://docs.databricks.com/aws/en/sql/language-manual/security-grant)
- [Access control lists](https://docs.databricks.com/aws/en/security/auth/access-control/) · [SQL warehouse types](https://docs.databricks.com/aws/en/admin/sql/warehouse-types)
- [IP access lists](https://docs.databricks.com/aws/en/security/network/front-end/ip-access-list) · [workspace IP access lists](https://docs.databricks.com/aws/en/security/network/front-end/ip-access-list-workspace) · [context-based ingress control](https://docs.databricks.com/aws/en/security/network/front-end/context-based-ingress)
- [ODBC compute settings](https://docs.databricks.com/aws/en/integrations/odbc/compute) (port/transport confirmation)

**Package metadata (verified via PyPI JSON API, 1 Aug 2026)**

- [`databricks-sql-connector` 4.4.0](https://pypi.org/project/databricks-sql-connector/) · [repo](https://github.com/databricks/databricks-sql-python) · [CHANGELOG](https://github.com/databricks/databricks-sql-python/blob/main/CHANGELOG.md) · [`client.py`](https://raw.githubusercontent.com/databricks/databricks-sql-python/main/src/databricks/sql/client.py) · [`auth/retry.py`](https://raw.githubusercontent.com/databricks/databricks-sql-python/main/src/databricks/sql/auth/retry.py)
- [`databricks-sdk` 0.123.0](https://pypi.org/project/databricks-sdk/) · [CHANGELOG](https://raw.githubusercontent.com/databricks/databricks-sdk-py/main/CHANGELOG.md)
- [`databricks-connect` 19.0.0](https://pypi.org/project/databricks-connect/)

**Railway**

- [Cron jobs](https://docs.railway.com/reference/cron-jobs) — minimum 5-minute interval; UTC; overlapping runs are **skipped**, not queued; _"we do not guarantee execution times to the minute"_
- [Static Outbound IPs](https://docs.railway.com/networking/static-outbound-ips) — Pro plan; three IPv4 addresses; not guaranteed dedicated
