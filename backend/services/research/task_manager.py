"""ResearchTaskManager — central coordinator for autonomous research tasks.

Lifecycle: PROPOSED -> APPROVED -> QUEUED -> ACTIVE -> COMPLETED / FAILED
Rejection: PROPOSED -> REJECTED  (terminal)
Expiry:    PROPOSED -> EXPIRED    (terminal)
Cancel:    any non-terminal -> CANCELLED

Priority: 1=user-inline, 2=user-console, 3=symbia-conversation, 4=symbia-daemon
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from backend.utils.research_logger import now_utc_str
from backend.utils.concurrency import ensure_semaphore

logger = logging.getLogger("aaa.research_task_manager")

VALID_STATUSES = {
    "proposed", "approved", "queued", "active",
    "completed", "failed", "cancelled", "rejected", "expired",
}

VALID_TRANSITIONS = {
    "proposed":  {"approved", "rejected", "expired", "cancelled"},
    "approved":  {"queued", "active", "cancelled"},
    "queued":    {"active", "cancelled"},
    "active":    {"completed", "failed", "cancelled"},
}

TERMINAL_STATUSES = {"completed", "failed", "cancelled", "rejected", "expired"}


class ResearchTaskManager:
    """Singleton service managing the lifecycle of all research tasks."""

    def __init__(self, app_state: Any):
        self._app_state = app_state
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._orchestrator = None  # lazy init

    @property
    def orchestrator(self):
        """Lazy-init the orchestrator singleton (shared across all tasks)."""
        if self._orchestrator is None:
            from backend.services.research.orchestrator import SomaticResearchOrchestrator
            self._orchestrator = SomaticResearchOrchestrator(self._app_state)
        return self._orchestrator

    @property
    def config(self) -> dict:
        return self._app_state.config.get("research_tasks", {})

    @property
    def max_concurrent(self) -> int:
        return self.config.get("max_concurrent", 2)

    @property
    def task_repo(self):
        return self._app_state.research_task_repo

    @property
    def branch_repo(self):
        return self._app_state.research_branch_repo

    @property
    def asset_repo(self):
        return self._app_state.scraped_asset_repo

    def _get_semaphore(self) -> asyncio.Semaphore:
        return ensure_semaphore(self, '_semaphore', self.max_concurrent)

    # ── Task Creation ─────────────────────────────────────────────

    def create_task(
        self,
        objective: str,
        trigger_source: str,
        title: str = "",
        conversation_id: Optional[str] = None,
        status: str = "proposed",
        priority: int = 2,
        max_depth: int = 3,
        max_breadth: int = 4,
        is_agonistic: bool = False,
        budget_limit_usd: float = 0.50,
        proposal_rationale: Optional[str] = None,
        proposal_message_id: Optional[int] = None,
        previous_context: Optional[str] = None,
        continue_from_task_id: Optional[str] = None,
        inject_file_id: Optional[str] = None,
        inject_conversation_id: Optional[str] = None,
        document_mode: Optional[str] = None,
        document_chunk_limit: Optional[int] = None,
    ) -> str:
        """Create a new research task and persist it. Returns task_id."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")

        task_id = str(uuid.uuid4())
        task_data = {
            "id": task_id,
            "title": title or objective[:80],
            "objective": objective,
            "trigger_source": trigger_source,
            "status": status,
            "priority": priority,
            "conversation_id": conversation_id,
            "max_depth": max_depth,
            "max_breadth": max_breadth,
            "is_agonistic": is_agonistic,
            "budget_limit_usd": budget_limit_usd,
            "proposal_rationale": proposal_rationale,
            "proposal_message_id": proposal_message_id,
        }
        self.task_repo.create(task_data)

        extra_state: dict[str, Any] = {}
        if previous_context:
            extra_state["previous_context"] = previous_context
        if continue_from_task_id:
            extra_state["continue_from_task_id"] = continue_from_task_id
        if inject_file_id:
            extra_state["inject_file_id"] = inject_file_id
        if inject_conversation_id:
            extra_state["inject_conversation_id"] = inject_conversation_id
        if document_mode:
            extra_state["document_mode"] = document_mode
        if document_chunk_limit is not None:
            extra_state["document_chunk_limit"] = document_chunk_limit
        if extra_state:
            import json
            self.task_repo.update(task_id, orchestrator_state=json.dumps(
                extra_state, default=str, ensure_ascii=False))
        logger.info(
            "Research task created: %s [%s] status=%s trigger=%s",
            task_id, task_data["title"][:60], status, trigger_source,
        )
        return task_id

    # ── Lifecycle Transitions ─────────────────────────────────────

    def transition(self, task_id: str, new_status: str) -> None:
        """Validate and execute a status transition."""
        task = self.task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        current = task["status"]
        if current in TERMINAL_STATUSES:
            raise ValueError(f"Cannot transition from terminal status: {current}")

        allowed = VALID_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {current} -> {new_status}. "
                f"Allowed: {allowed}"
            )

        self.task_repo.transition_status(task_id, new_status)
        logger.info("Research task %s: %s -> %s", task_id, current, new_status)

        # Dispatch notification
        self._dispatch_notification(task, new_status)

    def approve(self, task_id: str) -> None:
        """User approves a Symbia-proposed task."""
        self.task_repo.update(task_id, approved_by="user", approved_at=now_utc_str())
        self.transition(task_id, "approved")

    def reject(self, task_id: str) -> None:
        """User rejects a Symbia proposal."""
        self.transition(task_id, "rejected")

    def queue(self, task_id: str) -> None:
        """Move an approved task into the execution queue."""
        self.transition(task_id, "queued")
        asyncio.create_task(self._try_process_queue())

    def cancel(self, task_id: str) -> None:
        """Cancel a queued or active task."""
        task = self.task_repo.get(task_id)
        if task is None:
            return
        if task["status"] not in ("queued", "active", "proposed", "approved"):
            raise ValueError(f"Cannot cancel task in status: {task['status']}")

        self.transition(task_id, "cancelled")
        if task_id in self._active_tasks:
            self._active_tasks[task_id].cancel()

    def delete(self, task_id: str) -> None:
        """Delete a task and all associated data (CASCADE)."""
        task = self.task_repo.get(task_id)
        if task is None:
            return
        if task_id in self._active_tasks:
            try:
                self._active_tasks[task_id].cancel()
            except Exception:
                pass
            self._active_tasks.pop(task_id, None)

        note_repo = getattr(self._app_state, "note_repo", None)
        if note_repo:
            try:
                note_repo.delete_notes_by_asset("research_task", task_id)
            except Exception:
                pass

        self.task_repo.delete(task_id)
        logger.info("Research task %s deleted", task_id)

    def complete(self, task_id: str, result_summary: str = "") -> None:
        self.task_repo.update(task_id, result_summary=result_summary)
        self.transition(task_id, "completed")

        # Ingestion Hook: write synthesis report and start digestion
        task = self.task_repo.get(task_id)
        if task and task.get("conversation_id"):
            conversation_id = task["conversation_id"]
            try:
                v = task.get("rerun_count") or 0
                filename = f"research-synthesis-{task_id}_v{v}.md"
                from backend.services.file import FileService
                
                from backend.services.export import ExportService
                full_report = ExportService.build_research_report_content(self._app_state, task_id)
                content_bytes = full_report.encode("utf-8")
                
                # Cache on disk
                FileService.cache_file(conversation_id, filename, content_bytes)
                
                # Register in perception_files
                perception_repo = getattr(self._app_state, "perception_repo", None)
                if perception_repo:
                    perception_repo.create_file(
                        conversation_id=conversation_id,
                        file_name=filename,
                        file_type="research-synthesis",
                        status="uploading",
                    )
                    
                    # Spawn async digest worker
                    coro = FileService.process_and_summarize(
                        self._app_state, conversation_id, filename, "research-synthesis"
                    )
                    asyncio.create_task(coro)
                    logger.info("Automatically registered and queued digestion for research-synthesis: %s", filename)
            except Exception as e:
                logger.error("Failed to automatically digest research synthesis for task %s: %s", task_id, e)

    def fail(self, task_id: str, error_reason: str = "") -> None:
        self.task_repo.update(
            task_id,
            result_summary=f"FAILED: {error_reason}" if error_reason else "FAILED",
        )
        self.transition(task_id, "failed")

    # ── Queue Processing ──────────────────────────────────────────

    async def _try_process_queue(self) -> None:
        """Pull the next queued task and activate it if slots are available."""
        semaphore = self._get_semaphore()
        if semaphore.locked() or semaphore._value == 0:
            return  # No slots available

        task = self.task_repo.get_next_queued()
        if task is None:
            return

        task_id = task["id"]
        self.transition(task_id, "active")

        # Spawn the execution coroutine
        coro = self._execute_task(task_id)
        asyncio_task = asyncio.create_task(coro)
        self._active_tasks[task_id] = asyncio_task
        logger.info("Research task %s activated (%d/%d slots)", task_id, len(self._active_tasks), self.max_concurrent)

    async def _execute_task(self, task_id: str) -> None:
        """Execute a research task — orchestrator or legacy engine based on config."""
        semaphore = self._get_semaphore()
        async with semaphore:
            try:
                task = self.task_repo.get(task_id)
                logger.info(
                    "EXECUTING research task %s: %s",
                    task_id, task.get("title", "")[:80],
                )

                logger.info("EXECUTING task %s via orchestrator", task_id[:8])
                result = await self.orchestrator.execute(task_id)

                summary = result.get("result_summary", "")
                if not summary:
                    summary = (
                        f"Research complete. "
                        f"{result.get('branches_created', 0)} branches explored, "
                        f"{result.get('assets_harvested', 0)} assets harvested."
                    )
                self.complete(task_id, result_summary=summary)

            except asyncio.CancelledError:
                logger.info("Research task %s cancelled during execution", task_id)
                raise
            except Exception:
                logger.exception("Research task %s failed", task_id)
                self.fail(task_id, "Unhandled exception during research execution")
            finally:
                self._active_tasks.pop(task_id, None)
                if not self.config.get("manual_mode", False):
                    asyncio.create_task(self._try_process_queue())

    def run_task(self, task_id: str) -> None:
        """Manually trigger execution of a queued task. (manual mode)"""
        task = self.task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        if task["status"] != "queued":
            raise ValueError(f"Task must be queued to run, got: {task['status']}")

        orch_config = self._app_state.config.get("research_orchestrator", {})
        use_orchestrator = orch_config.get("enabled", False)
        is_manual = self.config.get("manual_mode", False)

        if use_orchestrator and is_manual:
            # Step-by-step mode: init state + run just planning phase
            self.transition(task_id, "active")
            coro = self._orchestrator_step_async(task_id, first_step=True)
            asyncio_task = asyncio.create_task(coro)
            self._active_tasks[task_id] = asyncio_task
            logger.info("Research task %s — orchestrator step-by-step activated", task_id)
        else:
            self.transition(task_id, "active")
            coro = self._execute_task(task_id)
            asyncio_task = asyncio.create_task(coro)
            self._active_tasks[task_id] = asyncio_task
            logger.info("Research task %s manually activated", task_id)

    async def _orchestrator_step_async(self, task_id: str, first_step: bool = False) -> None:
        """Run one orchestrator step as a background task, handling completion."""
        try:
            if first_step:
                self.orchestrator.init_task(task_id)

            result = await self.orchestrator.execute_step(task_id)
            phase = self.orchestrator.get_task_phase(task_id)

            if phase == "complete":
                summary = result.get("result_summary", "Research complete.")
                self.complete(task_id, result_summary=summary)
            elif result.get("error"):
                self.fail(task_id, result["error"])
            # Otherwise stays active — user clicks "Step" for next phase
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Orchestrator step failed for %s", task_id)
            self.fail(task_id, "Step execution failed")
        finally:
            self._active_tasks.pop(task_id, None)

    async def orchestrator_step(self, task_id: str) -> dict:
        """Execute the next orchestrator phase. Returns phase info."""
        state = self.orchestrator.get_task_phase(task_id)
        if not state:
            raise RuntimeError(f"No orchestrator state for {task_id}")
        if state == "complete":
            return {"task_id": task_id, "executed_phase": "complete", "next_phase": "complete",
                    "message": "already complete"}

        result = await self.orchestrator.execute_step(task_id)
        phase = self.orchestrator.get_task_phase(task_id)

        if phase == "complete":
            if result.get("status") == "error":
                # Task was already set to "failed" by execute_step's exception handler;
                # don't overwrite with "completed".
                logger.warning("orchestrator_step: phase=complete but result is error — skipping complete(), "
                               "task already failed for %s", result.get("failed_phase", task_id[:8]))
            else:
                summary = result.get("result_summary", "Research complete.")
                self.complete(task_id, result_summary=summary)

        return result

    def rerun_task(self, task_id: str) -> None:
        """Rerun a terminal task in-place — resets counters, clears old data.

        Use for debugging: edit code, rerun same task to see new results.
        Does NOT clone — preserves task ID, objective, parameters.
        """
        task = self.task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        if task["status"] not in ("completed", "failed", "cancelled"):
            raise ValueError(
                f"Can only rerun terminal tasks, got: {task['status']}"
            )

        # Delete old branches and assets for this task
        try:
            self.asset_repo.delete_by_task(task_id)
        except Exception:
            pass
        try:
            self.branch_repo.delete_by_task(task_id)
        except Exception:
            pass

        # Delete old steps and plans (step results cascade delete)
        try:
            if hasattr(self.orchestrator, "step_repo") and self.orchestrator.step_repo:
                conn = self.orchestrator.step_repo._conn()
                conn.execute("DELETE FROM research_steps WHERE task_id = ?", (task_id,))
                conn.commit()
        except Exception:
            logger.exception("Failed to delete old steps for task %s during rerun", task_id)
        try:
            if hasattr(self.orchestrator, "plan_repo") and self.orchestrator.plan_repo:
                conn = self.orchestrator.plan_repo._conn()
                conn.execute("DELETE FROM research_plans WHERE task_id = ?", (task_id,))
                conn.commit()
        except Exception:
            logger.exception("Failed to delete old plans for task %s during rerun", task_id)

        # Reset counters
        rerun_count = (task.get("rerun_count") or 0) + 1
        update_fields = {
            "status": "queued",
            "budget_spent_usd": 0.0,
            "branches_created": 0,
            "assets_harvested": 0,
            "lateral_flights": 0,
            "bifurcation_triggered": 0,
            "result_summary": None,
            "started_at": None,
            "completed_at": None,
            "orchestrator_state": None,
        }
        try:
            update_fields["rerun_count"] = rerun_count
            self.task_repo.update(task_id, **update_fields)
        except Exception:
            # rerun_count column may not exist (m035 not applied yet)
            update_fields.pop("rerun_count", None)
            self.task_repo.update(task_id, **update_fields)
        logger.info(
            "Research task %s rerun #%d (in-place reset)", task_id, rerun_count,
        )

        asyncio.create_task(self._try_process_queue())

    def continue_task(
        self,
        task_id: str,
        additional_cycles: int = 1,
        adjusted_objective: str = "",
        inject_file_id: str = "",
        inject_conversation_id: str = "",
        document_mode: str = "",
        document_chunk_limit: int = 5,
        budget_limit_usd: float = 0.0,
    ) -> None:
        """Continue a completed task in-place — bumps depth, resets phase, re-queues.

        Preserves the task ID and prior synthesis as planner context.
        New document injection is optional (re-runs document_digestion phase).
        """
        import json
        import sys

        rt_config = self.config
        logger.debug("continue_task START: manual_mode=%s, enabled=%s",
                     rt_config.get('manual_mode', False), rt_config.get('enabled', 'MISSING'))

        task = self.task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        if task["status"] not in ("completed", "failed", "cancelled"):
            raise ValueError(
                f"Can only continue terminal tasks, got: {task['status']}"
            )

        new_objective = adjusted_objective or task["objective"]
        new_budget = budget_limit_usd or task["budget_limit_usd"]

        # Carry forward old orchestrator state so the planner sees previous
        # findings, consolidation report, reflection notes, etc.
        orch_state: dict[str, Any] = {}
        old_raw = task.get("orchestrator_state")
        if old_raw:
            try:
                old_orch = json.loads(old_raw) if isinstance(old_raw, str) else old_raw
            except Exception:
                old_orch = {}

            carry_keys = (
                "plan", "all_findings", "last_reflection",
                "search_results_cache", "parsed_sources_cache", "digest_results_cache",
                "digest_signals", "sedimentation_queue",
                "reflection_notes", "detected_biases", "knowledge_gaps",
                "glitch_fidelity", "contradiction_density", "source_entropy",
                "signal_flags", "refined_queries", "revised_confidence",
                "monologue_trace", "critique_log", "diffractive_audit", "diffractive_audit_description",
            )
            for k in carry_keys:
                if k in old_orch:
                    orch_state[k] = old_orch[k]

        # Always override these with current values
        previous_context = task.get("result_summary") or ""
        if previous_context:
            orch_state["previous_context"] = previous_context
        if inject_file_id:
            orch_state["inject_file_id"] = inject_file_id
        if inject_conversation_id:
            orch_state["inject_conversation_id"] = inject_conversation_id
        if document_mode:
            orch_state["document_mode"] = document_mode
        if document_chunk_limit:
            orch_state["document_chunk_limit"] = document_chunk_limit
        orch_state["document_digested"] = False

        max_phase_group = 0
        old_current_depth = 0
        try:
            steps_repo = getattr(self._app_state, "research_step_repo", None)
            if steps_repo:
                existing = steps_repo.get_by_task(task_id)
                for s in (existing or []):
                    pg = s.get("phase_group", 0) or s.get("step_number", 0)
                    if pg > max_phase_group:
                        max_phase_group = pg
                    sd = s.get("step_data")
                    if sd:
                        try:
                            parsed = json.loads(sd) if isinstance(sd, str) else sd
                            d = parsed.get("depth") if isinstance(parsed, dict) else 0
                            if isinstance(d, (int, float)) and d > old_current_depth:
                                old_current_depth = int(d)
                        except Exception:
                            pass
        except Exception:
            pass

        old_cur_depth = old_orch.get("current_depth", 0) if old_raw else 0
        if old_cur_depth > old_current_depth:
            old_current_depth = old_cur_depth

        orch_state["phase_group"] = max_phase_group
        orch_state["step_number"] = max_phase_group
        orch_state["last_block"] = ""
        orch_state["sub_sequence"] = 0
        orch_state["current_depth"] = old_current_depth + 1
        orch_state["max_depth"] = orch_state["current_depth"]  # one cycle then hard-stop

        logger.info("continue_task: max_phase_group=%d, previous_context=%d chars",
                     max_phase_group, len(previous_context))

        rerun_count = (task.get("rerun_count") or 0) + 1
        update_fields: dict[str, Any] = {
            "status": "queued",
            "objective": new_objective,
            "max_depth": orch_state["current_depth"],
            "budget_limit_usd": new_budget,
            "budget_spent_usd": 0.0,
            "branches_created": 0,
            "assets_harvested": 0,
            "lateral_flights": 0,
            "bifurcation_triggered": 0,
            "result_summary": task.get("result_summary"),
            "started_at": None,
            "completed_at": None,
            "orchestrator_state": json.dumps(orch_state, default=str, ensure_ascii=False),
        }
        try:
            update_fields["rerun_count"] = rerun_count
            self.task_repo.update(task_id, **update_fields)
        except Exception:
            update_fields.pop("rerun_count", None)
            self.task_repo.update(task_id, **update_fields)

        # Clear cached phase inputs so they recalculate for the new depth/context
        try:
            self.orchestrator.reinitialize(task_id)
        except Exception:
            logger.exception("Failed to reinitialize cache during continue_task")

        manual = self.config.get("manual_mode", False)
        logger.info("continue_task: spawning orchestrator for %s (manual_mode=%s)", task_id[:8], manual)
        self.transition(task_id, "active")
        coro = self._execute_continued_task(task_id)
        asyncio_task = asyncio.create_task(coro)
        self._active_tasks[task_id] = asyncio_task

        logger.info(
            "Research task %s continued (run #%d) — depth %d→%d, pg_offset=%d, previous_context=%d chars",
            task_id, rerun_count, task["max_depth"], orch_state["current_depth"], max_phase_group, len(previous_context),
        )

    async def _execute_continued_task(self, task_id: str) -> None:
        """Execute a continued task step-by-step via orchestrator, stopping after planning."""
        try:
            logger.info("EXECUTING continued task %s via orchestrator (step-by-step)", task_id[:8])
            await self._orchestrator_step_async(task_id, first_step=True)
            logger.info("Continued task %s initial step executed", task_id[:8])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Continued task %s failed", task_id)
            self.fail(task_id, "Continued task execution failed")
        finally:
            self._active_tasks.pop(task_id, None)

    # ── Budget ────────────────────────────────────────────────────

    def allocate_budget(self, task_id: str, amount_usd: float) -> None:
        task = self.task_repo.get(task_id)
        if task is None:
            return
        new_spent = task["budget_spent_usd"] + amount_usd
        self.task_repo.update(task_id, budget_spent_usd=new_spent)

    # ── Proposal Management ──────────────────────────────────────

    def expire_stale_proposals(self) -> int:
        """Expire proposals past their timeout. Returns count of expired."""
        rt_config = self.config
        count = self.task_repo.expire_stale_proposals(
            conversation_timeout_mins=rt_config.get("conversation_proposal_timeout_minutes", 30),
            daemon_timeout_mins=rt_config.get("daemon_proposal_timeout_minutes", 60),
        )
        if count > 0:
            logger.info("Expired %d stale research proposals", count)
        return count

    def pending_proposal_count(self) -> int:
        return self.task_repo.count_by_status("proposed")

    def active_task_count(self) -> int:
        return self.task_repo.count_by_status("active")

    def queued_task_count(self) -> int:
        return self.task_repo.count_by_status("queued")

    def has_active_for_conversation(self, conversation_id: str) -> bool:
        return self.task_repo.has_active_for_conversation(conversation_id)

    # ── Query ─────────────────────────────────────────────────────

    def get_task(self, task_id: str) -> Optional[dict]:
        return self.task_repo.get(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        trigger_source: Optional[str] = None,
        conversation_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        return self.task_repo.list_all(
            status=status,
            trigger_source=trigger_source,
            conversation_id=conversation_id,
            limit=limit,
        )

    def get_active_summary(self) -> dict:
        """Lightweight summary for frontend polling."""
        return {
            "active_count": self.active_task_count(),
            "queued_count": self.queued_task_count(),
            "pending_proposals": self.pending_proposal_count(),
        }

    # ── Notifications ─────────────────────────────────────────────

    def _dispatch_notification(self, task: dict, new_status: str) -> None:
        """Create a notification for a lifecycle transition."""
        try:
            notif_repo = getattr(self._app_state, "notification_repo", None)
            if notif_repo is None:
                return

            snippet_map = {
                "approved": f"Research approved: {task['title'][:80]}",
                "queued": f"Research queued: {task['title'][:80]}",
                "active": f"Research started: {task['title'][:80]}",
                "completed": f"Research complete: {task['title'][:80]}",
                "failed": f"Research failed: {task['title'][:80]}",
                "cancelled": f"Research cancelled: {task['title'][:80]}",
                "rejected": f"Proposal rejected: {task['title'][:80]}",
                "expired": f"Proposal expired: {task['title'][:80]}",
            }

            notif_repo.create(
                type="trace",
                snippet=snippet_map.get(new_status, f"Research {new_status}: {task['title'][:80]}"),
                source=f"research_task_manager:{new_status}",
                source_type="research",
                source_id=task["id"],
                conversation_id=task.get("conversation_id"),
            )
        except Exception:
            logger.exception("Failed to create research notification")
