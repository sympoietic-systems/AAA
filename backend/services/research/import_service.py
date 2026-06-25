"""Research Import Service — imports a JSON export payload into the database.

Generates fresh UUIDs for the task and all child records to avoid ID collisions.
Remaps all internal foreign keys (task_id, branch_id, plan_id, step_id) to new IDs.
Nullifies external foreign keys (conversation_id, message_id, memory_node_id).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("aaa.research.import_service")


class ImportResult:
    def __init__(self):
        self.imported = False
        self.new_task_id: str = ""
        self.stats: dict[str, Any] = {}
        self.warnings: list[str] = []

    def to_dict(self) -> dict:
        return {
            "imported": self.imported,
            "new_task_id": self.new_task_id,
            "stats": self.stats,
            "warnings": self.warnings,
        }


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def import_research_task(payload: dict, app_state: Any) -> ImportResult:
    result = ImportResult()
    stats: dict[str, Any] = {}
    warnings: list[str] = []

    task_data = payload.get("task")
    if not task_data:
        result.warnings.append("No 'task' field in payload")
        return result

    old_task_id = task_data.get("id", "")

    # ── Generate new IDs ────────────────────────────────────────────
    new_task_id = str(uuid.uuid4())

    id_map: dict[str, str] = {old_task_id: new_task_id}

    for b in payload.get("branches", []):
        old_bid = b.get("id")
        if old_bid:
            id_map[old_bid] = str(uuid.uuid4())

    for s in payload.get("steps", []):
        old_sid = s.get("id")
        if old_sid:
            id_map[old_sid] = str(uuid.uuid4())

    if payload.get("plan"):
        old_pid = payload["plan"].get("id")
        if old_pid:
            id_map[old_pid] = str(uuid.uuid4())

    for r in payload.get("step_results", []):
        old_rid = r.get("id")
        if old_rid:
            id_map[old_rid] = str(uuid.uuid4())

    for m in payload.get("meta_log", []):
        old_mid = m.get("id")
        if old_mid:
            id_map[old_mid] = str(uuid.uuid4())

    for n in payload.get("notes", []):
        old_nid = n.get("id")
        if old_nid:
            id_map[old_nid] = str(uuid.uuid4())

    # ── Helper ──────────────────────────────────────────────────────
    def _remap_id(old: str | None) -> str | None:
        if old and old in id_map:
            return id_map[old]
        if old:
            warnings.append(f"Unknown reference ID: {old}")
        return None

    # ── 1. Insert Task ──────────────────────────────────────────────
    task_repo = app_state.research_task_repo
    new_task = {
        "id": new_task_id,
        "title": task_data.get("title", ""),
        "objective": task_data.get("objective", ""),
        "trigger_source": task_data.get("trigger_source", "user_console"),
        "status": task_data.get("status", "completed"),
        "priority": task_data.get("priority", 2),
        "conversation_id": None,
        "max_depth": task_data.get("max_depth", 3),
        "max_breadth": task_data.get("max_breadth", 4),
        "is_agonistic": task_data.get("is_agonistic", 0),
        "budget_limit_usd": task_data.get("budget_limit_usd", 0.50),
        "budget_spent_usd": task_data.get("budget_spent_usd", 0.0),
        "branches_created": task_data.get("branches_created", 0),
        "assets_harvested": task_data.get("assets_harvested", 0),
        "lateral_flights": task_data.get("lateral_flights", 0),
        "bifurcation_triggered": task_data.get("bifurcation_triggered", 0),
        "result_summary": task_data.get("result_summary"),
        "proposal_rationale": task_data.get("proposal_rationale"),
        "proposal_message_id": None,
        "approved_by": task_data.get("approved_by"),
    }
    task_repo.create(new_task)

    # create() only inserts core columns — update the rest
    extra_fields = {}
    for key in (
        "budget_spent_usd", "branches_created", "assets_harvested",
        "lateral_flights", "bifurcation_triggered", "result_summary",
        "approved_by", "approved_at", "started_at", "completed_at",
    ):
        val = task_data.get(key)
        if val is not None:
            extra_fields[key] = val
    if extra_fields:
        task_repo.update(new_task_id, **extra_fields)

    stats["task"] = "inserted"
    logger.info("Imported research task: %s (new ID: %s)", old_task_id, new_task_id)

    # ── 2. Insert Plan ─────────────────────────────────────────────
    plan_data = payload.get("plan")
    if plan_data:
        plan_repo = app_state.research_plan_repo
        new_plan_id = _remap_id(plan_data.get("id"))
        if new_plan_id:
            plan_repo.create({
                "id": new_plan_id,
                "task_id": new_task_id,
                "plan_json": plan_data.get("plan_json", "{}"),
                "status": plan_data.get("status", "draft"),
                "created_at": plan_data.get("created_at") or _now_str(),
            })
            stats["plan"] = 1

    # ── 3. Insert Branches ─────────────────────────────────────────
    branches = payload.get("branches", [])
    branch_count = 0
    if branches:
        branch_repo = app_state.research_branch_repo
        for b in branches:
            old_bid = b.get("id", "")
            new_bid = _remap_id(old_bid)
            if not new_bid:
                continue
            old_parent_bid = b.get("parent_branch_id")
            new_parent_bid = _remap_id(old_parent_bid)
            branch_repo.create({
                "id": new_bid,
                "task_id": new_task_id,
                "conversation_id": None,
                "parent_branch_id": new_parent_bid,
                "query": b.get("query", ""),
                "goal": b.get("goal", ""),
                "depth": b.get("depth", 0),
                "breadth": b.get("breadth", 0),
                "status": b.get("status", "probing"),
                "vector_16d": b.get("vector_16d"),
                "homeostatic_tension": b.get("homeostatic_tension", 0.0),
            })
            branch_count += 1
        stats["branches"] = branch_count

    # ── 4. Insert Assets ───────────────────────────────────────────
    assets = payload.get("assets", [])
    asset_count = 0
    if assets:
        asset_repo = app_state.scraped_asset_repo
        for a in assets:
            old_branch_id = a.get("branch_id", "")
            new_branch_id = _remap_id(old_branch_id)
            asset_repo.create({
                "id": str(uuid.uuid4()),
                "branch_id": new_branch_id,
                "task_id": new_task_id,
                "url": a.get("url", ""),
                "raw_markdown": a.get("raw_markdown", ""),
                "relevance_score": a.get("relevance_score", 0.0),
                "novelty_score": a.get("novelty_score", 0.0),
                "diffractive_score": a.get("diffractive_score", 0.0),
                "memory_node_id": None,
            })
            asset_count += 1
        stats["assets"] = asset_count

    # ── 5. Insert Steps ────────────────────────────────────────────
    steps = payload.get("steps", [])
    step_count = 0
    if steps:
        step_repo = app_state.research_step_repo
        for s in steps:
            old_sid = s.get("id", "")
            new_sid = _remap_id(old_sid)
            if not new_sid:
                continue
            old_plan_id = s.get("plan_id", "")
            old_plan_id_remapped = _remap_id(old_plan_id) if old_plan_id else None
            step_repo.create({
                "id": new_sid,
                "task_id": new_task_id,
                "plan_id": old_plan_id_remapped or new_task_id,
                "step_number": s.get("step_number", 0),
                "step_type": s.get("step_type", ""),
                "step_data": s.get("step_data", "{}"),
                "status": s.get("status", "pending"),
                "result_summary": s.get("result_summary"),
                "started_at": s.get("started_at"),
                "completed_at": s.get("completed_at"),
                "created_at": s.get("created_at") or _now_str(),
                "query_group": s.get("query_group"),
                "query_text": s.get("query_text"),
            })
            step_count += 1
        stats["steps"] = step_count

    # ── 6. Insert Step Results ─────────────────────────────────────
    step_results_data = payload.get("step_results", [])
    sr_count = 0
    if step_results_data:
        result_repo = app_state.research_step_result_repo
        for r in step_results_data:
            old_step_id = r.get("step_id", "")
            new_step_id = _remap_id(old_step_id)
            result_repo.create({
                "id": str(uuid.uuid4()),
                "step_id": new_step_id,
                "task_id": new_task_id,
                "source_url": r.get("source_url"),
                "source_title": r.get("source_title"),
                "raw_content": r.get("raw_content"),
                "analyzed_json": r.get("analyzed_json"),
                "relevance_score": r.get("relevance_score", 0.0),
                "novelty_score": r.get("novelty_score", 0.0),
                "raw_file_path": r.get("raw_file_path"),
                "created_at": r.get("created_at") or _now_str(),
            })
            sr_count += 1
        stats["step_results"] = sr_count

    # ── 7. Insert Meta Log ─────────────────────────────────────────
    meta_entries = payload.get("meta_log", [])
    meta_count = 0
    if meta_entries:
        meta_repo = app_state.research_meta_log_repo
        for m in meta_entries:
            old_branch_id = m.get("branch_id")
            old_step_id = m.get("step_id")
            meta_repo.create({
                "id": str(uuid.uuid4()),
                "task_id": new_task_id,
                "branch_id": _remap_id(old_branch_id),
                "step_id": _remap_id(old_step_id),
                "event_type": m.get("event_type", ""),
                "event_data": m.get("event_data", "{}"),
                "created_at": m.get("created_at") or _now_str(),
            })
            meta_count += 1
        stats["meta_log_entries"] = meta_count

    # ── 8. Insert Notes ────────────────────────────────────────────
    notes = payload.get("notes", [])
    note_count = 0
    if notes:
        note_repo = getattr(app_state, "note_repo", None)
        if note_repo:
            for n in notes:
                asset_type = n.get("asset_type", "research_task")
                asset_id_old = n.get("asset_id", "")
                if asset_type == "research_task":
                    asset_id_new = new_task_id
                elif asset_type == "research_step":
                    asset_id_new = _remap_id(asset_id_old) or new_task_id
                else:
                    asset_id_new = new_task_id

                note_repo.create_self_note(
                    id=str(uuid.uuid4()),
                    asset_type=asset_type,
                    asset_id=asset_id_new,
                    conversation_id=None,
                    selected_text=n.get("selected_text", ""),
                    comment=n.get("comment", ""),
                    visibility=n.get("visibility", "personal"),
                )
                note_count += 1
            stats["notes"] = note_count

    result.imported = True
    result.new_task_id = new_task_id
    result.stats = stats
    result.warnings = warnings
    return result
