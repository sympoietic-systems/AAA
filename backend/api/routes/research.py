"""Research API endpoints — Autonomous Research Engine.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 4.8 and 5.
"""

from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


class DispatchPayload(BaseModel):
    objective: str
    title: Optional[str] = None
    conversation_id: Optional[str] = None
    max_depth: int = 3
    max_breadth: int = 4
    is_agonistic: bool = False
    budget_limit_usd: float = 0.50


# ── Task CRUD ─────────────────────────────────────────────────────────

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
    )

    manager.queue(task_id)

    return {"task_id": task_id, "status": "queued"}


@router.get("/research/tasks")
async def list_tasks(
    status: Optional[str] = None,
    trigger_source: Optional[str] = None,
    conversation_id: Optional[str] = None,
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
    task["assets"] = [{
        "id": a["id"],
        "url": a.get("url", ""),
        "relevance_score": a.get("relevance_score", 0),
        "novelty_score": a.get("novelty_score", 0),
        "diffractive_score": a.get("diffractive_score", 0),
        "created_at": a.get("created_at"),
    } for a in assets]
    return task


# ── Proposal Actions ──────────────────────────────────────────────────

@router.post("/research/proposals/{task_id}/approve")
async def approve_proposal(task_id: str, request: Request):
    """User approves a Symbia-generated research proposal."""
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if task["status"] != "proposed":
        raise HTTPException(status_code=400, detail="Task is not in proposed state")

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
        raise HTTPException(status_code=404, detail="Proposal not found")
    if task["status"] != "proposed":
        raise HTTPException(status_code=400, detail="Task is not in proposed state")

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


@router.post("/research/tasks/{task_id}/retry")
async def retry_task(task_id: str, request: Request):
    """Retry a failed or completed task with same parameters."""
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in ("failed", "completed"):
        raise HTTPException(status_code=400, detail="Only failed or completed tasks can be retried")

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


# ── Meta Log ──────────────────────────────────────────────────────────

@router.get("/research/tasks/{task_id}/meta-log")
async def get_task_meta_log(task_id: str, limit: int = 200, request: Request = None):
    """Full activity log for a research task — fetches, prompts, decisions, errors."""
    state = request.app.state
    meta_repo = getattr(state, "research_meta_log_repo", None)
    if meta_repo is None:
        raise HTTPException(status_code=501, detail="Meta logging not available")

    task = state.research_task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")

    entries = meta_repo.get_by_task(task_id, limit=limit)
    # Parse JSON event_data for each entry
    import json
    for entry in entries:
        try:
            entry["event_data"] = json.loads(entry["event_data"])
        except (json.JSONDecodeError, TypeError):
            entry["event_data"] = {"raw": entry.get("event_data", "")}

    return {
        "task_id": task_id,
        "title": task.get("title", ""),
        "status": task.get("status", ""),
        "entries": entries,
        "count": len(entries),
    }
