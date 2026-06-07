from fastapi import APIRouter, HTTPException, Request

from backend.api.schemas import DbSkillsResponse, SkillsResponse, WorkshopActionRequest, WorkshopResponse
from backend.services.skill import SkillService

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


@router.get("/skills/db", response_model=DbSkillsResponse)
async def get_db_skills(request: Request):
    service = SkillService(request.app.state)
    return await service.get_skills()


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
