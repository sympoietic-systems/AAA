from fastapi import APIRouter, Request

from backend.api.schemas import SkillsResponse
from backend.services.skill import SkillService

router = APIRouter()


@router.get("/skills", response_model=SkillsResponse)
async def get_skills(request: Request):
    return SkillService.get_skills(request.app.state)
