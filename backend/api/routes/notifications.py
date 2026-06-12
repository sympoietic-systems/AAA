from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


class NotificationCreatePayload(BaseModel):
    id: Optional[str] = None
    type: str  # 'sediment', 'glitch', 'trace'
    snippet: str
    timestamp: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[int] = None
    parent_message_id: Optional[int] = None
    speaker: Optional[str] = None
    source: Optional[str] = None
    read: int = 0
    dismissed: int = 0


class ClearPayload(BaseModel):
    type: Optional[str] = None


@router.get("/notifications", response_model=List[Dict[str, Any]])
async def list_notifications(
    dismissed: Optional[bool] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
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


@router.post("/notifications", response_model=Dict[str, Any])
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
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/notifications/{id}/read", response_model=Dict[str, Any])
async def mark_read(id: str, request: Request = None):
    state = request.app.state
    notification_repo = state.notification_repo
    notif = notification_repo.mark_as_read(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.patch("/notifications/{id}/dismiss", response_model=Dict[str, Any])
async def dismiss_notification(id: str, request: Request = None):
    state = request.app.state
    notification_repo = state.notification_repo
    notif = notification_repo.dismiss(id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.patch("/notifications/dismiss-match", response_model=Dict[str, Any])
async def dismiss_by_match_endpoint(
    conversation_id: str,
    message_id: int,
    request: Request = None,
) -> Dict[str, Any]:
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
    payload: Optional[ClearPayload] = None,
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
    payload: Optional[ClearPayload] = None,
    request: Request = None,
):
    state = request.app.state
    notification_repo = state.notification_repo
    if payload and payload.type:
        notification_repo.mark_all_as_read(payload.type)
    else:
        notification_repo.mark_all_as_read()
    return {"status": "ok"}

