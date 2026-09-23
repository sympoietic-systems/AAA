"""Research task management endpoints — creation, listing, approval, control."""

import contextlib
import json
import logging

from fastapi import APIRouter, HTTPException, Request

from backend.api.routes.research.schemas import (
    ApproveProposalPayload,
    ContinuePayload,
    ContinueTaskPayload,
    DispatchPayload,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────


def _extract_depth(task: dict) -> int:

    try:
        orch_raw = task.get("orchestrator_state")
        if orch_raw:
            orch = json.loads(orch_raw) if isinstance(orch_raw, str) else orch_raw
            d = orch.get("current_depth", 0)
            if d:
                return int(d)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return task.get("max_depth", 0)


@router.post("/research/dispatch")
async def dispatch_research(payload: DispatchPayload, request: Request):
    """User dispatches a research task from conversation or console.

    User-initiated tasks are auto-approved (no proposal gate).
    Creates a research_task with status=approved, then queues it.
    """
    state = request.app.state
    manager = state.research_task_manager

    task_id = manager.create_task(
        objective=payload.objective,
        trigger_source="user_console" if not payload.conversation_id else "user_inline",
        title=payload.title or payload.objective[:80],
        conversation_id=payload.conversation_id,
        status="approved",
        max_depth=payload.max_depth,
        max_breadth=payload.max_breadth,
        is_agonistic=payload.is_agonistic,
        budget_limit_usd=payload.budget_limit_usd,
        previous_context=payload.previous_context,
        continue_from_task_id=payload.continue_from_task_id,
        inject_file_id=payload.inject_file_id,
        inject_conversation_id=payload.inject_conversation_id,
        document_mode=payload.document_mode,
        document_chunk_limit=payload.document_chunk_limit,
        injected_documents=[d.model_dump() for d in payload.injected_documents] if payload.injected_documents else None,
    )

    manager.queue(task_id)

    return {"task_id": task_id, "status": "queued"}


@router.post("/research/continue")
async def continue_research(payload: ContinuePayload, request: Request):
    """Continue a completed/failed/cancelled research task with adjusted parameters.

    Reads the source task's result_summary as previous_context so the new
    planner inherits the prior synthesis. Optionally injects a document
    (from perception_files) for digestion against the objective.
    """
    state = request.app.state
    manager = state.research_task_manager

    source = manager.get_task(payload.source_task_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source task not found")

    previous_context = source.get("result_summary") or ""
    source_depth = source.get("max_depth", 3)
    source_breadth = source.get("max_breadth", 4)
    source_agonistic = bool(source.get("is_agonistic"))
    source_budget = source.get("budget_limit_usd", 0.50)
    source_conv_id = source.get("conversation_id")

    objective = payload.adjusted_objective or source["objective"]
    title = payload.title or source.get("title", objective[:80])
    new_max_depth = source_depth + payload.additional_cycles
    new_breadth = payload.max_breadth or source_breadth
    is_agonistic = payload.is_agonistic if payload.is_agonistic is not None else source_agonistic
    budget = payload.budget_limit_usd or source_budget
    new_conv_id = payload.conversation_id or source_conv_id

    task_id = manager.create_task(
        objective=objective,
        trigger_source=source.get("trigger_source", "user_console"),
        title=title,
        conversation_id=new_conv_id,
        status="approved",
        priority=source.get("priority", 2),
        max_depth=new_max_depth,
        max_breadth=new_breadth,
        is_agonistic=is_agonistic,
        budget_limit_usd=budget,
        previous_context=previous_context,
        continue_from_task_id=payload.source_task_id,
        inject_file_id=payload.inject_file_id,
        inject_conversation_id=payload.inject_conversation_id,
        document_mode=payload.document_mode,
        document_chunk_limit=payload.document_chunk_limit,
    )

    manager.queue(task_id)

    return {
        "task_id": task_id,
        "status": "queued",
        "continued_from": payload.source_task_id,
        "max_depth": new_max_depth,
    }


@router.post("/research/{task_id}/continue")
async def continue_task(task_id: str, payload: ContinueTaskPayload, request: Request):
    """Continue a completed/failed/cancelled research task in-place.

    Does NOT create a new task. Bumps max_depth, resets phase to planning,
    injects prior synthesis as planner context, and re-queues the task.
    Optionally injects a document for digestion.
    """
    state = request.app.state
    manager = state.research_task_manager

    manager.continue_task(
        task_id=task_id,
        additional_cycles=payload.additional_cycles,
        adjusted_objective=payload.adjusted_objective or "",
        inject_file_id=payload.inject_file_id or "",
        inject_conversation_id=payload.inject_conversation_id or "",
        document_mode=payload.document_mode or "",
        document_chunk_limit=payload.document_chunk_limit or 5,
        budget_limit_usd=payload.budget_limit_usd or 0.0,
    )

    task = manager.get_task(task_id)
    return {
        "task_id": task_id,
        "status": task["status"] if task else "queued",
        "max_depth": task["max_depth"] if task else 0,
    }


@router.get("/research/files")
async def list_research_files(conversation_id: str | None = None, request: Request = None):
    """List indexed perception_files available for document injection.

    Returns file metadata (name, type, summary, status, token_count, chunk_count)
    along with the conversation_id each file belongs to.
    Optionally filtered by conversation_id.
    """
    state = request.app.state
    perception_repo = getattr(state, "perception_repo", None)
    if not perception_repo:
        return {"files": [], "count": 0}

    if conversation_id:
        files = perception_repo.get_files_by_conversation(conversation_id)
    else:
        files = perception_repo.get_all_files_across_conversations()

    result = [
        {
            "file_name": f["file_name"],
            "file_type": f.get("file_type", ""),
            "status": f.get("status", ""),
            "summary": f.get("summary"),
            "token_count": f.get("token_count", 0),
            "chunk_count": f.get("chunk_count", 0),
            "conversation_id": f.get("conversation_id", ""),
        }
        for f in files
        if f.get("status") == "ready"
    ]

    return {"files": result, "count": len(result)}


@router.get("/research/tasks")
async def list_tasks(
    status: str | None = None,
    trigger_source: str | None = None,
    conversation_id: str | None = None,
    limit: int = 50,
    request: Request = None,
):
    """List all research tasks with optional filters. Includes lightweight asset summaries."""
    state = request.app.state
    manager = state.research_task_manager
    tasks = manager.list_tasks(
        status=status,
        trigger_source=trigger_source,
        conversation_id=conversation_id,
        limit=limit,
    )

    # Enrich tasks with lightweight asset summaries (no raw_markdown)
    task_ids = [t["id"] for t in tasks]
    if task_ids:
        assets_by_task = state.scraped_asset_repo.get_lightweight_by_task_ids(task_ids)
        for task in tasks:
            tid = task["id"]
            task_assets = assets_by_task.get(tid, [])
            task["assets"] = task_assets
            task["asset_count"] = len(task_assets)

    return tasks


@router.get("/research/tasks/active/summary")
async def get_active_summary(request: Request):
    """Lightweight poll endpoint for frontend status indicators."""
    state = request.app.state
    manager = state.research_task_manager
    return manager.get_active_summary()


@router.get("/research/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    """Detail for a single task: metadata + branches + assets summary."""
    state = request.app.state
    manager = state.research_task_manager
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")

    # Enrich with branches and assets
    branches = state.research_branch_repo.get_by_task(task_id)
    assets = state.scraped_asset_repo.get_by_task(task_id)
    task["branches"] = branches
    task["asset_count"] = len(assets)
    task["assets"] = [
        {
            "id": a["id"],
            "url": a.get("url", ""),
            "relevance_score": a.get("relevance_score", 0),
            "novelty_score": a.get("novelty_score", 0),
            "diffractive_score": a.get("diffractive_score", 0),
            "created_at": a.get("created_at"),
        }
        for a in assets
    ]
    return task


# ── Proposal Actions ──────────────────────────────────────────────────


@router.post("/research/proposals/{task_id}/approve")
async def approve_proposal(task_id: str, request: Request, payload: ApproveProposalPayload | None = None):
    """User approves a Symbia-generated research proposal."""
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        if payload and payload.objective:
            manager.create_task(
                task_id=task_id,
                objective=payload.objective,
                trigger_source="symbia_conversation",
                title=payload.title or payload.objective[:80],
                conversation_id=payload.conversation_id,
                status="approved",
                priority=3,
                max_depth=payload.max_depth,
                max_breadth=payload.max_breadth,
                is_agonistic=payload.is_agonistic,
                budget_limit_usd=0.50,
                proposal_rationale=payload.rationale,
            )
            manager.queue(task_id)
            return {"task_id": task_id, "status": "queued"}
        raise HTTPException(status_code=404, detail="Proposal not found")

    if task["status"] in ("approved", "queued", "active", "completed"):
        return {"task_id": task_id, "status": task["status"]}

    if task["status"] != "proposed":
        raise HTTPException(status_code=400, detail=f"Task is in {task['status']} state, not proposed")

    manager.approve(task_id)
    manager.queue(task_id)

    return {"task_id": task_id, "status": "queued"}


@router.post("/research/proposals/{task_id}/reject")
async def reject_proposal(task_id: str, request: Request):
    """User rejects a Symbia-generated research proposal."""
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        return {"task_id": task_id, "status": "rejected"}
    if task["status"] == "rejected":
        return {"task_id": task_id, "status": "rejected"}
    if task["status"] != "proposed":
        raise HTTPException(status_code=400, detail=f"Task is in {task['status']} state, not proposed")

    manager.reject(task_id)
    return {"task_id": task_id, "status": "rejected"}


# ── Task Control ──────────────────────────────────────────────────────


@router.post("/research/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, request: Request):
    """Cancel a queued or active task."""
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] in ("completed", "failed", "cancelled", "rejected", "expired"):
        raise HTTPException(status_code=400, detail="Task is already terminal")

    manager.cancel(task_id)
    return {"task_id": task_id, "status": "cancelled"}


@router.delete("/research/tasks/{task_id}")
async def delete_task(task_id: str, request: Request):
    """Delete a research task and all associated data permanently."""
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # CASCADE deletes branches, assets, plans, steps, step results, meta log
    manager.delete(task_id)
    return {"task_id": task_id, "deleted": True}


@router.post("/research/tasks/{task_id}/retry")
async def retry_task(task_id: str, request: Request):
    """Retry a failed or completed task with same parameters."""
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in ("failed", "completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Only failed, completed, or cancelled tasks can be retried")

    # Create a new task with same parameters
    new_id = manager.create_task(
        objective=task["objective"],
        trigger_source=task["trigger_source"],
        title=task["title"],
        conversation_id=task.get("conversation_id"),
        status="approved",
        priority=task["priority"],
        max_depth=task["max_depth"],
        max_breadth=task["max_breadth"],
        is_agonistic=bool(task["is_agonistic"]),
        budget_limit_usd=task["budget_limit_usd"],
    )

    manager.queue(new_id)
    return {"task_id": new_id, "status": "queued", "retried_from": task_id}


# ── Manual Execution (debug / manual mode) ────────────────────────────


@router.post("/research/tasks/{task_id}/run")
async def run_task(task_id: str, request: Request):
    """Manually trigger execution of a queued task. Used in manual mode."""
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "queued":
        raise HTTPException(status_code=400, detail=f"Task must be queued to run, got: {task['status']}")

    manager.run_task(task_id)
    return {"task_id": task_id, "status": "active"}


@router.post("/research/tasks/{task_id}/rerun")
async def rerun_task(task_id: str, request: Request):
    """Rerun a terminal task in-place — resets counters, clears old data.

    Same task ID, same parameters. Use for debugging: edit code, rerun to see new results.
    Does NOT clone — old branches/assets are deleted, counters reset to zero.
    """
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Can only rerun terminal tasks, got: {task['status']}")

    manager.rerun_task(task_id)
    is_manual = manager.config.get("manual_mode", False)
    return {
        "task_id": task_id,
        "status": "queued",
        "rerun_count": (task.get("rerun_count") or 0) + 1,
        "auto_run": not is_manual,
    }


# ── Reinitialize ───────────────────────────────────────────────────────


@router.post("/research/tasks/{task_id}/reinitialize")
async def reinitialize_task(task_id: str, request: Request = None):
    """Clear cached phase inputs so next preview/step recomputes from scratch."""
    state = request.app.state
    manager = state.research_task_manager
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    manager.orchestrator.reinitialize(task_id)
    # Also evict the in-memory state so the next execute_step call reloads it fresh from DB
    with contextlib.suppress(Exception):
        manager.orchestrator._state_mgr.states.pop(task_id, None)
    return {"task_id": task_id, "status": "reinitialized"}
