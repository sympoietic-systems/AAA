from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter()


class NotificationCreatePayload(BaseModel):
    id: str | None = Field(default=None, max_length=100)
    type: str = Field(..., min_length=1, max_length=50)  # 'sediment', 'glitch', 'trace'
    snippet: str = Field(..., min_length=1, max_length=10_000)
    timestamp: str | None = Field(default=None, max_length=50)
    conversation_id: str | None = Field(default=None, max_length=100)
    message_id: int | None = None
    parent_message_id: int | None = None
    speaker: str | None = Field(default=None, max_length=100)
    source: str | None = Field(default=None, max_length=500)
    read: int = 0
    dismissed: int = 0
    source_type: str | None = Field(default=None, max_length=100)
    source_id: str | None = Field(default=None, max_length=100)


class ClearPayload(BaseModel):
    type: str | None = Field(default=None, max_length=50)


@router.get("/notifications", response_model=list[dict[str, Any]])
def list_notifications(
    dismissed: bool | None = None,
    type: str | None = Query(default=None, max_length=50),
    search: str | None = Query(default=None, max_length=500),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
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
def get_notification(id: str, request: Request = None):
    state = request.app.state
    notification_repo = state.notification_repo
    notif = notification_repo.get(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.post("/notifications", response_model=dict[str, Any])
def create_notification(
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
def mark_read(id: str, request: Request = None):
    state = request.app.state
    notification_repo = state.notification_repo
    notif = notification_repo.mark_as_read(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.patch("/notifications/{id}/unread", response_model=dict[str, Any])
def mark_unread(id: str, request: Request = None):
    state = request.app.state
    notification_repo = state.notification_repo
    notif = notification_repo.mark_as_unread(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.patch("/notifications/{id}/dismiss", response_model=dict[str, Any])
def dismiss_notification(id: str, request: Request = None):
    state = request.app.state
    notification_repo = state.notification_repo
    notif = notification_repo.dismiss(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.patch("/notifications/dismiss-match", response_model=dict[str, Any])
def dismiss_by_match_endpoint(
    conversation_id: str,
    message_id: int,
    request: Request = None,
) -> dict[str, Any]:
    state = request.app.state
    notification_repo = state.notification_repo
    notification_repo.dismiss_by_match(conversation_id, message_id)
    return {"status": "ok"}


@router.post("/notifications/clear")
def clear_notifications(
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
def mark_all_read_endpoint(
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
