from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from backend.api.schemas import ConversationInfo, ConversationListResponse, ConversationUpdateRequest
from backend.services.conversation import ConversationService
from backend.services.title import TitleService

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
        info = ConversationService.build_conversation_info(conv_repo, checkpoint_repo, c)
        res_convos.append(ConversationInfo(**info))
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
    info = ConversationService.build_conversation_info(conv_repo, checkpoint_repo, conv)
    return ConversationInfo(**info)


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
    info = ConversationService.build_conversation_info(conv_repo, checkpoint_repo, conv)
    return ConversationInfo(**info)


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
    state = request.app.state
    conv_repo = getattr(state, "conversation_repo", None)
    checkpoint_repo = getattr(state, "checkpoint_repo", None)
    if not conv_repo:
        raise HTTPException(status_code=404, detail="Conversations not available")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    background_engine = getattr(state, "background_engine", None)
    if not background_engine:
        raise HTTPException(status_code=503, detail="Background engine not available")

    title = await TitleService.generate_from_conversation(
        background_engine, request.app.state.message_repo, conversation_id
    )
    conv_repo.update_title(conversation_id, title)
    conv = conv_repo.get(conversation_id)
    info = ConversationService.build_conversation_info(conv_repo, checkpoint_repo, conv)
    return ConversationInfo(**info)
