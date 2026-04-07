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


class CreateSampleRequest(BaseModel):
    content: str


@router.get("")
async def list_samples(user: dict = Depends(get_current_user)):
    samples = await get_email_samples(user["id"])
    return samples


@router.post("", status_code=201)
async def add_sample(req: CreateSampleRequest, user: dict = Depends(get_current_user)):
    if not req.content or not req.content.strip():
        raise HTTPException(status_code=422, detail="Content must not be empty.")
    try:
        sample = await create_email_sample(user["id"], req.content.strip())
        return sample
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{sample_id}")
async def remove_sample(sample_id: int, user: dict = Depends(get_current_user)):
    deleted = await delete_email_sample(sample_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Sample not found.")
    return {"detail": "Deleted."}
