"""Typed async boundary for synchronous research API operations."""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


async def run_research_sync(operation: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs) -> R:
    """Run one synchronous research use case outside the event loop."""
    return await asyncio.to_thread(operation, *args, **kwargs)


async def queue_task(manager: Any, task_id: str) -> None:
    """Persist a queue transition off-loop, then start queue processing on-loop."""
    await run_research_sync(manager.transition, task_id, "queued")
    await manager._try_process_queue()


async def approve_and_queue_task(manager: Any, task_id: str) -> None:
    await run_research_sync(manager.approve, task_id)
    await queue_task(manager, task_id)


async def cancel_task(manager: Any, task_id: str) -> None:
    await run_research_sync(manager.transition, task_id, "cancelled")
    active = manager._active_tasks.get(task_id)
    if active is not None:
        active.cancel()


async def delete_task(manager: Any, task_id: str) -> None:
    active = manager._active_tasks.pop(task_id, None)
    if active is not None:
        active.cancel()

    def delete_persistence() -> None:
        manager.task_repo.delete_with_notes(task_id)

    await run_research_sync(delete_persistence)


async def run_task(manager: Any, task_id: str) -> None:
    await run_research_sync(manager.transition, task_id, "active")
    orch_config = manager._app_state.config.get("research_orchestrator", {})
    if orch_config.get("enabled", False) and manager.config.get("manual_mode", False):
        coroutine = manager._orchestrator_step_async(task_id, first_step=True)
    else:
        coroutine = manager._execute_task(task_id)
    manager._active_tasks[task_id] = asyncio.create_task(coroutine)


async def rerun_task(manager: Any, task_id: str) -> None:
    await run_research_sync(manager.rerun_task, task_id, schedule=False)
    await manager._try_process_queue()


def prepare_step_recovery(manager: Any, task_id: str, phase: str, step_type: str, step_id: str | None) -> None:
    """User-requested same-task recovery: fresh policy, retained source provenance."""
    from backend.services.research.action_journal import input_hash
    from backend.services.research.orchestrator import PHASE_BLOCK
    from backend.services.research.provider_policy import ProviderPolicy, query_limit
    from backend.services.research.task_state import serialize_research_state
    from backend.storage.repositories.research.action_receipt import (
        ReceiptConflictError,
        ResearchActionReceiptRepository,
    )

    orch = manager.orchestrator
    orch.ensure_state(task_id)
    task = manager.task_repo.get(task_id)
    expected = task["orchestrator_state"]
    state = json.loads(expected)
    steps = orch.step_repo.get_by_task(task_id)
    candidates = [
        step
        for step in steps
        if step["step_type"] == step_type
        and (step["id"] == step_id if step_id else orch._get_step_depth(step) == state.get("current_depth", 0))
    ]
    if not candidates:
        raise ReceiptConflictError("No matching step belongs to this research")
    selected = candidates[0]
    depth = orch._get_step_depth(selected)
    policy = dict(state.get("action_journal_policy") or {})
    revision = policy.get("execution_revision", 1) + 1
    history = state.get("recovery_history", [])
    if len(history) >= 16:
        raise ReceiptConflictError("Research recovery limit reached")
    state["recovery_history"] = history + [
        {
            "revision": revision,
            "requested_at": datetime.now(UTC).isoformat(),
            "phase": phase,
            "step_id": selected["id"],
            "previous_policy": policy,
            "previous_status": task["status"],
            "previous_action_id": state.get("last_action_id"),
        }
    ]
    policy = {
        **policy,
        "execution_revision": revision,
        "provider_policy": ProviderPolicy.model_validate(orch.config.get("provider_limits", {})).freeze(),
        "max_queries_per_cycle": query_limit(orch.config, {}),
    }
    policy["policy_hash"] = input_hash({key: value for key, value in policy.items() if key != "policy_hash"})
    repo = ResearchActionReceiptRepository(manager.task_repo._db_path)
    predecessor = repo.successful_predecessor(task_id, "parsing" if phase == "digesting" else None)
    if phase == "digesting" and policy.get("enabled") and predecessor is None:
        raise ReceiptConflictError("Digest recovery requires a successful parse action")
    state.update(
        phase=phase,
        current_depth=depth,
        phase_group=selected["phase_group"],
        last_block=PHASE_BLOCK.get(phase, phase),
        action_journal_policy=policy,
        last_action_id=predecessor,
        delivery_degraded=False,
        _failed_phase=None,
        should_stop=False,
        stop_reason=None,
        result_summary=None,
        scheduler_state={},
        _reuse_completed_digests=phase == "digesting",
    )
    if phase == "document_digestion":
        state.update(document_digested=False, document_learnings=[])
    groups = [
        step
        for step in steps
        if step["step_type"] == step_type
        and orch._get_step_depth(step) == depth
        and step["phase_group"] == selected["phase_group"]
    ]
    state["_rerun_group_ids"] = {str(step.get("query_group", 0)): step["id"] for step in groups}
    if phase == "digesting":
        sources = []
        retained = {
            (source["url"], source.get("content", "")): source for source in state.get("parsed_sources_cache", [])
        }
        for step in steps:
            if (
                step["step_type"] == "parallel_parse"
                and step["status"] == "completed"
                and orch._get_step_depth(step) == depth
                and step["phase_group"] == selected["phase_group"]
            ):
                for source in orch.step_result_repo.get_by_step(step["id"]):
                    sources.append(
                        {
                            **retained.get((source["source_url"], source["raw_content"] or ""), {}),
                            "id": source["id"],
                            "url": source["source_url"],
                            "title": source["source_title"],
                            "content": source["raw_content"] or "",
                            "query_group": step.get("query_group", 1),
                            "existing_analysis": json.loads(source["analyzed_json"])
                            if source.get("analyzed_json")
                            else None,
                        }
                    )
        if not sources:
            raise ReceiptConflictError("No retained parsed sources for Digest recovery")
        state["parsed_sources_cache"] = sources
    repo.recover_task_state(task_id, expected, serialize_research_state(state), selected["phase_group"])
    orch._state_mgr.states[task_id] = state


async def resume_step_recovery(manager: Any, task_id: str) -> None:
    """Continue a recovered automatic task without reinitializing its state."""
    if manager.config.get("manual_mode", False):
        return
    phase = await run_research_sync(manager.orchestrator.get_task_phase, task_id)
    if phase != "complete":
        manager._active_tasks[task_id] = asyncio.create_task(manager._execute_task(task_id, resume=True))


async def continue_task(manager: Any, task_id: str, **kwargs: Any) -> None:
    await run_research_sync(manager.continue_task, task_id, schedule=False, **kwargs)
    coroutine = manager._execute_continued_task(task_id)
    manager._active_tasks[task_id] = asyncio.create_task(coroutine)
