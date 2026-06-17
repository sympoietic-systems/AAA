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


# ── Orchestrator Step-by-Step ──────────────────────────────────────────

@router.post("/research/tasks/{task_id}/step")
async def execute_step(task_id: str, request: Request):
    """Execute the next orchestrator phase (planning → searching → parsing →
    digesting → reflecting → evaluating → synthesizing → complete).

    Used in manual mode for step-by-step debugging.  Each call advances
    the pipeline by exactly one phase.
    """
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in ("active", "queued"):
        raise HTTPException(
            status_code=400,
            detail=f"Task must be active or queued, got: {task['status']}",
        )

    # If queued and in manual+orchestrator mode, init + run first step
    if task["status"] == "queued":
        orch_config = state.config.get("research_orchestrator", {})
        if orch_config.get("enabled") and manager.config.get("manual_mode", False):
            manager.transition(task_id, "active")
            manager.orchestrator.init_task(task_id)

    try:
        result = await manager.orchestrator_step(task_id)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


# ── Meta Log ──────────────────────────────────────────────────────────

def _parse_event_data(entry: dict) -> dict:
    import json
    try:
        entry["event_data"] = json.loads(entry["event_data"])
    except (json.JSONDecodeError, TypeError):
        entry["event_data"] = {"raw": entry.get("event_data", "")}
    return entry


@router.get("/research/tasks/{task_id}/meta-log")
async def get_task_meta_log(
    task_id: str,
    limit: int = 200,
    branch_id: Optional[str] = None,
    request: Request = None,
):
    """Full activity log for a research task.  Pass ?branch_id=<step_id> to
    filter to a specific orchestrator step.
    """
    state = request.app.state
    meta_repo = getattr(state, "research_meta_log_repo", None)
    if meta_repo is None:
        raise HTTPException(status_code=501, detail="Meta logging not available")

    task = state.research_task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")

    if branch_id:
        entries = meta_repo.get_by_branch(branch_id)
        # Filter further to this task (branch_id may not be globally unique)
        entries = [e for e in entries if e.get("task_id") == task_id]
    else:
        entries = meta_repo.get_by_task(task_id, limit=limit)

    entries = [_parse_event_data(e) for e in entries]

    return {
        "task_id": task_id,
        "title": task.get("title", ""),
        "status": task.get("status", ""),
        "branch_id": branch_id,
        "entries": entries,
        "count": len(entries),
    }


# ── Orchestrator Phase ────────────────────────────────────────────────

@router.get("/research/tasks/{task_id}/phase")
async def get_task_phase(task_id: str, request: Request = None):
    """Return the current orchestrator phase for a task (manual step-by-step mode)."""
    state = request.app.state
    manager = state.research_task_manager
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    phase = manager.orchestrator.get_task_phase(task_id)
    return {"task_id": task_id, "phase": phase or "not_started"}


# ── Step Input Preview (inspect before running) ────────────────────────

@router.get("/research/tasks/{task_id}/preview/{phase}")
async def preview_step_inputs(task_id: str, phase: str, request: Request = None):
    """Return the prompts/inputs that WOULD be used for a given phase,
    without executing it.  Useful for inspecting before clicking 'Run'.

    Supported phases: planning (full system + user prompts), searching.
    """
    state = request.app.state
    manager = state.research_task_manager
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        result = await manager.orchestrator.preview_step_inputs(task_id, phase)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


# ── Orchestrator Steps ────────────────────────────────────────────────

@router.get("/research/tasks/{task_id}/steps")
async def get_task_steps(task_id: str, request: Request = None):
    """Orchestrator pipeline steps — plan, search, parse, digest, reflect, evaluate."""
    state = request.app.state
    step_repo = getattr(state, "research_step_repo", None)
    result_repo = getattr(state, "research_step_result_repo", None)
    plan_repo = getattr(state, "research_plan_repo", None)

    # Get the plan
    plan = None
    if plan_repo:
        plan = plan_repo.get_by_task(task_id)

    # Get all steps
    steps = []
    if step_repo:
        steps = step_repo.get_by_task(task_id)

    # Get all step results
    all_results = []
    if result_repo:
        all_results = result_repo.get_by_task(task_id)

    # Group results by step_id
    results_by_step: dict = {}
    for r in all_results:
        sid = r.get("step_id", "")
        if sid not in results_by_step:
            results_by_step[sid] = []
        results_by_step[sid].append({
            "id": r.get("id"),
            "source_url": r.get("source_url"),
            "source_title": r.get("source_title"),
            "analyzed_json": r.get("analyzed_json"),
            "relevance_score": r.get("relevance_score"),
            "novelty_score": r.get("novelty_score"),
            "raw_file_path": r.get("raw_file_path"),
        })

    return {
        "task_id": task_id,
        "plan": plan,
        "steps": steps,
        "results_by_step": results_by_step,
    }
