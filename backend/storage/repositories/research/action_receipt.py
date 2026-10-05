"""Atomic receipt writes; callers offload synchronous repository operations."""

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.research_receipts import ActionStatus, ResearchActionReceipt


class ReceiptConflictError(ValueError):
    """An action identity or terminal observation was reused inconsistently."""


class ResearchActionReceiptRepository(BaseRepository):
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
