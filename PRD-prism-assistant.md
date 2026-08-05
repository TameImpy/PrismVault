# PRD: Prism Assistant — AI-powered data product knowledge base for sales

## Problem Statement

The sales team frequently needs quick answers about Immediate Media's data products, audience segments, targeting methodologies, SLAs, and processes. Currently this knowledge is scattered across multiple documents (PDFs, Word docs, CSVs, slide decks) and the team either has to dig through files or email the audience team for basic questions. This creates delays, inconsistent answers, and unnecessary load on the audience team for questions that could be self-served.

## Solution

Build a "Prism Assistant" — a conversational AI chat interface within the existing Prism Data Vault application. The assistant is grounded in a curated knowledge base of internal documentation about IM Audiences, data products, methodologies, SLAs, and the full segment library. Sales users can ask natural language questions and get immediate, accurate answers. The assistant uses OpenAI function calling to search the segment library when specific segment data is needed, and streams responses in real-time for a responsive experience.

## User Stories

1. As a sales user, I want to ask natural language questions about our data products, so that I can quickly get accurate answers without searching through documents.
2. As a sales user, I want to ask what audience segments we have for a specific category (e.g. "food & drink"), so that I can recommend relevant targeting options to a client.
3. As a sales user, I want to see segment sizes when asking about specific segments, so that I can advise clients on potential reach.
4. As a sales user, I want to understand the difference between Permutive and Audience Project, so that I can explain our methodology to clients.
5. As a sales user, I want to know the SLAs for audience requests, so that I can set client expectations on turnaround times.
6. As a sales user, I want to know the correct email address and process for audience requests, so that I follow the right workflow.
7. As a sales user, I want to ask about our cookie-less targeting approach, so that I can confidently pitch our privacy-first proposition.
8. As a sales user, I want to ask about lookalike modelling capabilities, so that I can propose audience extension to clients.
9. As a sales user, I want to ask about data onboarding and identity matching, so that I can discuss integration options with clients.
10. As a sales user, I want to have a multi-turn conversation with follow-up questions, so that I can explore a topic in depth without re-explaining context.
11. As a sales user, I want to see responses stream in real-time, so that the interface feels responsive and I can start reading immediately.
12. As a sales user, I want suggested prompt cards when I first open the assistant, so that I know what kinds of questions I can ask.
13. As a sales user, I want the assistant to tell me when it doesn't know something and direct me to the audience team, so that I don't act on incorrect information.
14. As a sales user, I want the assistant to never invent segment names or capabilities, so that I can trust everything it tells me.
15. As a sales user, I want to access the assistant from the main navigation, so that it's easy to find alongside the other tools.
16. As a sales user, I want the assistant page to require login, so that only authorised users can access it.
17. As a sales user, I want the assistant to match the existing Prism Deep Sea design, so that the experience feels consistent with the rest of the application.
18. As a sales user, I want to ask about the rate card for data products, so that I can quote pricing guidance to clients.
19. As a sales user, I want to ask what insight deliverables are available for audience campaigns, so that I can set expectations with clients on what reporting they'll receive.
20. As a sales user, I want to ask about tracking pixel requirements, so that I know when to involve the audience team before campaign launch.
21. As a sales user, I want to ask about demographic targeting options, so that I can advise on what demographic segments are available.
22. As a sales user, I want to ask about programmatic access to segments (PMP, PG, DSP sharing), so that I can discuss deal structures with agencies.
23. As a sales user, I want the conversation to reset when I refresh the page, so that I start fresh without stale context.
24. As a knowledge base maintainer, I want the knowledge documents stored as markdown in the repo, so that they're version-controlled and easy to update.
25. As a knowledge base maintainer, I want the segment library kept as a CSV, so that it can be updated by replacing a single file.

## Implementation Decisions

- **LLM**: GPT-4o via the existing OpenAI integration. No new API keys or dependencies required.
- **Knowledge approach**: Context stuffing — the entire knowledge base (~15-20k tokens) is loaded into the system prompt on every request. This guarantees the model always has access to everything and avoids retrieval misses. RAG is not needed at this scale.
- **Knowledge base files**: The six source documents (CSV, PDF, DOCX) are converted to 3 markdown files plus the CSV, stored in a `data/assistant/` directory:
  - `data_proposition.md` — merged from Audience Team Intro, IM Audiences 2024, and Key Terms. Covers what Prism is, methodologies (Permutive & Audience Project), available solutions, insight deliverables, glossary.
  - `faqs.md` — the sales FAQs as Q&A pairs.
  - `slas_and_process.md` — SLAs table, request process, contact info, tracking pixel requirements.
  - `segment_library.csv` — the full segment library for structured lookup.
- **Segment lookup via function calling**: OpenAI function calling with a `search_segments` tool. Parameters: `query` (string, required — matched case-insensitively against name and description), `category` (string, optional — filter by segment category), `max_results` (int, optional, default 20). Returns: name, size, category, and description per match. Dashboard codes and include/exclude flags are omitted as they're internal/technical.
- **Conversation**: Multi-turn chat. History held client-side in React state (array of `{role, content}` messages). Full history sent to the API on each request. Resets on page refresh — no persistence needed.
- **Streaming**: Server-Sent Events (SSE) from a `POST /api/assistant/chat` endpoint. Two event types: `content` (text tokens to append) and `status` (e.g. "Searching segments..." during tool execution). Single round of function calling per message.
- **Function calling flow**: The backend streams the initial response. If a tool call is returned instead of content, the backend sends a `status` event, executes the tool, makes a second streaming API call with the tool result, and resumes streaming content events.
- **Chat UI**: Full-page layout at `/assistant`. Glass-card message bubbles (user right-aligned, assistant left-aligned), fixed input bar at bottom. "Prism Assistant" header with subtitle "Ask me anything about our data products and audience segments."
- **Welcome state**: 3 suggested prompt cards shown on empty chat state, disappearing after the first message is sent. Clicking a card sends it as a message. Prompts: (1) "What audience segments do we have for [category]?" (2) "How does our 1st party data targeting work?" (3) "What are the SLAs for audience requests?"
- **Navigation**: New "Assistant" item in the Navbar linking to `/assistant`.
- **Route protection**: Same dual approach as `/app` — `proxy.ts` checks for `access_token` cookie on `/assistant` routes, plus `useAuth()` client-side guard. Redirects to `/login` if unauthenticated.
- **System prompt**: Instructs the assistant to: identify as Prism Assistant for the Immediate Media sales team; answer only from the provided knowledge base; say "I don't know" and direct to dl-audience-ads@immediate.co.uk when unsure; be concise and practical; include segment sizes where available; never invent segment names, capabilities, or pricing.
- **Backend module**: A single `src/assistant.py` module encapsulates all logic — knowledge loading, segment search, and chat streaming with function calling. Exposed through a simple interface: `load_knowledge_base()`, `search_segments()`, `chat()`.

## Testing Decisions

- Tests should verify external behaviour through public interfaces, not implementation details. A test should survive an internal refactor without breaking.
- **Modules to test**:
  - `src/assistant.py` — test `load_knowledge_base()` returns non-empty content containing expected sections; test `search_segments()` with various queries, categories, and edge cases (no matches, max_results cap); test `chat()` yields expected event types with OpenAI mocked.
  - API endpoint — test `POST /api/assistant/chat` returns SSE stream, requires auth, handles malformed input. Following the pattern in existing `test_api.py`.
- **Prior art**: `tests/test_web_search.py` (mocking external APIs, testing data loading), `tests/test_api.py` (endpoint testing with auth).

## Out of Scope

- RAG / vector embeddings for the knowledge base (context stuffing is sufficient at this scale)
- Conversation persistence (no database storage of chat history)
- Multiple tool call rounds per message
- Admin UI for editing knowledge base content (edit markdown files directly)
- Analytics/tracking of assistant usage (can be added later via existing Mixpanel)
- File upload or dynamic knowledge base updates through the UI
- Voice input or text-to-speech

## Further Notes

- The knowledge base is approximately 50-80KB of source text, which compresses to ~15-20k tokens in the system prompt. This leaves ample room for multi-turn conversation history within GPT-4o's 128k context window.
- The segment library CSV contains ~1,800 rows. A category-level summary is included in the system prompt so the LLM knows what's available without loading all rows. The `search_segments` function handles specific lookups.
- If the knowledge base grows substantially in future (e.g. 500KB+), the architecture can be migrated to RAG using the existing ChromaDB infrastructure without changing the API contract or frontend.
- The 3 suggested prompts can be updated easily in the frontend without backend changes.
