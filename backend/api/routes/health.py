import asyncio

from fastapi import APIRouter, Depends, Query, Request

from backend.api.deps import get_message_repo
from backend.api.schemas import HealthResponse, ReleaseReadinessResponse
from backend.services.health import HealthService
from backend.services.release_readiness import build_release_readiness
from backend.storage.repositories import MessageRepository

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    result = await asyncio.to_thread(HealthService.check, request.app.state)
    return HealthResponse.model_validate(result)


@router.get("/release-readiness", response_model=ReleaseReadinessResponse)
async def release_readiness(
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    repo: MessageRepository = Depends(get_message_repo),
) -> ReleaseReadinessResponse:
    """Return bounded runtime and receipt coverage evidence; perform no writes."""
    result = await asyncio.to_thread(
        build_release_readiness,
        request.app.state.config,
        repo.db_path,
        days,
    )
    return ReleaseReadinessResponse.model_validate(result)
