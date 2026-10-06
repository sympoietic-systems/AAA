"""Proposal lifecycle boundary; no child execution occurs here."""

import asyncio
from typing import Any

from backend.storage.repositories.research.branch_proposal import ResearchBranchProposalRepository
from backend.storage.research_branch_proposal import BranchProposal, BranchScope


async def resolve_proposal(
    manager: Any,
    task_id: str,
    proposal_id: str,
    decision: str,
    scopes: tuple[BranchScope, ...] | None = None,
    boundary_acknowledged: bool = False,
) -> BranchProposal:
    repo = ResearchBranchProposalRepository(manager.task_repo._db_path)
    proposal = await asyncio.to_thread(
        repo.resolve,
        task_id,
        proposal_id,
        decision,
        scopes=scopes,
        boundary_acknowledged=boundary_acknowledged,
        manual=manager.config.get("manual_mode", False),
    )
    if manager._orchestrator is not None:
        manager._orchestrator._state_mgr.states.pop(task_id, None)
    task = await asyncio.to_thread(manager.task_repo.get, task_id)
    if task and task["status"] == "queued":
        await manager._try_process_queue()
    return proposal
