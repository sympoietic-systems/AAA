from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from backend.core.logging_config import SecretMaskingFilter, get_log_dir, tail_log_file
from backend.utils.security import safe_resolve_path

router = APIRouter()

ALLOWED_LOG_FILES = {
    "error": "error.log",
    "server": "server.log",
}


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


@router.get("/errors/logs")
async def get_log_tail(
    type: Literal["error", "server"] = Query("error", description="Log file type ('error' or 'server')"),
    lines: int = Query(100, ge=1, le=500, description="Number of tail lines to retrieve (1-500)"),
    request: Request = None,
):
    """Retrieve recent lines from rotating log files.

    Guarded with:
    - Token/Password authentication via /api parent router
    - Strictly allow-listed log target files
    - safe_resolve_path traversal defense
    - Bounded line limits (max 500 lines)
    - Secret scrubbing filter before serialization
    """
    filename = ALLOWED_LOG_FILES.get(type)
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid log type requested")

    config = getattr(request.app.state, "config", {}) if request and hasattr(request, "app") else {}
    log_dir = get_log_dir(config)

    try:
        target_path = safe_resolve_path(log_dir, filename)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail="Forbidden path resolution") from e

    raw_lines = tail_log_file(target_path, max_lines=lines)

    # Secondary defense: scrub any secrets before JSON transmission
    masker = SecretMaskingFilter()
    sanitized_lines = [masker._mask_text(line) for line in raw_lines]

    return {
        "status": "success",
        "log_type": type,
        "file": filename,
        "count": len(sanitized_lines),
        "lines": sanitized_lines,
    }
