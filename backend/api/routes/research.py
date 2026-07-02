"""Research API endpoints — Autonomous Research Engine.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 4.8 and 5.
"""

from typing import Any, Optional
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
    previous_context: Optional[str] = None
    continue_from_task_id: Optional[str] = None
    additional_cycles: Optional[int] = None
    inject_file_id: Optional[str] = None
    inject_conversation_id: Optional[str] = None
    document_mode: Optional[str] = None
    document_chunk_limit: Optional[int] = None


class ContinuePayload(BaseModel):
    source_task_id: str
    adjusted_objective: Optional[str] = None
    title: Optional[str] = None
    conversation_id: Optional[str] = None
    additional_cycles: int = 1
    inject_file_id: Optional[str] = None
    inject_conversation_id: Optional[str] = None
    document_mode: Optional[str] = None
    document_chunk_limit: Optional[int] = None
    budget_limit_usd: Optional[float] = None
    max_breadth: Optional[int] = None
    is_agonistic: Optional[bool] = None


class ContinueTaskPayload(BaseModel):
    adjusted_objective: Optional[str] = None
    additional_cycles: int = 1
    inject_file_id: Optional[str] = None
    inject_conversation_id: Optional[str] = None
    document_mode: Optional[str] = None
    document_chunk_limit: Optional[int] = None
    budget_limit_usd: Optional[float] = None


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
        previous_context=payload.previous_context,
        continue_from_task_id=payload.continue_from_task_id,
        inject_file_id=payload.inject_file_id,
        inject_conversation_id=payload.inject_conversation_id,
        document_mode=payload.document_mode,
        document_chunk_limit=payload.document_chunk_limit,
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
async def list_research_files(conversation_id: Optional[str] = None, request: Request = None):
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

    result = [{
        "file_name": f["file_name"],
        "file_type": f.get("file_type", ""),
        "status": f.get("status", ""),
        "summary": f.get("summary"),
        "token_count": f.get("token_count", 0),
        "chunk_count": f.get("chunk_count", 0),
        "conversation_id": f.get("conversation_id", ""),
    } for f in files if f.get("status") == "ready"]

    return {"files": result, "count": len(result)}


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
async def execute_step(
    task_id: str,
    request: Request,
    rerun_step_type: Optional[str] = None,
    rerun_step_id: Optional[str] = None,
):
    """Execute the next orchestrator phase (planning → searching → parsing →
    digesting → consolidating → reflection → evaluating → synthesizing → complete).

    If rerun_step_type is provided (e.g., 'digest'), the existing DB state
    is preserved and only that single phase is re-executed (per-step rerun).
    """
    state = request.app.state
    manager = state.research_task_manager

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in ("active", "queued", "completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Task must be active, queued, completed, or failed, got: {task['status']}",
        )

    # Map step_type to orchestrator phase for rerun-to-target
    STEP_TYPE_TO_PHASE: dict[str, str] = {
        "plan": "planning", "search": "searching", "parallel_parse": "parsing",
        "digest": "digesting", "document_digestion": "document_digestion",
        "reflect": "consolidating", "reflection": "reflection", "evaluate": "evaluating",
        "synthesize": "synthesizing",
    }
    target_phase = STEP_TYPE_TO_PHASE.get(rerun_step_type or "")

    if target_phase:
        # Per-step rerun — resume state, set phase, mark step for in-place update.
        # Downstream steps are deleted by execute_step before re-execution.
        if task["status"] in ("completed", "failed"):
            manager.task_repo.update(task_id, status="active")
        orch = manager.orchestrator
        orch.ensure_state(task_id)
        orch.set_phase(task_id, target_phase)

        # Find the exact step to update in-place
        step_repo = getattr(state, "research_step_repo", None)
        if step_repo and rerun_step_type:
            if rerun_step_id:
                existing = step_repo.get(rerun_step_id)
            else:
                all_steps = step_repo.get_by_task(task_id)
                matching = [s for s in all_steps
                            if s["step_type"] == rerun_step_type and s["status"] == "completed"]
                existing = matching[-1] if matching else None
            if existing:
                s2 = orch._state_mgr._states.get(task_id)
                if s2 is not None:
                    s2["_rerun_step_id"] = existing["id"]
                    # Reset digest-related flags so document_digestion re-runs fresh
                    if rerun_step_type == "document_digestion":
                        s2["document_digested"] = False
                        s2["document_learnings"] = []
                    # Set query_index from the step's query_group
                    qg = existing.get("query_group")
                    if qg and rerun_step_type in ("search", "parallel_parse", "digest"):
                        s2["query_index"] = qg - 1  # query_group is 1-based, query_index is 0-based
                    elif rerun_step_type in ("search", "parallel_parse", "digest"):
                        # Fallback: count searches before this step
                        all_steps = step_repo.get_by_task(task_id)
                        s2["query_index"] = sum(
                            1 for s in all_steps
                            if s["step_type"] == "search" and s["step_number"] < existing["step_number"]
                        )
    else:
        # Normal sequential step execution
        if task["status"] in ("completed", "failed"):
            # Check if the orchestrator state has an unfinished phase we can resume
            # (e.g. synthesizing was never run because the task was incorrectly marked complete).
            # In that case, just resume the existing state rather than wiping all research data.
            orch = manager.orchestrator
            try:
                existing_phase = orch.get_task_phase(task_id)
            except Exception:
                existing_phase = None
            if existing_phase and existing_phase not in ("complete", ""):
                # Task marked completed but still has work to do — resume it
                manager.task_repo.update(task_id, status="active")
                orch.ensure_state(task_id)  # already loaded, no-op
            else:
                manager.rerun_task(task_id)
                task = manager.get_task(task_id)  # refresh after rerun
                manager.transition(task_id, "active")
                manager.orchestrator.init_task(task_id)
        elif task["status"] == "queued":
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
    step_id: Optional[str] = None,
    request: Request = None,
):
    """Full activity log for a research task.  Pass ?step_id=<step_id> to
    filter to a specific orchestrator step.
    """
    state = request.app.state
    meta_repo = getattr(state, "research_meta_log_repo", None)
    if meta_repo is None:
        raise HTTPException(status_code=501, detail="Meta logging not available")

    task = state.research_task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")

    if step_id:
        entries = meta_repo.get_by_step(step_id)
    elif branch_id:
        entries = meta_repo.get_by_branch(branch_id)
        entries = [e for e in entries if e.get("task_id") == task_id]
    else:
        entries = meta_repo.get_by_task(task_id, limit=limit)

    entries = [_parse_event_data(e) for e in entries]

    return {
        "task_id": task_id,
        "title": task.get("title", ""),
        "status": task.get("status", ""),
        "branch_id": branch_id,
        "step_id": step_id,
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
    try:
        manager.orchestrator._state_mgr.states.pop(task_id, None)
    except Exception:
        pass
    return {"task_id": task_id, "status": "reinitialized"}


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
        raw_content = r.get("raw_content") or ""
        error_msg = raw_content if raw_content.startswith("Error:") else None
        content_preview = raw_content[:1000] if (raw_content and not error_msg) else ""
        results_by_step[sid].append({
            "id": r.get("id"),
            "source_url": r.get("source_url"),
            "source_title": r.get("source_title"),
            "analyzed_json": r.get("analyzed_json"),
            "relevance_score": r.get("relevance_score"),
            "novelty_score": r.get("novelty_score"),
            "raw_file_path": r.get("raw_file_path"),
            "error": error_msg,
            "content_preview": content_preview,
        })

    # Retrieve current depth from orchestrator state
    current_depth = 0
    if hasattr(state, "research_task_manager"):
        task = state.research_task_manager.get_task(task_id)
        if task:
            orch_state_raw = task.get("orchestrator_state")
            if orch_state_raw:
                try:
                    import json
                    state_dict = json.loads(orch_state_raw) if isinstance(orch_state_raw, str) else orch_state_raw
                    if isinstance(state_dict, dict):
                        current_depth = state_dict.get("current_depth", 0)
                except Exception:
                    pass

    return {
        "task_id": task_id,
        "plan": plan,
        "steps": steps,
        "results_by_step": results_by_step,
        "current_depth": current_depth,
    }


# ── Research Notes ─────────────────────────────────────────────────────

@router.get("/research/tasks/{task_id}/notes")
async def get_task_notes(task_id: str, request: Request = None):
    state = request.app.state
    note_repo = getattr(state, "note_repo", None)
    if not note_repo:
        raise HTTPException(status_code=503, detail="Note repository not available")

    task = state.research_task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")

    from backend.services.note import NoteService
    notes = NoteService.list_by_asset(note_repo, "research_task", task_id)
    from backend.api.schemas import NoteResponse
    return [NoteResponse(**n) for n in notes]


@router.get("/research/tasks/{task_id}/notes/unified")
async def get_task_unified_notes(task_id: str, request: Request = None):
    state = request.app.state
    note_repo = getattr(state, "note_repo", None)
    if not note_repo:
        raise HTTPException(status_code=503, detail="Note repository not available")

    task = state.research_task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")

    from backend.services.note import NoteService
    from backend.api.schemas import UnifiedNoteResponse
    notes = NoteService.list_by_task_with_steps(note_repo, task_id)
    return [UnifiedNoteResponse(**n) for n in notes]


# ── Research Export ────────────────────────────────────────────────────

@router.get("/research/tasks/{task_id}/export")
async def export_research_task(task_id: str, request: Request):
    from fastapi.responses import PlainTextResponse

    state = request.app.state
    manager = state.research_task_manager
    note_repo = getattr(state, "note_repo", None)
    branch_repo = getattr(state, "research_branch_repo", None)
    asset_repo = getattr(state, "scraped_asset_repo", None)
    step_repo = getattr(state, "research_step_repo", None)
    result_repo = getattr(state, "research_step_result_repo", None)
    plan_repo = getattr(state, "research_plan_repo", None)

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")

    branches = branch_repo.get_by_task(task_id) if branch_repo else []
    assets = asset_repo.get_by_task(task_id) if asset_repo else []
    steps = step_repo.get_by_task(task_id) if step_repo else []
    plan = plan_repo.get_by_task(task_id) if plan_repo else None
    notes = note_repo.get_notes_by_task(task_id) if note_repo else []

    all_results = result_repo.get_by_task(task_id) if result_repo else []
    results_by_step: dict = {}
    for r in all_results:
        sid = r.get("step_id", "")
        if sid not in results_by_step:
            results_by_step[sid] = []
        results_by_step[sid].append(r)

    from backend.services.export import ExportService

    markdown = ExportService.build_research_export(
        task=task,
        branches=branches,
        assets=assets,
        steps=steps,
        plan=plan,
        results_by_step=results_by_step,
        notes=notes,
    )

    safe_title = (task.get("title") or "research").strip().replace(" ", "_").replace("/", "_")[:80]
    filename = f"research_{safe_title}_{task_id[:8]}.md"

    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/research/tasks/{task_id}/export/stages")
async def export_research_stages(task_id: str, request: Request):
    """Export all research stages and findings as a clean markdown file,
    organized by cycle. Excludes raw source materials — only source links and names.
    """
    from fastapi.responses import PlainTextResponse

    state = request.app.state
    manager = state.research_task_manager
    note_repo = getattr(state, "note_repo", None)
    step_repo = getattr(state, "research_step_repo", None)
    result_repo = getattr(state, "research_step_result_repo", None)
    plan_repo = getattr(state, "research_plan_repo", None)

    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")

    steps = step_repo.get_by_task(task_id) if step_repo else []
    step_results = result_repo.get_by_task(task_id) if result_repo else []
    plan = plan_repo.get_by_task(task_id) if plan_repo else None
    notes = note_repo.get_notes_by_task(task_id) if note_repo else []

    from backend.services.export import ExportService

    markdown = ExportService.build_research_stages_export(
        task=task,
        steps=steps,
        step_results=step_results,
        plan=plan,
        notes=notes,
    )

    safe_title = (task.get("title") or "research").strip().replace(" ", "_").replace("/", "_")[:80]
    filename = f"research_stages_{safe_title}_{task_id[:8]}.md"

    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/research/tasks/{task_id}/export/json")
async def export_research_task_json(task_id: str, request: Request):
    """Export a single research task and all its children as structured JSON for re-import."""
    state = request.app.state
    payload = _build_task_export(task_id, state)
    if payload is None:
        raise HTTPException(status_code=404, detail="Research task not found")
    return payload


@router.get("/research/export/all")
async def export_all_research_tasks(
    request: Request,
    status: Optional[str] = None,
    limit: Optional[int] = None,
):
    """Export all research tasks (optionally filtered by status) as a JSON array.

    Each element in the returned array is a complete task export suitable for
    re-import via POST /api/research/import.
    """
    state = request.app.state
    manager = state.research_task_manager

    tasks = manager.list_tasks(status=status, limit=limit or 10000)

    exports = []
    for task in tasks:
        tid = task["id"]
        export = _build_task_export(tid, state)
        if export:
            exports.append(export)

    return {
        "tasks": exports,
        "count": len(exports),
    }


def _build_task_export(task_id: str, state: Any) -> dict | None:
    """Build a JSON export for a single task. Returns None if task not found."""
    manager = state.research_task_manager
    note_repo = getattr(state, "note_repo", None)
    branch_repo = getattr(state, "research_branch_repo", None)
    asset_repo = getattr(state, "scraped_asset_repo", None)
    step_repo = getattr(state, "research_step_repo", None)
    result_repo = getattr(state, "research_step_result_repo", None)
    plan_repo = getattr(state, "research_plan_repo", None)
    meta_repo = getattr(state, "research_meta_log_repo", None)

    task = manager.get_task(task_id)
    if not task:
        return None

    from backend.services.export import ExportService

    return ExportService.build_research_export_json(
        task=task,
        branches=branch_repo.get_by_task(task_id) if branch_repo else [],
        assets=asset_repo.get_by_task(task_id) if asset_repo else [],
        steps=step_repo.get_by_task(task_id) if step_repo else [],
        plan=plan_repo.get_by_task(task_id) if plan_repo else None,
        step_results=result_repo.get_by_task(task_id) if result_repo else [],
        notes=note_repo.get_notes_by_task_with_steps(task_id) if note_repo else [],
        meta_log=meta_repo.get_by_task(task_id) if meta_repo else [],
    )


@router.post("/research/import")
async def import_research_task(payload: dict[str, Any], request: Request):
    """Import research tasks from a JSON export payload.

    Accepts either:
      - Single task: {"task": {...}, "branches": [...], ...}
      - Bulk export: {"tasks": [{"task": {...}, ...}, ...]}

    Generates fresh UUIDs for all records.
    Remaps internal foreign keys and nullifies external references
    (conversation_id, message_id, memory_node_id).
    """
    from backend.services.research.import_service import import_research_task

    state = request.app.state
    required_repos = [
        "research_task_repo",
        "research_branch_repo",
        "scraped_asset_repo",
        "research_plan_repo",
        "research_step_repo",
        "research_step_result_repo",
        "research_meta_log_repo",
    ]
    missing = [r for r in required_repos if not hasattr(state, r)]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Repositories not available: {', '.join(missing)}",
        )

    task_entries = payload.get("tasks")
    if task_entries and isinstance(task_entries, list):
        results = []
        for entry in task_entries:
            result = import_research_task(entry, state)
            results.append(result.to_dict())
        return {"imported": True, "count": len(results), "results": results}

    result = import_research_task(payload, state)
    if not result.imported:
        raise HTTPException(status_code=400, detail=result.to_dict())

    return result.to_dict()
