from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api.deps import get_app_state, get_dream_log_repo
from backend.services.daemon import DaemonService

router = APIRouter()


@router.get("/daemon/status")
async def get_daemon_status(state=Depends(get_app_state)):
    status = DaemonService.get_status(state)
    if status is None:
        raise HTTPException(status_code=503, detail="Dream Daemon not initialized")
    return status


@router.post("/daemon/trigger")
async def trigger_daemon_dream(state=Depends(get_app_state)):
    result = await DaemonService.trigger(state)
    if result is None:
        raise HTTPException(status_code=503, detail="Dream Daemon not initialized")
    return result


@router.get("/daemon/dreams")
async def get_recent_dreams(request: Request, limit: int = 24, repo=Depends(get_dream_log_repo)):
    if not repo:
        raise HTTPException(status_code=503, detail="Dream Log not available")
    dreams = repo.get_recent(limit)
    return {"dreams": dreams, "count": len(dreams)}
