import asyncio

from fastapi import APIRouter, Request

from backend.api.schemas import HealthResponse
from backend.services.health import HealthService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    return await asyncio.to_thread(HealthService.check, request.app.state)
