# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install

# Run the FastAPI backend (Terminal 1)
python3 -m uvicorn api.main:app --reload --port 8000

# Run the Next.js frontend (Terminal 2)
cd frontend && npm run dev

# Run all Python tests
python3 -m pytest tests/ -v

# Run a single Python test file
python3 -m pytest tests/test_synthesiser.py -v

# Run frontend tests
cd frontend && npm test

# Ingest transcripts into ChromaDB (run once, or after adding new transcripts)
python3 ingest.py
```

## Environment

### Backend
Requires a `.env` file at root with:
- `OPENAI_API_KEY` (required)
- `JWT_SECRET` (defaults to `"change-me-in-production"` — change for any non-local use)

Optional overrides: `CHROMA_PERSIST_DIR`, `EMBEDDING_MODEL`, `CHAT_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`.

Python 3.9 (system Python on macOS) — do not use `dict | None` union syntax or other 3.10+ features.

### Frontend
Requires `frontend/.env.local` with:
- `NEXT_PUBLIC_MIXPANEL_TOKEN` — Mixpanel project token (EU data residency)

## Architecture

Prism Data Vault is a RAG-based advertising strategy insights tool. The frontend is a Next.js 16 app (`frontend/`) and the backend is a FastAPI server (`api/`) wrapping a Python pipeline (`src/`).

### Backend (FastAPI + Python `src/`)

**API endpoints** (`api/main.py`):
- `POST /api/auth/signup` — register (email, name, password) → JWT cookie
- `POST /api/auth/login` — authenticate → JWT cookie
- `POST /api/auth/logout` — clear cookie
- `GET /api/me` — current user (requires auth)
- `POST /api/insights` — generate brief (requires auth). Accepts `{topic, advertiser, kpi, include_google_trends, client_brief}`
- `GET /api/leaderboard` — top 10 Tetris scores (optional `?player_name=X` for rank)
- `POST /api/leaderboard` — submit Tetris score

**Auth** (`api/auth.py`):
- JWT tokens (7-day expiry) stored as httponly `access_token` cookie (samesite=lax)
- Password hashing via bcrypt (passlib)
- `get_current_user()` dependency extracts/verifies JWT from cookie

**Database** (`api/database.py`):
- SQLite via aiosqlite
- Users table: `id, email, name, hashed_password, created_at`
- DB file: `users.db` at project root

**Data sources** (gathered in `src/synthesiser.py`):
1. **Editorial transcripts** — JSON files in `data/transcripts/`, embedded into ChromaDB (`src/embeddings.py`, `src/vectorstore.py`)
2. **Advertiser web research** — skill-based DuckDuckGo + GPT-4o (`src/web_search.py`)
3. **Audience data** — CSV trends in `data/audience_trends.csv` (`src/audience.py`)
4. **Google Trends** — live pytrends data (`src/trends.py`)
5. **Format recommendations** — ad format benchmarks in `data/format_recommendations.csv` (`src/formats.py`)
6. **Client brief summary** — optional GPT-4o summarisation (`src/brief.py`)

**Pipeline flow**:
`api/main.py` → `synthesiser.generate_insights()` → gathers all sources → assembles prompt from `src/prompts.py` → calls GPT-4o → returns dict with synthesis + raw data for UI.

### Frontend (Next.js 16)

**Important**: This project uses Next.js 16.2.1 with Turbopack. Middleware uses the `proxy.ts` convention (not `middleware.ts`). Read `node_modules/next/dist/docs/` before making framework-level changes.

**Pages**:
- `/` — marketing landing page (Prism Deep Sea design system)
- `/app` — insights tool (protected route)
- `/login` — login form
- `/signup` — signup form
- `/tetris` — Tetris game with leaderboard

**Route protection** (dual approach):
1. **Server-side**: `proxy.ts` checks for `access_token` cookie on `/app/*` routes, redirects to `/login?redirect=...` if missing
2. **Client-side**: `useAuth()` guard in `/app/page.tsx` handles client-side navigation that bypasses the proxy

**Auth context** (`contexts/AuthContext.tsx`):
- `AuthProvider` wraps entire app (via `providers.tsx` → `layout.tsx`)
- `useAuth()` hook: `{ user, loading, login, signup, logout }`
- Login/signup pages must use `useAuth()` methods (not raw fetch) so state updates before navigation
- Calls `mixpanel.identify()` on successful auth

**Analytics** (`components/AnalyticsProvider.tsx`):
- Mixpanel with EU API host (`api-eu.mixpanel.com`)
- Auto page-view tracking via `usePathname()`
- `useAnalytics()` hook: `{ track, identify }`

**Design system** (Prism Deep Sea):
- Tokens in `app/globals.css` using Tailwind v4 `@theme`
- Dark mode: ultra-dark surfaces (#0a0c10) + cyan accent (#1F89DF)
- Glass-card effect, refractive gradients, glow effects
- Fonts: Montserrat (headlines), Inter (body)

**Components** (`components/`):
- Navbar, Footer, GlassCard, Button, CollapsiblePanel, SectionHeading, StatusDot
- Tetris: TetrisBoard, tetris-engine, useTetris, Leaderboard, PiecePreview

### Research skills system

`skills/*.md` files define extensible research capabilities. Each has YAML frontmatter (`name`, `queries` with `{brand}` placeholder, `max_results_per_query`) and a prompt body with `{brand}` and `{search_results}` placeholders. `src/web_search.py` loads all skills at runtime via glob — adding a new `.md` file adds a new research dimension with no code changes.

DuckDuckGo searches use the `ddgs` package (not the deprecated `duckduckgo_search`). Rate limiting (1.5s between queries) and retries (3 attempts, 2s delay) handle transient TLS failures.

### Key data contracts

- `generate_insights()` returns: `{content, sources, research_skills, audience_timing, google_trends, format_recommendations, client_brief_summary}`
- Each skill result: `{skill_name, raw_results, processed_summary, error}`
- `USER_PROMPT_TEMPLATE` placeholders: `{topic}`, `{advertiser}`, `{advertiser_kpi}`, `{editorial_insights}`, `{advertiser_research}`, `{audience_timing}`, `{google_trends}`, `{format_recommendations}`, `{client_brief}`

### Prompt structure

`SYSTEM_PROMPT` defines output sections: At a Glance, Key Recommendations, Advertiser Overview, Editorial Insights, Strategic Alignment, Audience Timing, Recommended Products, Messaging & Tone. `USER_PROMPT_TEMPLATE` assembles all gathered data. Both live in `src/prompts.py`. The system prompt instructs the model to cite sources with inline links and ground all recommendations in evidence.

## Testing

After implementing any feature or change — no matter how small — always launch the `unit-test-runner` agent to write and run tests for the new or modified code. Do not skip this step.

- **Backend**: `python3 -m pytest tests/ -v`
- **Frontend**: `cd frontend && npm test` (vitest)

## Known issues

- Use `python3 -m uvicorn` instead of bare `uvicorn` (not on PATH)
- Frontend dev server uses `--max-old-space-size=512` to limit Node memory (Turbopack can be hungry)
- Delete `frontend/.next/` if you see stale build errors after file renames/deletions
- CORS is configured for `localhost:3000` and `127.0.0.1:3000` only
