import sys
import os

# Ensure the project root is on sys.path so `src` and `config` are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

import config
from src.synthesiser import generate_insights
from api.database import init_db
from api.auth import router as auth_router, me_router, get_current_user

LEADERBOARD_DB = os.path.join(os.path.dirname(__file__), "..", "data", "leaderboard.db")


@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield


app = FastAPI(title="Editorial Data Vault API", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(me_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


def _get_db():
    """Return a connection to the leaderboard SQLite database, creating the
    table on first use."""
    conn = sqlite3.connect(LEADERBOARD_DB)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            score INTEGER NOT NULL,
            lines INTEGER NOT NULL,
            level INTEGER NOT NULL,
            user_id TEXT,
            created_at TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


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
def submit_score(entry: LeaderboardSubmission):
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO scores (player_name, score, lines, level, user_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (entry.player_name, entry.score, entry.lines, entry.level, entry.user_id, now),
        )
        row_id = cursor.lastrowid
        conn.commit()
        # Compute rank
        rank = conn.execute(
            "SELECT COUNT(*) FROM scores WHERE score > (SELECT score FROM scores WHERE id = ?)",
            (row_id,),
        ).fetchone()[0] + 1
        return {
            "id": row_id,
            "rank": rank,
            "player_name": entry.player_name,
            "score": entry.score,
            "lines": entry.lines,
            "level": entry.level,
            "created_at": now,
        }
    finally:
        conn.close()


@app.get("/api/leaderboard")
def get_leaderboard(player_name: Optional[str] = Query(None)):
    conn = _get_db()
    try:
        # Top 10 with dense ranking
        rows = conn.execute(
            "SELECT player_name, score, lines, level, created_at FROM scores ORDER BY score DESC LIMIT 10"
        ).fetchall()

        top_10 = []
        prev_score = None
        rank = 0
        for i, row in enumerate(rows):
            if row["score"] != prev_score:
                rank = i + 1
                prev_score = row["score"]
            top_10.append({
                "rank": rank,
                "player_name": row["player_name"],
                "score": row["score"],
                "lines": row["lines"],
                "level": row["level"],
                "created_at": row["created_at"],
            })

        total_players = conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]

        # Player rank (best score for this name)
        player_rank = None
        if player_name:
            best = conn.execute(
                "SELECT MAX(score) as best_score FROM scores WHERE player_name = ?",
                (player_name,),
            ).fetchone()
            if best and best["best_score"] is not None:
                player_rank = conn.execute(
                    "SELECT COUNT(DISTINCT score) + 1 FROM scores WHERE score > ?",
                    (best["best_score"],),
                ).fetchone()[0]

        return {
            "top_10": top_10,
            "player_rank": player_rank,
            "total_players": total_players,
        }
    finally:
        conn.close()
