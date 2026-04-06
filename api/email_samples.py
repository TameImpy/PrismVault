"""
Email samples API router: CRUD endpoints for managing writing style samples.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from api.auth import get_current_user
from api.database import (
    create_email_sample,
    get_email_samples,
    delete_email_sample,
)

router = APIRouter(prefix="/api/email-samples", tags=["email-samples"])

# Overridden in tests to point at a test database.
DB_PATH = None


def _get_db_path():
    if DB_PATH is not None:
        return DB_PATH
    from api.database import DEFAULT_DB_PATH
    return DEFAULT_DB_PATH


class CreateSampleRequest(BaseModel):
    content: str


@router.get("")
async def list_samples(user: dict = Depends(get_current_user)):
    db_path = _get_db_path()
    samples = await get_email_samples(user["id"], db_path)
    return samples


@router.post("", status_code=201)
async def add_sample(req: CreateSampleRequest, user: dict = Depends(get_current_user)):
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=422, detail="Content must not be empty.")
    db_path = _get_db_path()
    try:
        sample = await create_email_sample(user["id"], req.content.strip(), db_path)
        return sample
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{sample_id}")
async def remove_sample(sample_id: int, user: dict = Depends(get_current_user)):
    db_path = _get_db_path()
    deleted = await delete_email_sample(sample_id, user["id"], db_path)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sample not found.")
    return {"detail": "Deleted."}
