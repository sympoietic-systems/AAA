import logging

from fastapi import APIRouter, HTTPException, Request

from .schemas import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
    HistoryMessage,
    HistoryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    state = request.app.state
    pipeline = state.pipeline
    repo = state.message_repo
    error_repo = state.error_repo

    try:
        result = await pipeline.run({
            "content": body.content,
            "speaker": body.speaker,
        })

        response_text = result.payload.get("response", "")
        thinking = result.payload.get("thinking")
        embedding = result.payload.get("embedding", b"")
        embedding_model = result.payload.get("embedding_model", "unknown")
        embedding_dim = result.payload.get("embedding_dim", 0)

        if result.status == "error" or not response_text:
            for err in result.errors:
                error_repo.log_error(
                    module=err["module"],
                    error=RuntimeError(err["error_message"]),
                    context={"input": body.content},
                )
            raise HTTPException(status_code=500, detail="Pipeline processing failed")

        msg = repo.insert(
            speaker=body.speaker,
            content=body.content,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
        )

        response_msg = repo.insert(
            speaker="apparatus",
            content=response_text,
            thinking=thinking,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
        )

        return ChatResponse(
            id=response_msg.id,
            timestamp=response_msg.timestamp,
            speaker="apparatus",
            content=response_text,
            thinking=thinking,
            embedding_generated=bool(embedding),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat endpoint error")
        error_repo.log_error(module="api", error=e, context={"input": body.content})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=HistoryResponse)
async def history(limit: int = 50, request: Request = None):
    state = request.app.state
    repo = state.message_repo
    messages = repo.get_recent(limit=limit)
    return HistoryResponse(
        messages=[
            HistoryMessage(
                id=m.id,
                timestamp=m.timestamp,
                speaker=m.speaker,
                content=m.content,
                thinking=m.thinking,
            )
            for m in messages
        ],
        count=len(messages),
    )


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    state = request.app.state
    registry = state.registry
    modules_status = registry.validate_all()
    return HealthResponse(
        status="ok",
        modules=modules_status,
    )


@router.get("/errors", response_model=list[dict])
async def list_errors(limit: int = 20, request: Request = None):
    state = request.app.state
    error_repo = state.error_repo
    errors = error_repo.get_recent(limit=limit)
    return [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "module": e.module,
            "error_type": e.error_type,
            "error_message": e.error_message,
            "context": e.context,
        }
        for e in errors
    ]
