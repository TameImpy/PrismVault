# PrismVault

A RAG-based strategic insights tool that combines editorial interview transcripts, live web research, audience engagement data, and Google Trends into actionable advertising briefs — powered by GPT-4o.

## Setup

```bash
pip3 install -r requirements.txt
```

Create a `.env` file:
```
OPENAI_API_KEY=your-key-here
```

## Usage

1. Ingest editorial transcripts (JSON files in `data/transcripts/`):
   ```bash
   python3 ingest.py
   ```

2. Run the app:
   ```bash
   python3 -m streamlit run app.py
   ```

3. Enter a topic and advertiser to generate a strategic insights brief.

## Research Skills

Advertiser research is driven by extensible markdown skill files in `skills/`. Each skill defines search queries and a GPT-4o processing prompt. Add a new `.md` file to add a new research dimension — no code changes needed.

## Tests

```bash
python3 -m pytest tests/ -v
```
