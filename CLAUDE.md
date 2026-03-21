# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install

# Run the FastAPI backend (Terminal 1)
uvicorn api.main:app --reload --port 8000

# Run the Next.js frontend (Terminal 2)
cd frontend && npm run dev

# Run all tests
python3 -m pytest tests/ -v

# Run a single test file
python3 -m pytest tests/test_synthesiser.py -v

# Ingest transcripts into ChromaDB (run once, or after adding new transcripts)
python3 ingest.py
```

## Environment

Requires a `.env` file with `OPENAI_API_KEY`. Optional overrides: `CHROMA_PERSIST_DIR`, `EMBEDDING_MODEL`, `CHAT_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`.

Python 3.9 (system Python on macOS) — do not use `dict | None` union syntax or other 3.10+ features.

## Architecture

This is a RAG-based app that generates advertising strategy briefs by combining four data sources. The frontend is a Next.js app (`frontend/`) and the backend is a FastAPI server (`api/main.py`) wrapping the existing Python pipeline.

### Backend (FastAPI + Python `src/`)

1. **Editorial transcripts** — editor interview JSON files in `data/transcripts/`, chunked and embedded into ChromaDB (`src/embeddings.py`, `src/vectorstore.py`). Queried by topic similarity.
2. **Advertiser web research** — skill-based DuckDuckGo search + GPT-4o processing (`src/web_search.py`). Skills are defined as markdown files in `skills/`.
3. **Audience data** — CSV-based engagement trends in `data/audience_trends.csv` (`src/audience.py`).
4. **Google Trends** — live pytrends data with related queries and multi-timeframe analysis (`src/trends.py`).

### API endpoint

`POST /api/insights` — accepts `{topic, advertiser, include_google_trends}`, calls `generate_insights()`, returns the full result dict as JSON.

### Pipeline flow

`api/main.py` → `synthesiser.generate_insights()` → gathers all four sources → assembles prompt from `src/prompts.py` templates → calls GPT-4o → returns dict with synthesis + all raw intermediate data for UI display.

### Frontend (Next.js)

- `/` — marketing landing page (Prism Deep Sea design system)
- `/app` — insights tool (topic + advertiser inputs → calls `/api/insights` → renders results)
- Design system: Prism Deep Sea tokens defined in `frontend/app/globals.css` using Tailwind v4 `@theme`
- Components in `frontend/components/`: Navbar, Footer, GlassCard, Button, CollapsiblePanel, etc.

### Research skills system

`skills/*.md` files define extensible research capabilities. Each has YAML frontmatter (`name`, `queries` with `{brand}` placeholder, `max_results_per_query`) and a prompt body with `{brand}` and `{search_results}` placeholders. `src/web_search.py` loads all skills at runtime via glob — adding a new `.md` file adds a new research dimension with no code changes.

DuckDuckGo searches use the `ddgs` package (not the deprecated `duckduckgo_search`). Rate limiting (1.5s between queries) and retries (3 attempts, 2s delay) are built in to handle transient TLS failures.

### Key data contracts

- `generate_insights()` returns: `{content, sources, research_skills, audience_timing, google_trends}`
- Each skill result: `{skill_name, raw_results, processed_summary, error}`
- `USER_PROMPT_TEMPLATE` placeholders: `{topic}`, `{advertiser}`, `{editorial_insights}`, `{advertiser_research}`, `{audience_timing}`, `{google_trends}`

## Testing

After implementing any feature or change — no matter how small — always launch the `unit-test-runner` agent to write and run tests for the new or modified code. Do not skip this step.

### Prompt structure

`SYSTEM_PROMPT` defines output sections: Advertiser Overview, Editorial Insights, Strategic Alignment, Audience Timing, Messaging & Tone Recommendations. `USER_PROMPT_TEMPLATE` assembles all gathered data. Both live in `src/prompts.py`. The system prompt instructs the model to cite sources with inline links and ground all recommendations in evidence.
