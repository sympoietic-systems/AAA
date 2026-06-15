from fastapi import APIRouter, BackgroundTasks, Depends, Request

from backend.api.deps import get_app_state, get_chat_service
from backend.api.exceptions import ServiceException
from backend.api.helpers import _parse_chat_request
from backend.api.schemas import ChatResponse, ChatRequest, GenerateRequest

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    background_tasks: BackgroundTasks,
    service=Depends(get_chat_service),
):
    parsed = await _parse_chat_request(request)
    content, speaker, conversation_id, attachments, include_structural_scoring, max_tokens_override, parent_message_id = parsed

    try:
        return await service.process_chat(
            content=content,
            speaker=speaker,
            conversation_id=conversation_id,
            attachments=attachments,
            include_structural_scoring=include_structural_scoring,
            max_tokens_override=max_tokens_override,
            background_tasks=background_tasks,
            parent_message_id=parent_message_id,
        )
    except ValueError as e:
        raise ServiceException(str(e), status_code=500)


@router.post("/chat/message", response_model=ChatResponse)
async def chat_message(
    request: Request,
    body: ChatRequest,
    service=Depends(get_chat_service),
):
    try:
        attachments_dict = [a.model_dump() for a in body.attachments] if body.attachments else None
        return await service.save_message(
            content=body.content,
            speaker=body.speaker,
            conversation_id=body.conversation_id,
            attachments=attachments_dict,
            include_structural_scoring=body.include_structural_scoring,
            parent_message_id=body.parent_message_id,
        )
    except ValueError as e:
        raise ServiceException(str(e), status_code=500)


@router.post("/chat/generate", response_model=ChatResponse)
async def chat_generate(
    request: Request,
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    service=Depends(get_chat_service),
):
    try:
        return await service.generate_response(
            conversation_id=body.conversation_id,
            user_message_id=body.user_message_id,
            max_tokens_override=body.max_tokens,
            include_structural_scoring=body.include_structural_scoring,
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise ServiceException(str(e), status_code=500)
