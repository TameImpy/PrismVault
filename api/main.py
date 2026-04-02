import sys
import os

# Ensure the project root is on sys.path so `src` and `config` are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from src.synthesiser import generate_insights
from api.database import init_db
from api.auth import router as auth_router, me_router, get_current_user


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
