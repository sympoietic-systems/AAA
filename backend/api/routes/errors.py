import asyncio
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from backend.api.schemas import LogClearResponse, LogFileClearResult
from backend.core.auth import auth_enabled
from backend.core.logging_config import SecretMaskingFilter, clear_active_log_files, get_log_dir, tail_log_file
from backend.utils.security import safe_resolve_path

router = APIRouter()

ALLOWED_LOG_FILES = {
    "error": "error.log",
    "server": "server.log",
}


@router.get("/errors", response_model=list[dict])
async def list_errors(limit: int = Query(default=20, ge=1, le=100), request: Request = None):
    state = request.app.state
    error_repo = state.error_repo
    errors = await asyncio.to_thread(error_repo.get_recent, limit=limit)
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

    raw_lines = await asyncio.to_thread(tail_log_file, target_path, max_lines=lines)

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


@router.delete("/errors/logs", response_model=LogClearResponse)
async def clear_log_files(
    type: Literal["error", "server", "all"] = Query(..., description="Active log file(s) to clear"),
    request: Request = None,
) -> LogClearResponse:
    """Clear active allowlisted log files; rotated archives are preserved.

    Guarded with:
    - Token/Password authentication via the /api parent router
    - Requires AAA_PASSWORD to be configured; clearing is disabled without authentication
    - Strictly allow-listed log targets
    - safe_resolve_path traversal and symlink-target defense
    - Active RotatingFileHandler locks while truncating
    """
    if not auth_enabled():
        raise HTTPException(status_code=503, detail="Log clearing requires AAA_PASSWORD to be configured")

    selected_types = list(ALLOWED_LOG_FILES) if type == "all" else [type]
    config = getattr(request.app.state, "config", {}) if request and hasattr(request, "app") else {}
    log_dir = get_log_dir(config)
    paths: dict[str, Path] = {}

    for log_type in selected_types:
        filename = ALLOWED_LOG_FILES[log_type]
        try:
            target_path = safe_resolve_path(log_dir, filename)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail="Forbidden path resolution") from exc
        if target_path != log_dir / filename:
            raise HTTPException(status_code=403, detail="Log target must not resolve through a symlink")
        paths[log_type] = target_path

    try:
        bytes_cleared = await asyncio.to_thread(clear_active_log_files, paths)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Active log handlers are not available") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Failed to clear active log files") from exc
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Invalid log target configuration") from exc

    return LogClearResponse(
        status="success",
        files=[LogFileClearResult(log_type=name, bytes_cleared=size) for name, size in bytes_cleared.items()],
    )
