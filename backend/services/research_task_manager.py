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
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def _now_utc_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

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
        self.task_repo.update(task_id, approved_by="user", approved_at=self._now_utc_str())
        self.transition(task_id, "approved")

    def reject(self, task_id: str) -> None:
        """User rejects a Symbia proposal."""
        self.transition(task_id, "rejected")

    def queue(self, task_id: str) -> None:
        """Move an approved task into the execution queue."""
        self.transition(task_id, "queued")
        # Try to start if slots are available
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
        # Cancel active task first if running
        if task_id in self._active_tasks:
            try:
                self._active_tasks[task_id].cancel()
            except Exception:
                pass
            self._active_tasks.pop(task_id, None)
        self.task_repo.delete(task_id)
        logger.info("Research task %s deleted", task_id)

    def complete(self, task_id: str, result_summary: str = "") -> None:
        self.task_repo.update(task_id, result_summary=result_summary)
        self.transition(task_id, "completed")

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

                # Check if orchestrator is enabled
                orch_config = self._app_state.config.get("research_orchestrator", {})
                use_orchestrator = orch_config.get("enabled", False)

                if use_orchestrator:
                    from backend.services.research_orchestrator import SomaticResearchOrchestrator
                    orchestrator = SomaticResearchOrchestrator(self._app_state)
                    result = await orchestrator.execute(task_id)
                else:
                    from backend.services.somatic_research import SomaticResearchEngine
                    engine = SomaticResearchEngine(self._app_state)
                    result = await engine.execute(task_id)

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
                asyncio.create_task(self._try_process_queue())

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
