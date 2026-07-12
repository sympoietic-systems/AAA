from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class NotificationCreatePayload(BaseModel):
    id: str | None = None
    type: str  # 'sediment', 'glitch', 'trace'
    snippet: str
    timestamp: str | None = None
    conversation_id: str | None = None
    message_id: int | None = None
    parent_message_id: int | None = None
    speaker: str | None = None
    source: str | None = None
    read: int = 0
    dismissed: int = 0
    source_type: str | None = None
    source_id: str | None = None


class ClearPayload(BaseModel):
    type: str | None = None


@router.get("/notifications", response_model=list[dict[str, Any]])
async def list_notifications(
    dismissed: bool | None = None,
    type: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    request: Request = None,
):
    state = request.app.state
    notification_repo = state.notification_repo
    return notification_repo.list_all(
        limit=limit,
        offset=offset,
        dismissed=dismissed,
        type_filter=type,
        search_query=search,
    )


@router.get("/notifications/{id}", response_model=dict[str, Any])
async def get_notification(id: str, request: Request = None):
    state = request.app.state
    notification_repo = state.notification_repo
    notif = notification_repo.get(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.post("/notifications", response_model=dict[str, Any])
async def create_notification(
    payload: NotificationCreatePayload,
    request: Request = None,
):
    state = request.app.state
    notification_repo = state.notification_repo
    try:
        return notification_repo.create(
            type=payload.type,
            snippet=payload.snippet,
            id=payload.id,
            timestamp=payload.timestamp,
            conversation_id=payload.conversation_id,
            message_id=payload.message_id,
            parent_message_id=payload.parent_message_id,
            speaker=payload.speaker,
            source=payload.source,
            read=payload.read,
            dismissed=payload.dismissed,
            source_type=payload.source_type,
            source_id=payload.source_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/notifications/{id}/read", response_model=dict[str, Any])
async def mark_read(id: str, request: Request = None):
    state = request.app.state
    notification_repo = state.notification_repo
    notif = notification_repo.mark_as_read(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.patch("/notifications/{id}/unread", response_model=dict[str, Any])
async def mark_unread(id: str, request: Request = None):
    state = request.app.state
    notification_repo = state.notification_repo
    notif = notification_repo.mark_as_unread(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.patch("/notifications/{id}/dismiss", response_model=dict[str, Any])
async def dismiss_notification(id: str, request: Request = None):
    state = request.app.state
    notification_repo = state.notification_repo
    notif = notification_repo.dismiss(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.patch("/notifications/dismiss-match", response_model=dict[str, Any])
async def dismiss_by_match_endpoint(
    conversation_id: str,
    message_id: int,
    request: Request = None,
) -> dict[str, Any]:
    """
    Dismiss notifications matching a specific conversation and message pair.

    This is used to mark notifications (e.g. sediment notifications) as dismissed
    when the user views the corresponding message node. It executes an UPDATE
    query which succeeds without throwing 404s even if no matching notifications exist.

    Args:
        conversation_id: The unique identifier of the conversation.
        message_id: The ID of the message.
        request: The FastAPI request context.

    Returns:
        dict: A status dictionary indicating successful operation.
    """
    state = request.app.state
    notification_repo = state.notification_repo
    notification_repo.dismiss_by_match(conversation_id, message_id)
    return {"status": "ok"}


@router.post("/notifications/clear")
async def clear_notifications(
    payload: ClearPayload | None = None,
    request: Request = None,
):
    state = request.app.state
    notification_repo = state.notification_repo
    if payload and payload.type:
        notification_repo.clear_by_type(payload.type)
    else:
        notification_repo.clear_all()
    return {"status": "ok"}


@router.post("/notifications/read")
async def mark_all_read_endpoint(
    payload: ClearPayload | None = None,
    request: Request = None,
):
    state = request.app.state
    notification_repo = state.notification_repo
    if payload and payload.type:
        notification_repo.mark_all_as_read(payload.type)
    else:
        notification_repo.mark_all_as_read()
    return {"status": "ok"}
