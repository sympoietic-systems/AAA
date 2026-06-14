from fastapi import APIRouter, HTTPException, Request

from backend.services.daemon import DaemonService

router = APIRouter()


@router.get("/daemon/status")
async def get_daemon_status(request: Request):
    status = DaemonService.get_status(request.app.state)
    if status is None:
        raise HTTPException(status_code=503, detail="Dream Daemon not initialized")
    return status


@router.post("/daemon/trigger")
async def trigger_daemon_dream(request: Request):
    result = await DaemonService.trigger(request.app.state)
    if result is None:
        raise HTTPException(status_code=503, detail="Dream Daemon not initialized")
    return result


@router.get("/daemon/dreams")
async def get_recent_dreams(request: Request, hours: int = 48):
    """Return recent dream conversations from the last N hours."""
    daemon = getattr(request.app.state, "dream_daemon", None)
    if not daemon:
        raise HTTPException(status_code=503, detail="Dream Daemon not initialized")
    dreams = DaemonService.get_recent_dreams(request.app.state, hours)
    return {"dreams": dreams, "count": len(dreams)}
