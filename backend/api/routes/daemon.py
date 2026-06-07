from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/daemon/status")
async def get_daemon_status(request: Request):
    state = request.app.state
    daemon = getattr(state, "dream_daemon", None)
    if not daemon:
        raise HTTPException(status_code=503, detail="Dream Daemon not initialized")
    return daemon.get_status()


@router.post("/daemon/trigger")
async def trigger_daemon_dream(request: Request):
    state = request.app.state
    daemon = getattr(state, "dream_daemon", None)
    if not daemon:
        raise HTTPException(status_code=503, detail="Dream Daemon not initialized")

    result = await daemon.check_and_trigger_dream(force=True)
    if result is None:
        return {"status": "skipped", "reason": "No active conversation or compilation error"}
    return {"status": "success", "dream": result}
