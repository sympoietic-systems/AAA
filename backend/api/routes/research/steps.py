"""Research orchestrator steps, meta-log, and phase execution endpoints."""

import json
import logging

from fastapi import APIRouter, HTTPException, Request

from backend.api.routes.research.schemas import (
    KnotResponse,
    KnotsResponse,
    MemoryNodeResponse,
    MemoryNodesResponse,
)
from backend.api.schemas import UnifiedNoteResponse
from backend.services.note import NoteService

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Orchestrator Step-by-Step ──────────────────────────────────────────


@router.post("/research/tasks/{task_id}/step")
async def execute_step(
    task_id: str,
    request: Request,
    rerun_step_type: str | None = None,
    rerun_step_id: str | None = None,
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
        "plan": "planning",
        "search": "searching",
        "parallel_parse": "parsing",
        "digest": "digesting",
        "document_digestion": "document_digestion",
        "reflect": "consolidating",
        "reflection": "reflection",
        "evaluate": "evaluating",
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
                s2 = orch._state_mgr._states.get(task_id)
                current_depth = s2.get("current_depth", 0) if s2 else 0
                all_steps = step_repo.get_by_task(task_id)
                matching = sorted(
                    (
                        s
                        for s in all_steps
                        if s["step_type"] == rerun_step_type
                        and s["status"] in ("completed", "failed", "running")
                        and orch._get_step_depth(s) == current_depth
                    ),
                    key=lambda s: (
                        s.get("phase_group", s.get("step_number", 0)),
                        s.get("query_group", 0),
                        s.get("sub_sequence", 0),
                    ),
                )
                existing = matching[0] if matching else None
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
                            1
                            for s in all_steps
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
        raise HTTPException(status_code=400, detail=str(e)) from e

    return result


# ── Meta Log ──────────────────────────────────────────────────────────


def _parse_event_data(entry: dict) -> dict:

    try:
        entry["event_data"] = json.loads(entry["event_data"])
    except (json.JSONDecodeError, TypeError):
        entry["event_data"] = {"raw": entry.get("event_data", "")}
    return entry


@router.get("/research/tasks/{task_id}/meta-log")
async def get_task_meta_log(
    task_id: str,
    limit: int = 200,
    branch_id: str | None = None,
    step_id: str | None = None,
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
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
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
        raw_content = r.get("raw_content") or ""
        error_msg = raw_content if raw_content.startswith("Error:") else None
        content_preview = raw_content[:1000] if (raw_content and not error_msg) else ""
        results_by_step[sid].append(
            {
                "id": r.get("id"),
                "source_url": r.get("source_url"),
                "source_title": r.get("source_title"),
                "analyzed_json": r.get("analyzed_json"),
                "relevance_score": r.get("relevance_score"),
                "novelty_score": r.get("novelty_score"),
                "raw_file_path": r.get("raw_file_path"),
                "error": error_msg,
                "content_preview": content_preview,
            }
        )

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

    notes = NoteService.list_by_task_with_steps(note_repo, task_id)
    return [UnifiedNoteResponse(**n) for n in notes]


# ── Memory Nodes & Semantic Knots ─────────────────────────────────────


@router.get("/research/{task_id}/memory-nodes", response_model=MemoryNodesResponse)
async def get_research_memory_nodes(task_id: str, request: Request):
    state = request.app.state
    memory_node_repo = getattr(state, "memory_node_repo", None)
    if not memory_node_repo:
        return {"task_id": task_id, "nodes": [], "count": 0}

    nodes = memory_node_repo.get_by_source("research", task_id)
    if not nodes:
        task_repo = getattr(state, "research_task_repo", None)
        if task_repo:
            task = task_repo.get(task_id)
            conv_id = task.get("conversation_id") if task else None
            if conv_id:
                nodes = memory_node_repo.get_nodes(conv_id)

    result_nodes = []
    for n in nodes or []:
        result_nodes.append(
            MemoryNodeResponse(
                id=n.get("id", ""),
                node_type=n.get("node_type", "concept"),
                intensity=n.get("intensity", 0.0),
                scar=n.get("scar", ""),
                intra_active_text=n.get("intra_active_text", ""),
                surface_fragment=n.get("surface_fragment", ""),
                diffractive_key=n.get("diffractive_key", ""),
                agential_symmetry=n.get("agential_symmetry", ""),
                source_type=n.get("source_type", "conversation"),
                source_id=n.get("source_id", ""),
                created_at=str(n.get("created_at", "")),
            )
        )
    return {"task_id": task_id, "nodes": result_nodes, "count": len(result_nodes)}


@router.get("/research/{task_id}/semantic-knots", response_model=KnotsResponse)
async def get_research_semantic_knots(task_id: str, request: Request):
    state = request.app.state
    knot_repo = getattr(state, "semantic_knot_repo", None)
    if not knot_repo:
        return {"task_id": task_id, "knots": [], "count": 0}

    task_repo = getattr(state, "research_task_repo", None)
    conv_id = None
    if task_repo:
        task = task_repo.get(task_id)
        conv_id = task.get("conversation_id") if task else None

    if not conv_id:
        conv_id = f"research_{task_id}"

    knots = knot_repo.get_by_conversation(conv_id)
    result_knots = []
    for k in knots or []:
        result_knots.append(
            KnotResponse(
                id=k.id,
                weight=k.weight,
                concept_payload=k.concept_payload,
                token_count=k.token_count,
                created_at=str(k.created_at) if k.created_at else None,
            )
        )
    return {"task_id": task_id, "knots": result_knots, "count": len(result_knots)}
