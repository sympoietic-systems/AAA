from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_message_repo
from backend.api.schemas import HistoryMessage, HistoryResponse
from backend.services.metrics import MetricsService
from backend.utils.vector import build_history_message

router = APIRouter()


@router.get("/history", response_model=HistoryResponse)
async def history(
    limit: int = 50,
    offset: int = 0,
    conversation_id: str = "",
    repo=Depends(get_message_repo),
):
    rows = repo.get_recent_with_metrics(
        limit=limit,
        offset=offset,
        conversation_id=conversation_id if conversation_id else None,
    )
    messages: list[HistoryMessage] = []
    for r in rows:
        metrics = MetricsService.build_history(r)
        messages.append(build_history_message(r, metrics))

    total_count = repo.count_messages(conversation_id if conversation_id else None)
    return HistoryResponse(messages=messages, count=total_count)


@router.get("/messages/{message_id}/thinking")
async def get_message_thinking(message_id: int, repo=Depends(get_message_repo)):
    msg = repo.get_by_id(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"thinking": msg.thinking}


@router.get("/messages/{message_id}/context")
async def get_message_context(message_id: int, repo=Depends(get_message_repo)):
    msg = repo.get_by_id(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"context_sent": msg.context_sent}


@router.get("/messages/{message_id}/path", response_model=list[HistoryMessage])
async def get_message_path(message_id: int, repo=Depends(get_message_repo)):
    ancestors = repo.get_ancestor_path(message_id, limit=500)
    if not ancestors:
        raise HTTPException(status_code=404, detail="Message path not found")

    ancestor_ids = [m.id for m in ancestors if m.id is not None]
    rows = repo.get_recent_with_metrics_for_path(ancestor_ids, limit=len(ancestor_ids))

    messages: list[HistoryMessage] = []
    for r in rows:
        metrics = MetricsService.build_history(r)
        messages.append(build_history_message(r, metrics))
    return messages
