from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from backend.api.helpers import _parse_chat_request
from backend.api.schemas import ChatResponse, ChatRequest, GenerateRequest
from backend.services.chat import ChatService
from backend.services.title import TitleService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, background_tasks: BackgroundTasks):
    parsed = await _parse_chat_request(request)
    content, speaker, conversation_id, attachments, include_structural_scoring, max_tokens_override, parent_message_id = parsed

    service = ChatService(request.app.state)
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/message", response_model=ChatResponse)
async def chat_message(request: Request, body: ChatRequest):
    service = ChatService(request.app.state)
    try:
        # Convert list of AttachmentInfo to list of dict if present
        attachments_dict = [a.dict() for a in body.attachments] if body.attachments else None
        return await service.save_message(
            content=body.content,
            speaker=body.speaker,
            conversation_id=body.conversation_id,
            attachments=attachments_dict,
            include_structural_scoring=body.include_structural_scoring,
            parent_message_id=body.parent_message_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/generate", response_model=ChatResponse)
async def chat_generate(request: Request, body: GenerateRequest, background_tasks: BackgroundTasks):
    service = ChatService(request.app.state)
    try:
        return await service.generate_response(
            conversation_id=body.conversation_id,
            user_message_id=body.user_message_id,
            max_tokens_override=body.max_tokens,
            include_structural_scoring=body.include_structural_scoring,
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

