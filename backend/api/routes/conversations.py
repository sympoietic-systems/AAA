from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from .schemas import ConversationInfo, ConversationListResponse, ConversationUpdateRequest
from backend.api.helpers import _ensure_structural_tags

router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(request: Request, tag: Optional[str] = None):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    checkpoint_repo = getattr(state, "checkpoint_repo", None)
    if not conv_repo:
        return ConversationListResponse(conversations=[])
    convos = conv_repo.list_all(tag=tag)

    res_convos = []
    for c in convos:
        tags = _ensure_structural_tags(conv_repo, c)
        summary = None
        human_summary = None
        if checkpoint_repo:
            cp = checkpoint_repo.get_latest(c.id)
            if cp:
                summary = cp.get("summary")
                human_summary = cp.get("human_summary")
        res_convos.append(
            ConversationInfo(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=c.message_count,
                tags=[{"tag": t["tag"], "tag_type": t["tag_type"]} for t in tags],
                summary=summary,
                human_summary=human_summary,
            )
        )
    return ConversationListResponse(conversations=res_convos)


@router.get("/conversations/{conversation_id}", response_model=ConversationInfo)
async def get_conversation(conversation_id: str, request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    checkpoint_repo = getattr(state, "checkpoint_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    tags = _ensure_structural_tags(conv_repo, conv)
    summary = None
    human_summary = None
    if checkpoint_repo:
        cp = checkpoint_repo.get_latest(conv.id)
        if cp:
            summary = cp.get("summary")
            human_summary = cp.get("human_summary")

    return ConversationInfo(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=conv.message_count,
        tags=[{"tag": t["tag"], "tag_type": t["tag_type"]} for t in tags],
        summary=summary,
        human_summary=human_summary,
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationInfo)
async def update_conversation(
    conversation_id: str, body: ConversationUpdateRequest, request: Request
):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    checkpoint_repo = getattr(state, "checkpoint_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_repo.update_title(conversation_id, body.title)
    conv = conv_repo.get(conversation_id)

    tags = _ensure_structural_tags(conv_repo, conv)
    summary = None
    human_summary = None
    if checkpoint_repo:
        cp = checkpoint_repo.get_latest(conv.id)
        if cp:
            summary = cp.get("summary")
            human_summary = cp.get("human_summary")

    return ConversationInfo(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=conv.message_count,
        tags=[{"tag": t["tag"], "tag_type": t["tag_type"]} for t in tags],
        summary=summary,
        human_summary=human_summary,
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request):
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv_repo.delete(conversation_id)
    return {"status": "deleted", "id": conversation_id}


@router.post("/conversations/{conversation_id}/generate-title", response_model=ConversationInfo)
async def generate_conversation_title(conversation_id: str, request: Request):
    from backend.api.routes.chat import _generate_title_from_conversation

    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    background_engine = getattr(state, "background_engine", None)
    if not background_engine:
        raise HTTPException(status_code=503, detail="Background engine not available")

    title = await _generate_title_from_conversation(
        background_engine, request.app.state.message_repo, conversation_id
    )
    conv_repo.update_title(conversation_id, title)

    conv = conv_repo.get(conversation_id)
    tags = _ensure_structural_tags(conv_repo, conv)
    return ConversationInfo(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=conv.message_count,
        tags=[{"tag": t["tag"], "tag_type": t["tag_type"]} for t in tags]
    )
