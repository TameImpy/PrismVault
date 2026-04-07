# Production deployment: migrate to Postgres, Chroma Cloud, Vercel + Railway

## Problem Statement

Prism Plan currently runs entirely on local infrastructure — SQLite for user data and leaderboard, ChromaDB persisted to a local directory, and hardcoded `localhost` URLs throughout the frontend. This makes it impossible to deploy to a publicly accessible domain. The app needs to be production-ready: hosted on reliable infrastructure with a proper database, managed vector store, and correct cross-environment configuration.

## Solution

Migrate the backend database layer from SQLite to Postgres (hosted on Railway), move the vector store from local ChromaDB to Chroma Cloud, deploy the frontend to Vercel with API proxy rewrites, and replace all hardcoded localhost URLs with relative paths. The migration preserves the existing raw SQL approach and keeps tests running against SQLite for speed.

## User Stories

1. As a user, I want to access Prism Plan from any device via a public URL, so that I don't need to run the app locally
2. As a user, I want my account and data to persist across deployments, so that I don't lose my work when the server restarts
3. As a user, I want the app to load quickly from anywhere, so that I can use it without latency issues
4. As a user, I want to sign up and log in on the production site, so that I can access the insights tool
5. As a user, I want to generate insights briefs on the production site, so that I can use the tool without a local setup
6. As a user, I want to download PowerPoint decks on the production site, so that I can share recommendations with clients
7. As a user, I want to draft emails on the production site, so that I can use the full feature set remotely
8. As a user, I want to manage my writing samples on the production site, so that email drafts match my style
9. As a user, I want to play Tetris and see the leaderboard on the production site, so that the full experience is available
10. As a user, I want to reset my password on the production site, so that I can recover my account
11. As a developer, I want to run the app locally with the same codebase that's deployed, so that dev and production don't diverge
12. As a developer, I want tests to run without needing Postgres installed locally, so that the test suite stays fast and portable
13. As a developer, I want a single migration script to set up the production database, so that deployments are repeatable
14. As a developer, I want environment-based configuration for all external services, so that I can switch between local and production without code changes
15. As a developer, I want the frontend to use relative API paths, so that the same build works on localhost and the production domain
16. As a developer, I want ChromaDB to work locally for development and connect to Chroma Cloud in production, so that I don't need a cloud account to develop
17. As a developer, I want the JWT secret to fail loudly if not set in production, so that the app never runs with the insecure default

## Implementation Decisions

### Database migration (SQLite to Postgres)

- Use the `databases` library (by Encode) with `asyncpg` driver for all database access — users, email samples, and leaderboard
- Keep raw SQL queries — no ORM. Swap `?` parameter placeholders for `:param` named style (the `databases` library convention)
- Unify the leaderboard into the same async connection pool — remove the synchronous `sqlite3` code and separate `LEADERBOARD_DB` path from `api/main.py`
- Replace the module-level `DB_PATH` override pattern in `api/auth.py` and `api/email_samples.py` with a single `DATABASE_URL` from `config.py`
- Connection pool lifecycle managed via FastAPI's lifespan handler — connect on startup, disconnect on shutdown
- All three tables (users, email_samples, scores) managed through a single database connection

### Migration script

- New standalone `scripts/migrate.py` that creates all tables in Postgres using `CREATE TABLE IF NOT EXISTS`
- No Alembic or versioned migrations at this stage — the schema is simple and stable
- Railway start command chains the migration: `python scripts/migrate.py && python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT`

### ChromaDB to Chroma Cloud

- Modify `src/vectorstore.py` to use `CloudClient` when Chroma Cloud environment variables are present (`CHROMA_CLOUD_API_KEY`, `CHROMA_CLOUD_TENANT`, `CHROMA_CLOUD_DATABASE`), fall back to `PersistentClient` for local development
- `ingest.py` remains a one-off script — run it locally pointing at Chroma Cloud to populate the production vector store
- Collection name stays `editorial_transcripts`

### Configuration

- Add to `config.py`: `DATABASE_URL` (no default — required), `CHROMA_CLOUD_API_KEY`, `CHROMA_CLOUD_TENANT`, `CHROMA_CLOUD_DATABASE` (all optional — presence triggers cloud mode)
- Remove the default fallback for `JWT_SECRET` — raise an error at startup if not set, to prevent running with `"change-me-in-production"`
- Railway provides `DATABASE_URL` automatically when Postgres add-on is attached
- Python version bump from 3.9 to 3.11 via `runtime.txt`

### Frontend

- Replace all hardcoded `http://localhost:8000` references with relative paths (`/api/...`) across all 10 affected files: `AuthContext.tsx`, `app/app/page.tsx`, `forgot-password/page.tsx`, `reset-password/page.tsx`, `tetris/page.tsx`, `Leaderboard.tsx`, `WritingSamplesModal.tsx`, `DraftEmailModal.tsx`, and any others
- Remove `API_BASE` constants and `NEXT_PUBLIC_API_URL` env var — no longer needed
- Add rewrite rules to `next.config.ts` to proxy `/api/:path*` to `http://localhost:8000/api/:path*` in development
- In production, Vercel rewrites handle the proxy to the Railway backend URL (configured in `vercel.json`)

### CORS and cookies

- With Vercel proxy, all requests are same-origin from the browser's perspective
- CORS middleware can be simplified or retained for safety, but cross-origin issues are eliminated
- Cookie auth (`samesite=lax`, `httponly`) works without changes since there's no cross-domain boundary
- Update `FRONTEND_BASE_URL` default to be configurable for password reset email links

### Deployment topology

- Frontend: Vercel (default subdomain initially, custom domain later)
- Backend: Railway (with Postgres add-on)
- Vector store: Chroma Cloud
- Domain: `*.vercel.app` initially — custom domain is a DNS change, no code changes needed

### Dependencies

- Add: `databases[asyncpg]`, `asyncpg`
- Remove: `aiosqlite`
- Add: `chromadb-client` (cloud client, if separate from main `chromadb` package — verify during implementation)

## Testing Decisions

### What makes a good test

Tests should verify external behaviour through the module's public interface, not implementation details. A database test should verify that creating a user returns the correct data and that duplicate emails are rejected — not that a specific SQL query was executed. Tests should be independent, fast, and not require external services.

### Modules to test

1. **Database module** (`api/database.py`) — All CRUD operations for users, email samples, and leaderboard scores. Existing tests in `tests/test_database.py` and `tests/test_email_samples.py` are the prior art.

2. **Leaderboard** — Score submission, ranking, top-10 retrieval. Existing tests in `tests/test_leaderboard.py` are the prior art — these currently patch `LEADERBOARD_DB` and will be updated to use the `databases` library with a SQLite URL.

3. **Auth flows** — Signup, login, logout, token verification, password reset. Existing tests in `tests/test_auth.py` are the prior art.

4. **Migration script** — Verify that `scripts/migrate.py` creates all expected tables with correct schemas.

### Test database strategy

- Tests use the `databases` library with a `sqlite:///test.db` URL — same API as production Postgres, no Postgres installation required
- The `databases` library abstracts the driver difference, so tests exercise the same code paths as production
- Test fixtures override `DATABASE_URL` in `config.py` rather than patching module-level `DB_PATH` variables

## Out of Scope

- Custom domain setup and DNS configuration — post-deployment task
- Alembic or versioned migration framework — add later when schema evolves
- Data migration from existing SQLite databases — starting with empty tables
- CI/CD pipeline setup — manual deploys initially
- Rate limiting, WAF, or DDoS protection
- Monitoring, alerting, or logging infrastructure
- SSL/TLS configuration — handled by Vercel and Railway automatically
- Performance testing or load testing
- Multi-environment setup (staging, production) — single production environment initially

## Further Notes

- The Tetris leaderboard remains publicly accessible (no auth required) — accepted risk for a fun feature with low blast radius
- The Vercel proxy approach eliminates all cross-origin complexity but means Vercel is in the request path for API calls — acceptable for current scale
- ChromaDB cloud migration is independent of the Postgres migration and could be done in either order
- The `ingest.py` workflow doesn't change for the end user — they just need Chroma Cloud env vars set when running it against the production vector store
- Railway sets `PORT` automatically — the backend must bind to `0.0.0.0:$PORT`, not hardcoded port 8000
