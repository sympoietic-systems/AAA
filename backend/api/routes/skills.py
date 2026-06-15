from fastapi import APIRouter, Depends, HTTPException, Request
import logging

from backend.api.deps import require_agent_flux, get_skill_service, get_skill_repo, get_belief_repo, get_app_state
from backend.api.exceptions import ServiceException
from backend.api.schemas import (
    DbSkillInfo,
    DbSkillsResponse,
    SkillsResponse,
    SkillUpdateRequest,
    SkillCreateRequest,
    WorkshopActionRequest,
    WorkshopResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/skills", response_model=SkillsResponse)
async def get_skills(request: Request, service=Depends(get_skill_service)):
    result = await service.get_skills()

    return SkillsResponse(
        pipeline=[],
        on_demand=[
            {"name": s["name"], "description": s["description"], "category": "action",
             "always_run": False, "triggers": s.get("trigger_keywords", []),
             "cost": "free", "status": s["lifecycle_stage"] == "crystallized", "children": []}
            for s in result.get("on_demand", [])
        ],
    )


@router.get("/skills/db")
async def get_db_skills(request: Request, service=Depends(get_skill_service)):
    result = await service.get_skills()
    logger.info("GET /skills/db: always_active=%d, on_demand=%d, all=%d",
                len(result.get("always_active", [])),
                len(result.get("on_demand", [])),
                len(result.get("all", [])))
    return result


@router.post("/skills", response_model=DbSkillInfo, dependencies=[Depends(require_agent_flux)])
async def create_skill(body: SkillCreateRequest, service=Depends(get_skill_service)):
    try:
        return await service.create_new_skill(
            name=body.name,
            description=body.description,
            content=body.content,
            always_active=body.always_active,
            trigger_keywords=body.trigger_keywords,
        )
    except ValueError as e:
        raise ServiceException(str(e))


@router.put("/skills/{skill_id}", response_model=DbSkillInfo, dependencies=[Depends(require_agent_flux)])
async def update_skill(skill_id: str, body: SkillUpdateRequest, service=Depends(get_skill_service)):
    try:
        return await service.update_skill_details(
            skill_id=skill_id,
            description=body.description,
            content=body.content,
            trigger_keywords=body.trigger_keywords,
        )
    except ValueError as e:
        raise ServiceException(str(e))


@router.delete("/skills/{skill_id}", dependencies=[Depends(require_agent_flux)])
async def delete_skill(skill_id: str, service=Depends(get_skill_service)):
    try:
        await service.delete_skill(skill_id)
        return {"status": "ok", "message": f"Skill {skill_id} deleted"}
    except ValueError as e:
        raise ServiceException(str(e))


@router.post("/skills/workshop/{action}", response_model=WorkshopResponse)
async def workshop_action(
    action: str,
    body: WorkshopActionRequest,
    skill_repo=Depends(get_skill_repo),
    belief_repo=Depends(get_belief_repo),
):
    valid_actions = {"propose", "revise", "review", "apply", "reject", "load", "list", "inspect"}
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}. Valid: {', '.join(sorted(valid_actions))}")

    from backend.modules.skill_workshop import SkillWorkshopModule

    if not skill_repo:
        raise HTTPException(status_code=503, detail="Skill repository not available")

    workshop = SkillWorkshopModule()
    workshop.set_repos(skill_repo, belief_repo)

    command = {"action": action, **body.model_dump(exclude_none=True)}
    payload = {"skill_workshop_command": command}
    result_payload = await workshop.process(payload)
    result = result_payload.get("skill_workshop_result", {"status": "error", "message": "No result"})

    if result.get("status") == "error":
        raise ServiceException(result.get("message", "Workshop action failed"))

    return result


@router.get("/skills/{skill_id}/versions")
async def get_skill_versions(skill_id: str, skill_repo=Depends(get_skill_repo)):
    if not skill_repo:
        raise HTTPException(status_code=503, detail="Skill repository not available")

    try:
        versions = skill_repo.list_versions(skill_id)
        return {"skill_id": skill_id, "versions": versions}
    except Exception as e:
        raise ServiceException(str(e))


@router.post("/skills/{skill_id}/revert/{version}", dependencies=[Depends(require_agent_flux)])
async def revert_skill_version(
    skill_id: str,
    version: int,
    state=Depends(get_app_state),
    skill_repo=Depends(get_skill_repo),
    service=Depends(get_skill_service),
):
    if not skill_repo:
        raise HTTPException(status_code=503, detail="Skill repository not available")

    version_data = skill_repo.get_version(skill_id, version)
    if not version_data:
        raise HTTPException(status_code=404, detail=f"Version {version} for skill {skill_id} not found")

    content = version_data["content"]
    description = version_data["description"]
    triggers = version_data["trigger_keywords"]

    try:
        updated = await service.update_skill_details(
            skill_id=skill_id,
            description=description,
            content=content,
            trigger_keywords=triggers,
            changelog=f"Reverted to version {version}",
        )
        updated["content"] = content
        return updated
    except Exception as e:
        raise ServiceException(str(e))


@router.get("/skills/events")
async def get_recent_skill_events(request: Request, limit: int = 50, skill_repo=Depends(get_skill_repo)):
    if not skill_repo:
        raise HTTPException(status_code=503, detail="Skill repository not available")
    try:
        events = skill_repo.list_recent_events(limit=limit)
        return events
    except Exception as e:
        raise ServiceException(str(e))
