"""Review a source-backed proposal within its immutable parent boundary."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from backend.services.research.api import run_research_sync
from backend.services.research.branch_review import resolve_proposal
from backend.storage.repositories.research.action_receipt import ReceiptConflictError
from backend.storage.repositories.research.branch_proposal import ResearchBranchProposalRepository
from backend.storage.research_branch_proposal import BranchProposal, BranchScope

router = APIRouter()


class BranchApprovalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scopes: tuple[BranchScope, ...] | None = Field(default=None, min_length=2, max_length=2)
    boundary_acknowledged: bool


@router.get("/research/tasks/{task_id}/branch-proposal")
async def get_branch_proposal(task_id: str, request: Request) -> dict[str, Any] | None:
    manager = request.app.state.research_task_manager
    if not await run_research_sync(manager.task_repo.get, task_id):
        raise HTTPException(status_code=404, detail="Research task not found")
    proposal = await run_research_sync(ResearchBranchProposalRepository(manager.task_repo._db_path).current, task_id)
    if proposal is None:
        return None
    from backend.storage.repositories.research.evidence import ResearchEvidenceRepository

    def details() -> dict[str, Any]:
        repo = ResearchEvidenceRepository(manager.task_repo._db_path)
        witnesses = []
        for segment_id in proposal.draft.witness_segment_ids:
            source, segment = repo.resolve(task_id, segment_id)
            witnesses.append(
                {
                    "segment_id": segment_id,
                    "text": segment.text,
                    "source_url": source.canonical_url,
                    "source_version": source.source_version,
                    "representation": segment.representation,
                    "warnings": source.quality.warnings,
                }
            )
        return {**proposal.model_dump(mode="json"), "witnesses": witnesses}

    return await run_research_sync(details)


@router.post("/research/tasks/{task_id}/branch-proposals/{proposal_id}/approve")
async def approve_branch_proposal(
    task_id: str, proposal_id: str, payload: BranchApprovalPayload, request: Request
) -> BranchProposal:
    try:
        return await resolve_proposal(
            request.app.state.research_task_manager,
            task_id,
            proposal_id,
            "approved",
            payload.scopes,
            payload.boundary_acknowledged,
        )
    except ReceiptConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/research/tasks/{task_id}/branch-proposals/{proposal_id}/decline")
async def decline_branch_proposal(task_id: str, proposal_id: str, request: Request) -> BranchProposal:
    try:
        return await resolve_proposal(request.app.state.research_task_manager, task_id, proposal_id, "declined")
    except ReceiptConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
