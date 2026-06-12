from fastapi import APIRouter, HTTPException, Request
import logging

from backend.api.schemas import (
    DbSkillInfo,
    DbSkillsResponse,
    SkillsResponse,
    SkillUpdateRequest,
    SkillCreateRequest,
    WorkshopActionRequest,
    WorkshopResponse,
)
from backend.services.skill import SkillService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/skills", response_model=SkillsResponse)
async def get_skills(request: Request):
    service = SkillService(request.app.state)
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
async def get_db_skills(request: Request):
    service = SkillService(request.app.state)
    result = await service.get_skills()
    logger.info("GET /skills/db: always_active=%d, on_demand=%d, all=%d",
                len(result.get("always_active", [])),
                len(result.get("on_demand", [])),
                len(result.get("all", [])))
    return result


def check_agent_flux():
    import os
    if not os.environ.get("AAA_AGENT_FLUX", "false").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=403, detail="Skill modification is disabled (AAA_AGENT_FLUX is false)")


@router.post("/skills", response_model=DbSkillInfo)
async def create_skill(body: SkillCreateRequest, request: Request):
    check_agent_flux()
    service = SkillService(request.app.state)
    try:
        result = await service.create_new_skill(
            name=body.name,
            description=body.description,
            content=body.content,
            always_active=body.always_active,
            trigger_keywords=body.trigger_keywords
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/skills/{skill_id}", response_model=DbSkillInfo)
async def update_skill(skill_id: str, body: SkillUpdateRequest, request: Request):
    check_agent_flux()
    service = SkillService(request.app.state)
    try:
        result = await service.update_skill_details(
            skill_id=skill_id,
            description=body.description,
            content=body.content,
            trigger_keywords=body.trigger_keywords
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str, request: Request):
    check_agent_flux()
    service = SkillService(request.app.state)
    try:
        await service.delete_skill(skill_id)
        return {"status": "ok", "message": f"Skill {skill_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/skills/workshop/{action}", response_model=WorkshopResponse)
async def workshop_action(action: str, body: WorkshopActionRequest, request: Request):
    valid_actions = {"propose", "revise", "review", "apply", "reject", "load", "list", "inspect"}
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}. Valid: {', '.join(sorted(valid_actions))}")

    from backend.modules.skill_workshop import SkillWorkshopModule

    state = request.app.state
    skill_repo = getattr(state, "skill_repo", None)
    belief_repo = getattr(state, "belief_repo", None)

    if not skill_repo:
        raise HTTPException(status_code=503, detail="Skill repository not available")

    workshop = SkillWorkshopModule()
    workshop.set_repos(skill_repo, belief_repo)

    command = {"action": action, **body.model_dump(exclude_none=True)}
    payload = {"skill_workshop_command": command}
    result_payload = await workshop.process(payload)
    result = result_payload.get("skill_workshop_result", {"status": "error", "message": "No result"})

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Workshop action failed"))

    return result


@router.get("/skills/{skill_id}/versions")
async def get_skill_versions(skill_id: str, request: Request):
    state = request.app.state
    skill_repo = getattr(state, "skill_repo", None)
    if not skill_repo:
        raise HTTPException(status_code=503, detail="Skill repository not available")

    try:
        versions = skill_repo.list_versions(skill_id)
        return {"skill_id": skill_id, "versions": versions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/skills/{skill_id}/revert/{version}")
async def revert_skill_version(skill_id: str, version: int, request: Request):
    check_agent_flux()
    state = request.app.state
    skill_repo = getattr(state, "skill_repo", None)
    if not skill_repo:
        raise HTTPException(status_code=503, detail="Skill repository not available")

    # Find version history record
    version_data = skill_repo.get_version(skill_id, version)
    if not version_data:
        raise HTTPException(status_code=404, detail=f"Version {version} for skill {skill_id} not found")

    content = version_data["content"]
    description = version_data["description"]
    triggers = version_data["trigger_keywords"]

    # We call update_skill_details on the SkillService (which recalculates the 16D vector and handles versioning)
    service = SkillService(state)
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
        raise HTTPException(status_code=400, detail=str(e))
