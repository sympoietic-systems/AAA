"""Daily consolidation API routes — thin controller delegating to DailySummaryService."""

import logging

from fastapi import APIRouter, Depends, Request

from backend.api.deps import get_app_state
from backend.services.daily_summary import DailySummaryService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/agent/daily/index")
async def get_daily_index(state=Depends(get_app_state)):
    """Return a list of dates that have activity (conversations, nodes, evolution, summaries)."""
    service = DailySummaryService(state)
    return await service.get_daily_index()


@router.get("/agent/daily/{date_str}")
async def get_daily_details(date_str: str, state=Depends(get_app_state)):
    """Return aggregated activity details for a specific YYYY-MM-DD date."""
    service = DailySummaryService(state)
    return await service.get_daily_details(date_str)


@router.post("/agent/daily/{date_str}/summarize")
async def generate_daily_summary(date_str: str, request: Request, state=Depends(get_app_state)):
    """Generate (or re-generate) narrative daily summary via LLM and cache in SQLite."""
    service = DailySummaryService(state)
    return await service.generate_summary(date_str)
