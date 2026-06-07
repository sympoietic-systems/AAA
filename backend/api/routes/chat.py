from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from backend.api.helpers import _parse_chat_request
from backend.api.schemas import ChatResponse
from backend.services.chat import ChatService
from backend.services.title import TitleService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, background_tasks: BackgroundTasks):
    parsed = await _parse_chat_request(request)
    content, speaker, conversation_id, attachments, include_structural_scoring, max_tokens_override = parsed

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
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
