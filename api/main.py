import sys
import os

# Ensure the project root is on sys.path so `src` and `config` are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from src.synthesiser import generate_insights

app = FastAPI(title="Editorial Data Vault API")

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
    include_google_trends: bool = True


@app.post("/api/insights")
def create_insights(req: InsightsRequest):
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY on the server.")
    try:
        result = generate_insights(
            topic=req.topic,
            advertiser=req.advertiser,
            include_google_trends=req.include_google_trends,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
def health():
    return {"status": "ok"}
