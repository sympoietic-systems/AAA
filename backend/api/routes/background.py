import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api.deps import get_background_engine
from backend.api.exceptions import ServiceException
from backend.api.schemas import BackgroundTaskRequest, BackgroundTaskResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/background", response_model=BackgroundTaskResponse)
async def run_background_task(body: BackgroundTaskRequest, engine=Depends(get_background_engine)):
    if not engine:
        raise HTTPException(status_code=503, detail="Background engine not initialized")

    try:
        payload = {
            "text": body.text,
            "conversation_id": body.conversation_id,
            "context": body.context or {},
            "use_vision": body.use_vision,
        }
        result = await engine.run(body.action, payload)
        return BackgroundTaskResponse(
            action=body.action,
            result=result.get("content", ""),
            model_used=result.get("model", ""),
            error=result.get("error"),
        )
    except ValueError as e:
        raise ServiceException(str(e))
    except Exception as e:
        logger.exception("Background task error")
        raise HTTPException(status_code=500, detail=str(e))
