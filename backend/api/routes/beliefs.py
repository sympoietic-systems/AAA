from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.services.belief import BeliefService

router = APIRouter()


class VetProposalRequest(BaseModel):
    action: str  # "adopt", "reject", or "merge"
    suggested_label: Optional[str] = None
    suggested_statement: Optional[str] = None
    rejection_rationale: Optional[str] = None
    target_belief_id: Optional[str] = None


class EditStatementRequest(BaseModel):
    statement: str
    change_reason: Optional[str] = None


@router.get("/beliefs")
async def get_beliefs(request: Request, conversation_id: Optional[str] = None, agent_id: str = "symbia"):
    state = request.app.state
    belief_repo = getattr(state, "belief_repo", None)
    if not belief_repo:
        raise HTTPException(status_code=503, detail="Belief repository not initialized")

    service = BeliefService(state)
    return await service.get_beliefs(conversation_id=conversation_id, agent_id=agent_id)


@router.get("/beliefs/proposals")
async def get_proposals(request: Request, agent_id: str = "symbia"):
    state = request.app.state
    service = BeliefService(state)
    return await service.list_proposals(agent_id=agent_id)


@router.get("/beliefs/proposals/{proposal_id}")
async def get_proposal(proposal_id: str, request: Request):
    state = request.app.state
    service = BeliefService(state)
    p = await service.get_proposal(proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return p


@router.post("/beliefs/proposals/{proposal_id}/refine")
async def refine_proposal(proposal_id: str, request: Request):
    state = request.app.state
    service = BeliefService(state)
    res = await service.refine_proposal_sync(proposal_id)
    return res


@router.post("/beliefs/proposals/{proposal_id}/vet")
async def vet_proposal(proposal_id: str, payload: VetProposalRequest, request: Request):
    state = request.app.state
    service = BeliefService(state)
    
    action = payload.action.lower()
    if action == "adopt":
        res = await service.adopt_proposal(
            proposal_id,
            suggested_label=payload.suggested_label,
            suggested_statement=payload.suggested_statement
        )
    elif action == "reject":
        res = await service.reject_proposal(
            proposal_id,
            rationale=payload.rejection_rationale
        )
    elif action == "merge":
        if not payload.target_belief_id:
            raise HTTPException(status_code=400, detail="target_belief_id required for merge action")
        res = await service.merge_proposal(
            proposal_id,
            target_belief_id=payload.target_belief_id
        )
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
        
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
        
    return res


@router.put("/beliefs/{belief_id}/statement")
async def edit_belief_statement(belief_id: str, payload: EditStatementRequest, request: Request):
    state = request.app.state
    service = BeliefService(state)
    res = await service.update_belief_statement(
        belief_id,
        statement=payload.statement,
        change_reason=payload.change_reason
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res


@router.get("/beliefs/{belief_id}/versions")
async def get_belief_versions(belief_id: str, request: Request):
    state = request.app.state
    service = BeliefService(state)
    return await service.get_statement_versions(belief_id)
