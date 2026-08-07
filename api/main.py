import sys
import os

# Ensure the project root is on sys.path so `src` and `config` are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import partial
from typing import List, Optional

import json
import re

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

import config
from src.synthesiser import generate_insights
from src.email_drafter import draft_email
from src.slide_content import generate_slide_content
from src.deck_builder import build_deck
from src.provenance import drop_retired_sections
from src.assistant import chat as assistant_chat, chat_stream as assistant_chat_stream
from api.database import (
    connect, disconnect, init_db, get_email_samples,
    submit_score as db_submit_score, get_leaderboard as db_get_leaderboard,
    save_brief as db_save_brief, get_user_briefs as db_get_user_briefs,
    get_all_briefs as db_get_all_briefs, get_brief_by_id as db_get_brief_by_id,
    delete_brief as db_delete_brief,
)
from api.auth import router as auth_router, me_router, get_current_user
from api.email_samples import router as email_samples_router


@asynccontextmanager
async def lifespan(app):
    await connect()
    await init_db()
    yield
    await disconnect()


app = FastAPI(title="Editorial Data Vault API", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(me_router)
app.include_router(email_samples_router)

_frontend_url = os.environ.get("FRONTEND_BASE_URL", "")
_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if _frontend_url:
    _cors_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


class ProvenanceEntry(BaseModel):
    """One data section's provenance, posted back from a brief run (#156).

    Typed rather than a bare `list` because these entries are read with
    `.get()` downstream: an untyped list of strings from any client would be an
    AttributeError and a 500 rather than a 422. Every field defaults to "" so a
    brief saved before a field existed still posts.
    """
    section: str = ""
    source: str = ""
    as_at: str = ""
    coverage: str = ""
    period: str = ""
    cadence: str = ""


class InsightsRequest(BaseModel):
    """What the New Brief form posts.

    A browser holding the bundle from before #176 still posts
    `include_google_trends`. Pydantic ignores unknown fields by default and
    that default is doing real work here: rejecting the extra field would turn
    a tab left open across the deploy into a 422 the user cannot read their way
    out of, on a form that looks entirely valid. It is dropped rather than
    forwarded — `generate_insights()` no longer takes it — and
    `tests/test_api.py` pins both halves.
    """
    topic: str
    advertiser: str
    kpi: str
    client_brief: str = ""


@app.post("/api/insights")
async def create_insights(req: InsightsRequest, user: dict = Depends(get_current_user)):
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY on the server.")
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                generate_insights,
                topic=req.topic,
                advertiser=req.advertiser,
                kpi=req.kpi,
                client_brief=req.client_brief,
            ),
        )
        try:
            await db_save_brief(
                user_id=user["id"],
                topic=req.topic,
                advertiser=req.advertiser,
                kpi=req.kpi,
                client_brief=req.client_brief,
                result_json=json.dumps(result),
            )
        except Exception:
            pass  # Auto-save failure should not block the response
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DraftEmailRequest(BaseModel):
    content: str
    topic: str
    advertiser: str
    kpi: str
    # Where the brief's figures came from (#156), posted back verbatim so the
    # email carries the same account as the brief. Optional so an older client
    # — or a brief saved before provenance existed — still drafts.
    provenance: Optional[List[ProvenanceEntry]] = None


@app.post("/api/draft-email")
async def create_draft_email(req: DraftEmailRequest, user: dict = Depends(get_current_user)):
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY on the server.")
    try:
        samples = await get_email_samples(user["id"])
        writing_samples = [s["content"] for s in samples]
        result = draft_email(
            brief_content=req.content,
            topic=req.topic,
            advertiser=req.advertiser,
            kpi=req.kpi,
            writing_samples=writing_samples,
            provenance=_provenance_dicts(req.provenance),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DownloadDeckRequest(BaseModel):
    content: str
    topic: str
    advertiser: str
    kpi: str
    # Structured data the brief run already produced, posted back verbatim so
    # the deck and the brief can never disagree (PRD #131). All optional so an
    # older client still gets a deck.
    audience_segments: Optional[dict] = None
    format_recommendations: Optional[list] = None
    historical_research: Optional[dict] = None
    provenance: Optional[List[ProvenanceEntry]] = None


def _provenance_dicts(entries):
    """Validated provenance back to the plain dicts src/provenance.py reads.

    Entries naming a section the product has retired are dropped here rather
    than at either call site, because both of them — the deck appendix and the
    email footer — reach clients, and this is the one place the posted-back
    list passes through on its way to them (#176).
    """
    if not entries:
        return None
    return drop_retired_sections([e.model_dump() for e in entries])


def _sanitize_filename(text):
    """Replace spaces with underscores and remove special characters."""
    return re.sub(r'[^\w\-]', '', text.replace(' ', '_'))


@app.post("/api/download-deck")
async def download_deck(req: DownloadDeckRequest, user: dict = Depends(get_current_user)):
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY on the server.")
    try:
        # The LLM writes only the advertiser-overview prose and picks 3 insights
        # from the research the brief matched.
        slide_content = generate_slide_content(
            brief_content=req.content,
            topic=req.topic,
            advertiser=req.advertiser,
            kpi=req.kpi,
            historical_research=req.historical_research,
        )
        # Structured payload from the brief run, placed verbatim: segment reach
        # and format CTR/viewability are never regenerated or re-extracted.
        slide_content["audience_segments"] = req.audience_segments
        slide_content["format_recommendations"] = req.format_recommendations
        slide_content["historical_research"] = req.historical_research
        # The deck's appendix names the source behind every figure it shows.
        slide_content["provenance"] = _provenance_dicts(req.provenance)
        buf = build_deck(slide_content, req.advertiser)

        filename = "Prism_Plan_%s_%s.pptx" % (
            _sanitize_filename(req.advertiser),
            _sanitize_filename(req.topic),
        )

        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Prism Assistant
# ---------------------------------------------------------------------------


class AssistantChatRequest(BaseModel):
    messages: list


@app.post("/api/assistant/chat")
def assistant_chat_endpoint(req: AssistantChatRequest, user: dict = Depends(get_current_user)):
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY on the server.")
    try:
        result = assistant_chat(req.messages)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assistant/chat/stream")
def assistant_stream_endpoint(req: AssistantChatRequest, user: dict = Depends(get_current_user)):
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY on the server.")

    def event_generator():
        try:
            for event in assistant_chat_stream(req.messages):
                yield "data: %s\n\n" % json.dumps(event)
        except Exception as e:
            yield "data: %s\n\n" % json.dumps({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# ---------------------------------------------------------------------------
# Briefs
# ---------------------------------------------------------------------------


@app.get("/api/briefs")
async def get_briefs(scope: str = Query("mine"), user: dict = Depends(get_current_user)):
    if scope == "team":
        return await db_get_all_briefs()
    return await db_get_user_briefs(user["id"])


@app.get("/api/briefs/{brief_id}")
async def get_brief(brief_id: int, user: dict = Depends(get_current_user)):
    brief = await db_get_brief_by_id(brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found.")
    return brief


@app.delete("/api/briefs/{brief_id}")
async def remove_brief(brief_id: int, user: dict = Depends(get_current_user)):
    deleted = await db_delete_brief(brief_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Brief not found.")
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


class LeaderboardSubmission(BaseModel):
    player_name: str
    score: int
    lines: int
    level: int
    user_id: Optional[str] = None

    @field_validator("player_name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("player_name must not be empty")
        return v.strip()

    @field_validator("score")
    @classmethod
    def score_non_negative(cls, v):
        if v < 0:
            raise ValueError("score must be >= 0")
        return v


@app.post("/api/leaderboard", status_code=201)
async def post_score(entry: LeaderboardSubmission):
    now = datetime.now(timezone.utc).isoformat()
    result = await db_submit_score(
        player_name=entry.player_name,
        score=entry.score,
        lines=entry.lines,
        level=entry.level,
        user_id=entry.user_id,
        created_at=now,
    )
    return result


@app.get("/api/leaderboard")
async def get_leaderboard_endpoint(player_name: Optional[str] = Query(None)):
    return await db_get_leaderboard(player_name)
