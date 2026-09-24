from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.deps import get_history_service
from backend.api.schemas import HistoryMessage, HistoryResponse
from backend.services.history import HistoryService

router = APIRouter()


@router.get("/history", response_model=HistoryResponse)
async def history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conversation_id: str = Query(default="", max_length=100, pattern=r"^$|^[\w-]+$"),
    service: HistoryService = Depends(get_history_service),
):
    return await service.list_history(
        limit=limit,
        offset=offset,
        conversation_id=conversation_id if conversation_id else None,
    )


@router.get("/messages/{message_id}/thinking")
async def get_message_thinking(message_id: int, service: HistoryService = Depends(get_history_service)):
    try:
        thinking = await service.get_thinking(message_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Message not found") from exc
    return {"thinking": thinking}


@router.get("/messages/{message_id}/context")
async def get_message_context(message_id: int, service: HistoryService = Depends(get_history_service)):
    try:
        context = await service.get_context(message_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Message not found") from exc
    return {"context_sent": context}


@router.get("/messages/{message_id}/path", response_model=list[HistoryMessage])
async def get_message_path(message_id: int, service: HistoryService = Depends(get_history_service)):
    try:
        return await service.get_path(message_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Message path not found") from exc
