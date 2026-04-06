# Prism Data Vault - Project Overview

## What is it?

Prism Data Vault is a RAG-based advertising strategy insights tool built for editorial teams and ad sales. Users enter a topic (e.g. "gut health") and an advertiser (e.g. "Yakult"), and the system generates a comprehensive strategic brief by combining multiple data sources through GPT-4o.

The product name is **Prism Data Vault**. The codebase lives in the `EditorStore` directory.

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Next.js (Turbopack) | 16.2.1 |
| UI Framework | React | 19.2.4 |
| Styling | Tailwind CSS v4 | `@theme` tokens |
| Design System | Prism Deep Sea | Custom dark/glass theme |
| Backend | FastAPI | Latest |
| Language Model | GPT-4o | Via OpenAI API |
| Vector DB | ChromaDB | Persistent, local |
| Auth | JWT + bcrypt | httponly cookies |
| User DB | SQLite | aiosqlite (async) |
| Analytics | Mixpanel | EU data residency |
| Python | 3.9 | macOS system Python |
| Tests | pytest (backend), vitest (frontend) | |

## Project Structure

```
EditorStore/
├── api/                    # FastAPI backend
│   ├── main.py             # App entry, all endpoints
│   ├── auth.py             # Auth router (signup/login/logout/me)
│   └── database.py         # SQLite user database
├── src/                    # Python pipeline logic
│   ├── synthesiser.py      # Main pipeline orchestrator
│   ├── prompts.py          # System & user prompt templates
│   ├── embeddings.py       # Transcript chunking & embedding
│   ├── vectorstore.py      # ChromaDB interface
│   ├── web_search.py       # DuckDuckGo + skill-based research
│   ├── audience.py         # Audience trends from CSV
│   ├── trends.py           # Google Trends (pytrends)
│   ├── formats.py          # Ad format recommendations
│   └── brief.py            # Client brief summarisation
├── frontend/               # Next.js frontend
│   ├── app/
│   │   ├── layout.tsx      # Root layout (fonts, providers)
│   │   ├── providers.tsx   # AuthProvider wrapper
│   │   ├── globals.css     # Design tokens + global styles
│   │   ├── page.tsx        # Landing page
│   │   ├── app/page.tsx    # Insights tool (protected)
│   │   ├── login/page.tsx  # Login form
│   │   ├── signup/page.tsx # Signup form
│   │   └── tetris/page.tsx # Tetris game
│   ├── components/
│   │   ├── Navbar.tsx
│   │   ├── Footer.tsx
│   │   ├── GlassCard.tsx
│   │   ├── Button.tsx
│   │   ├── CollapsiblePanel.tsx
│   │   ├── AnalyticsProvider.tsx  # Mixpanel setup
│   │   ├── TetrisBoard.tsx
│   │   ├── tetris-engine.ts
│   │   ├── useTetris.ts
│   │   ├── Leaderboard.tsx
│   │   └── PiecePreview.tsx
│   ├── contexts/
│   │   └── AuthContext.tsx  # Auth state + API methods
│   ├── proxy.ts            # Route protection (Next.js 16 middleware)
│   ├── next.config.ts
│   ├── package.json
│   └── .env.local          # NEXT_PUBLIC_MIXPANEL_TOKEN
├── skills/                 # Extensible research skills (Markdown + YAML)
│   ├── company_overview.md
│   ├── recent_news.md
│   └── strategy_and_challenges.md
├── data/
│   ├── transcripts/        # Editorial interview JSON files
│   ├── audience_trends.csv # Audience engagement by topic/segment
│   ├── format_recommendations.csv  # Ad format benchmarks
│   └── leaderboard.db      # Tetris scores (auto-created)
├── db/                     # ChromaDB vector store (auto-created)
├── tests/                  # pytest test suite
├── users.db                # SQLite user database (auto-created)
├── config.py               # Environment config loader
├── ingest.py               # Transcript → ChromaDB ingestion script
├── requirements.txt        # Python dependencies
├── CLAUDE.md               # Developer guidance for Claude Code
├── PRISM DESIGN.MD         # Design system documentation
└── PRD-prism-play.md       # Tetris feature PRD
```

## How it Works

### Insights Pipeline

When a user submits a query, the backend orchestrates six data sources in parallel:

```
User Input (topic, advertiser, KPI, optional client brief)
  │
  ├─→ 1. Editorial Search (ChromaDB vector similarity)
  ├─→ 2. Advertiser Research (DuckDuckGo → GPT-4o per skill)
  ├─→ 3. Audience Timing (CSV lookup by topic/segment)
  ├─→ 4. Google Trends (pytrends, optional)
  ├─→ 5. Format Recommendations (CSV ad format data)
  └─→ 6. Client Brief Summary (GPT-4o, if provided)
        │
        ▼
  Prompt Assembly (system + user templates from prompts.py)
        │
        ▼
  GPT-4o Synthesis
        │
        ▼
  Structured Brief (with citations and evidence)
```

The output includes sections: At a Glance, Key Recommendations, Advertiser Overview, Editorial Insights, Strategic Alignment, Audience Timing, Recommended Products, and Messaging & Tone.

### Authentication Flow

```
Signup/Login → FastAPI validates → bcrypt hash check → JWT issued as httponly cookie
                                                              │
Frontend AuthContext ← POST /api/auth/login → cookie set ─────┘
     │
     ├─→ proxy.ts checks cookie on /app/* (server-side)
     └─→ useAuth() guard in page (client-side navigation)
```

- JWT tokens expire after 7 days
- `proxy.ts` (Next.js 16 convention) protects server-side route access
- Client-side `useAuth()` hook handles SPA navigation that bypasses the proxy
- Login/signup pages use `useAuth()` context methods to ensure state sync before redirect

### Analytics (Mixpanel)

- Initialised in `AnalyticsProvider` with EU data residency
- Auto page-view tracking on route changes
- User identification (`mixpanel.identify` + `people.set`) on login/signup/session restore
- CTA click tracking on landing page
- Token configured via `NEXT_PUBLIC_MIXPANEL_TOKEN` env var

### Research Skills System

Skills are Markdown files in `skills/` with YAML frontmatter defining search queries and a GPT-4o processing prompt. The system loads all skills dynamically at runtime — add a new `.md` file to add a new research dimension with zero code changes.

Current skills:
- **Company Overview** — core business, products, market position
- **Recent News** — latest campaigns, announcements, strategic shifts
- **Strategy & Challenges** — competitive dynamics, goals, market trends

## Design System (Prism Deep Sea)

Dark-mode interface with refractive glass elements:

- **Surfaces**: Ultra-dark backgrounds (#0a0c10 base) with layered container hierarchy
- **Accent**: Cyan (#1F89DF) for interactive elements and glow effects
- **Cards**: Glass-morphism with rgba backgrounds + backdrop blur
- **Typography**: Montserrat (headlines, extrabold), Inter (body, light/regular)
- **Corners**: Conservative rounding (4-12px)
- **Effects**: Refractive gradients, drop-shadow glows, float animations

Full spec in `PRISM DESIGN.MD`. Tokens defined in `frontend/app/globals.css` via Tailwind v4 `@theme`.

## Running Locally

### Prerequisites
- Python 3.9+
- Node.js 18+
- `.env` file at root with `OPENAI_API_KEY`
- `frontend/.env.local` with `NEXT_PUBLIC_MIXPANEL_TOKEN`

### Setup

```bash
# Install dependencies
pip3 install -r requirements.txt
cd frontend && npm install && cd ..

# Ingest editorial transcripts (first time only)
python3 ingest.py

# Start backend (Terminal 1)
python3 -m uvicorn api.main:app --reload --port 8000

# Start frontend (Terminal 2)
cd frontend && npm run dev
```

Frontend runs on http://localhost:3000, backend on http://localhost:8000.

### Database

SQLite databases are auto-created:
- `users.db` — user accounts (root directory)
- `data/leaderboard.db` — Tetris scores

To inspect: `sqlite3 users.db ".tables"` / `sqlite3 users.db "SELECT id, email, name FROM users;"`

Note: passwords are bcrypt-hashed and cannot be reversed.

## Features

### Insights Tool (`/app`)
- Topic + advertiser + KPI input form
- Optional Google Trends toggle
- Optional client brief upload
- Rendered markdown brief with collapsible source panels
- Protected route (login required)

### Tetris (`/tetris`)
- NES-style scoring with level progression
- Hold piece, next-piece preview, 7-bag randomiser, SRS rotation
- Persistent leaderboard (SQLite backend)
- Designed per `PRD-prism-play.md`

### Landing Page (`/`)
- Hero section with animated monolith cube
- Feature cards, data sources showcase
- CTA buttons with Mixpanel tracking
