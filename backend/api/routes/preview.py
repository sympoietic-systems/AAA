"""Public curated and authenticated live preview endpoints."""

from fastapi import APIRouter, Depends
from starlette.datastructures import State

from backend.api.deps import get_app_state
from backend.services.preview import get_live_preview_line as select_live_preview
from backend.services.preview import get_public_preview_line

router = APIRouter()
live_router = APIRouter()


@router.get("/api/preview/nodes")
async def get_preview_line() -> dict:
    return get_public_preview_line()


@live_router.get("/preview/live")
async def get_live_preview_line(state: State = Depends(get_app_state)) -> dict:
    return await select_live_preview(state)
