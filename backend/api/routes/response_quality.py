"""Authenticated quality review and reversible manual classification."""

import asyncio
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.datastructures import State

from backend.api.deps import get_app_state, get_message_repo
from backend.services.response_quality import assess_message
from backend.storage.repositories import MessageRepository
from backend.utils.message_quality import content_hash

router = APIRouter()


class QualityOverride(BaseModel):
    status: Literal["sound", "degraded", "uncertain", "unassessed"]
    reason: str = Field(min_length=1, max_length=500)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


@router.get("/messages/quality")
async def review_quality(
    status: Literal["degraded", "uncertain"] = "degraded",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: MessageRepository = Depends(get_message_repo),
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(repo.list_quality, status, limit, offset)


@router.post("/messages/{message_id}/quality/assess")
async def assess(
    message_id: int, repo: MessageRepository = Depends(get_message_repo), state: State = Depends(get_app_state)
) -> dict[str, Any]:
    message = await asyncio.to_thread(repo.get_by_id, message_id)
    if message is None:
        raise HTTPException(404, "Message not found")
    if message.speaker != "apparatus":
        raise HTTPException(422, "Only assistant messages can be assessed")
    try:
        return await assess_message(repo, state.config, message, state.response_quality_semaphore)
    except ValueError as exc:
        raise HTTPException(409, "Message changed during assessment") from exc


@router.patch("/messages/{message_id}/quality")
async def override(
    message_id: int, payload: QualityOverride, repo: MessageRepository = Depends(get_message_repo)
) -> dict[str, Any]:
    message = await asyncio.to_thread(repo.get_by_id, message_id)
    if message is None:
        raise HTTPException(404, "Message not found")
    if message.speaker != "apparatus":
        raise HTTPException(422, "Only assistant messages can be assessed")
    if payload.content_hash != content_hash(message.content):
        raise HTTPException(409, "Message changed; reload before classifying")
    try:
        return await asyncio.to_thread(
            repo.save_quality,
            message_id,
            {
                "status": payload.status,
                "reason": payload.reason,
                "source": "manual",
                "content_hash": payload.content_hash,
                "confidence": None,
            },
        )
    except ValueError as exc:
        raise HTTPException(409, "Message changed; reload before classifying") from exc
