import sys
import os

# Ensure the project root is on sys.path so `src` and `config` are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

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
from api.database import (
    connect, disconnect, init_db, get_email_samples,
    submit_score as db_submit_score, get_leaderboard as db_get_leaderboard,
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


class InsightsRequest(BaseModel):
    topic: str
    advertiser: str
    kpi: str
    include_google_trends: bool = True
    client_brief: str = ""


@app.post("/api/insights")
def create_insights(req: InsightsRequest, user: dict = Depends(get_current_user)):
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY on the server.")
    try:
        result = generate_insights(
            topic=req.topic,
            advertiser=req.advertiser,
            kpi=req.kpi,
            include_google_trends=req.include_google_trends,
            client_brief=req.client_brief,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DraftEmailRequest(BaseModel):
    content: str
    topic: str
    advertiser: str
    kpi: str


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
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DownloadDeckRequest(BaseModel):
    content: str
    topic: str
    advertiser: str
    kpi: str


def _sanitize_filename(text):
    """Replace spaces with underscores and remove special characters."""
    return re.sub(r'[^\w\-]', '', text.replace(' ', '_'))


@app.post("/api/download-deck")
async def download_deck(req: DownloadDeckRequest, user: dict = Depends(get_current_user)):
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY on the server.")
    try:
        slide_content = generate_slide_content(
            brief_content=req.content,
            topic=req.topic,
            advertiser=req.advertiser,
            kpi=req.kpi,
        )
        slide_content["kpi"] = req.kpi
        buf = build_deck(slide_content, req.topic, req.advertiser)

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
