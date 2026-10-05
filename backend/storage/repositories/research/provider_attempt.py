"""Durable attempt reservations and immutable terminal delivery."""

import json

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.research.action_receipt import ReceiptConflictError
from backend.storage.research_receipts import ProviderAttemptReceipt


class ResearchProviderAttemptRepository(BaseRepository):
    @with_connection
    def summary(self, task_id: str) -> dict[str, int]:
        rows = (
            self._conn()
            .execute(
                "SELECT outcome, COUNT(*) FROM research_provider_attempts WHERE task_id=? GROUP BY outcome", (task_id,)
            )
            .fetchall()
        )
        return {str(row[0]): int(row[1]) for row in rows}

    @with_connection
    def reserve(self, receipt: ProviderAttemptReceipt, max_task_attempts: int) -> None:
        if not receipt.attempt_id or receipt.outcome != "pending" or receipt.completed_at is not None:
            raise ReceiptConflictError("Provider reservation requires pending intent")
        with self.atomic():
            conn = self._conn()
            task = conn.execute(
                "SELECT orchestrator_state FROM research_tasks WHERE id=?", (receipt.task_id,)
            ).fetchone()
            action = conn.execute(
                "SELECT status FROM research_action_receipts WHERE task_id=? AND action_id=?",
                (receipt.task_id, receipt.action_id),
            ).fetchone()
            if (
                not task
                or not action
                or action[0] != "running"
                or json.loads(task[0] or "{}").get("active_action_id") != receipt.action_id
            ):
                raise ReceiptConflictError("Provider intent requires the current running action")
            existing = self.get(receipt.task_id, receipt.action_id, receipt.attempt_id)
            if existing is not None:
                if existing != receipt:
                    raise ReceiptConflictError("Attempt identity already reserved")
                return
            count = conn.execute(
                "SELECT COUNT(*) FROM research_provider_attempts WHERE task_id=?", (receipt.task_id,)
            ).fetchone()[0]
            if count >= max_task_attempts:
                raise ReceiptConflictError("Task provider attempt budget exhausted")
            conn.execute(
                "INSERT INTO research_provider_attempts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    receipt.attempt_id,
                    receipt.task_id,
                    receipt.action_id,
                    receipt.request_id,
                    receipt.attempt_number,
                    receipt.model_dump_json(),
                    receipt.outcome,
                ),
            )

    @with_connection
    def get(self, task_id: str, action_id: str, attempt_id: str) -> ProviderAttemptReceipt | None:
        row = (
            self._conn()
            .execute(
                "SELECT receipt_json FROM research_provider_attempts WHERE task_id=? AND action_id=? AND attempt_id=?",
                (task_id, action_id, attempt_id),
            )
            .fetchone()
        )
        return ProviderAttemptReceipt.model_validate_json(row[0]) if row else None

    @with_connection
    def finish(self, receipt: ProviderAttemptReceipt) -> None:
        if not receipt.attempt_id or receipt.outcome == "pending" or receipt.completed_at is None:
            raise ReceiptConflictError("Provider delivery requires a terminal observation")
        with self.atomic():
            existing = self.get(receipt.task_id, receipt.action_id, receipt.attempt_id)
            if existing == receipt:
                return
            if existing is None or existing.outcome != "pending":
                raise ReceiptConflictError("Stale provider delivery")
            keys = (
                "attempt_id",
                "task_id",
                "action_id",
                "request_id",
                "attempt_number",
                "provider",
                "model",
                "started_at",
            )
            if any(getattr(existing, key) != getattr(receipt, key) for key in keys):
                raise ReceiptConflictError("Provider delivery changed its request")
            self._conn().execute(
                "UPDATE research_provider_attempts SET receipt_json=?, outcome=? WHERE attempt_id=? AND outcome='pending'",
                (receipt.model_dump_json(), receipt.outcome, receipt.attempt_id),
            )

    @with_connection
    def list_by_action(self, task_id: str, action_id: str) -> list[ProviderAttemptReceipt]:
        rows = (
            self._conn()
            .execute(
                "SELECT receipt_json FROM research_provider_attempts WHERE task_id=? AND action_id=? ORDER BY rowid LIMIT 256",
                (task_id, action_id),
            )
            .fetchall()
        )
        return [ProviderAttemptReceipt.model_validate_json(row[0]) for row in rows]
