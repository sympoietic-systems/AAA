"""Atomic receipt writes; callers offload synchronous repository operations."""

import json

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.research_receipts import ActionStatus, ResearchActionReceipt


class ReceiptConflictError(ValueError):
    """An action identity or terminal observation was reused inconsistently."""


class ResearchActionReceiptRepository(BaseRepository):
    @with_connection
    def initialize_task_state(self, task_id: str, state_json: str) -> str:
        """Freeze policy before the first action; a competing initializer wins once."""
        with self.atomic():
            self._conn().execute(
                "UPDATE research_tasks SET orchestrator_state = ? WHERE id = ? AND (orchestrator_state IS NULL OR orchestrator_state = '')",
                (state_json, task_id),
            )
            row = (
                self._conn()
                .execute("SELECT orchestrator_state FROM research_tasks WHERE id = ?", (task_id,))
                .fetchone()
            )
            if row is None:
                raise ReceiptConflictError("Task disappeared during initialization")
            return str(row[0])

    @with_connection
    def checkpoint(self, receipt: ResearchActionReceipt, state_json: str, *, starting: bool = False) -> None:
        """Commit an action transition and task checkpoint as one short transaction."""
        with self.atomic():
            task = (
                self._conn()
                .execute("SELECT orchestrator_state FROM research_tasks WHERE id = ?", (receipt.task_id,))
                .fetchone()
            )
            if task is None:
                raise ReceiptConflictError("Task disappeared during checkpoint")
            previous = json.loads(task[0]) if task[0] else {}
            active_id = previous.get("active_action_id")
            last_id = previous.get("last_action_id")
            if starting:
                expected_last = receipt.dependency_ids[-1] if receipt.dependency_ids else None
                if active_id or last_id != expected_last:
                    raise ReceiptConflictError("Another executor already advanced this task")
                pending = ResearchActionReceipt.model_validate(
                    {
                        **receipt.model_dump(),
                        "status": "pending",
                        "started_at": None,
                    }
                )
                self.create(pending)
                self.transition(receipt, expected_status="pending")
            else:
                if active_id != receipt.action_id and not (active_id is None and last_id == receipt.action_id):
                    raise ReceiptConflictError("Late action cannot overwrite a newer task checkpoint")
                self.transition(receipt, expected_status="running")
            cursor = self._conn().execute(
                "UPDATE research_tasks SET orchestrator_state = ? WHERE id = ?",
                (state_json, receipt.task_id),
            )
            if cursor.rowcount != 1:
                raise ReceiptConflictError("Task disappeared during checkpoint")

    @with_connection
    def create(self, receipt: ResearchActionReceipt) -> ResearchActionReceipt:
        if receipt.status != "pending" or receipt.observation is not None or receipt.started_at or receipt.completed_at:
            raise ReceiptConflictError("New action must be pending without delivery observations")
        request_json = receipt.request_json()
        receipt_json = receipt.model_dump_json()
        with self.atomic():
            conn = self._conn()
            conn.execute(
                "INSERT INTO research_action_receipts VALUES (?, ?, ?, ?, ?) ON CONFLICT(action_id) DO NOTHING",
                (receipt.action_id, receipt.task_id, request_json, receipt_json, receipt.status),
            )
            row = conn.execute(
                "SELECT request_json, receipt_json FROM research_action_receipts WHERE action_id = ?",
                (receipt.action_id,),
            ).fetchone()
            if row is None or row["request_json"] != request_json:
                raise ReceiptConflictError("Action ID already belongs to a different request")
            return ResearchActionReceipt.model_validate_json(row["receipt_json"])

    @with_connection
    def get(self, task_id: str, action_id: str) -> ResearchActionReceipt | None:
        row = (
            self._conn()
            .execute(
                "SELECT receipt_json FROM research_action_receipts WHERE task_id = ? AND action_id = ?",
                (task_id, action_id),
            )
            .fetchone()
        )
        return ResearchActionReceipt.model_validate_json(row[0]) if row else None

    @with_connection
    def transition(self, receipt: ResearchActionReceipt, *, expected_status: ActionStatus) -> ResearchActionReceipt:
        request_json = receipt.request_json()
        receipt_json = receipt.model_dump_json()
        with self.atomic():
            conn = self._conn()
            existing = self.get(receipt.task_id, receipt.action_id)
            if existing is None or existing.request_json() != request_json:
                raise ReceiptConflictError("Missing action or changed request")
            if existing == receipt:
                return existing
            if existing.status != expected_status:
                raise ReceiptConflictError("Stale action transition")
            allowed = {"pending": {"running", "cancelled"}, "running": {"complete", "partial", "failed", "cancelled"}}
            if receipt.status not in allowed.get(existing.status, set()):
                raise ReceiptConflictError("Invalid action transition")
            if receipt.status == "running":
                if receipt.started_at is None or receipt.completed_at is not None or receipt.observation is not None:
                    raise ReceiptConflictError("Running action requires start time and no terminal observation")
            else:
                if receipt.completed_at is None or receipt.started_at != existing.started_at:
                    raise ReceiptConflictError("Terminal action requires completion time and original start")
                if receipt.started_at and receipt.completed_at < receipt.started_at:
                    raise ReceiptConflictError("Completion precedes start")
            if receipt.observation:
                for attempt in receipt.observation.provider_attempts:
                    if attempt.task_id != receipt.task_id or attempt.action_id != receipt.action_id:
                        raise ReceiptConflictError("Provider attempt belongs to another action")
                    if receipt.status == "complete" and (attempt.truncated or attempt.finish_reason == "length"):
                        raise ReceiptConflictError("Truncated delivery cannot be complete")
            conn.execute(
                "UPDATE research_action_receipts SET receipt_json = ?, status = ? WHERE action_id = ?",
                (receipt_json, receipt.status, receipt.action_id),
            )
            return receipt
