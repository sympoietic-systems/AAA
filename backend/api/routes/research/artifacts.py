"""Research task export, stages, and import endpoints."""

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from backend.api.routes.research.tasks import _extract_depth

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Research Export ────────────────────────────────────────────────────


@router.get("/research/tasks/{task_id}/export")
async def export_research_task(task_id: str, request: Request):

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
    v = task.get("rerun_count") or 0
    d = _extract_depth(task)
    filename = f"research_{safe_title}_{task_id[:8]}_v{v}_d{d}.md"

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
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", safe_title).strip("_") or "research"
    v = task.get("rerun_count") or 0
    d = _extract_depth(task)
    filename = f"{safe_name}_v{v}_d{d}.md"

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
    status: str | None = None,
    limit: int | None = None,
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
