from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from backend.services.belief import BeliefService

router = APIRouter()


@router.get("/beliefs")
async def get_beliefs(request: Request, conversation_id: Optional[str] = None, agent_id: str = "symbia"):
    state = request.app.state
    belief_repo = getattr(state, "belief_repo", None)
    if not belief_repo:
        raise HTTPException(status_code=503, detail="Belief repository not initialized")

    service = BeliefService(state)
    return await service.get_beliefs(conversation_id=conversation_id, agent_id=agent_id)
