import json
from datetime import UTC, datetime

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.research.action_receipt import ReceiptConflictError
from backend.storage.research_acquisition import AcquisitionReceipt


class ResearchAcquisitionRepository(BaseRepository):
    @with_connection
    def reserve(self, receipt: AcquisitionReceipt) -> None:
        if receipt.outcome != "pending":
            raise ReceiptConflictError("New acquisition must be pending")
        with self.atomic():
            action = (
                self._conn()
                .execute(
                    "SELECT request_json,status FROM research_action_receipts WHERE task_id=? AND action_id=?",
                    (receipt.task_id, receipt.action_id),
                )
                .fetchone()
            )
            task = (
                self._conn()
                .execute("SELECT orchestrator_state FROM research_tasks WHERE id=?", (receipt.task_id,))
                .fetchone()
            )
            if (
                not action
                or action[1] != "running"
                or not task
                or json.loads(task[0] or "{}").get("active_action_id") != receipt.action_id
            ):
                raise ReceiptConflictError("Acquisition requires the current running action")
            request = json.loads(action[0])
            if request.get("deadline") and datetime.now(UTC) >= datetime.fromisoformat(request["deadline"]):
                raise ReceiptConflictError("Acquisition action deadline expired")
            count = (
                self._conn()
                .execute("SELECT COUNT(*) FROM research_acquisitions WHERE task_id=?", (receipt.task_id,))
                .fetchone()[0]
            )
            if count >= 256:
                raise ReceiptConflictError("Task acquisition limit exceeded")
            self._conn().execute(
                "INSERT INTO research_acquisitions VALUES (?,?,?,?,?)",
                (
                    receipt.acquisition_id,
                    receipt.task_id,
                    receipt.action_id,
                    receipt.model_dump_json(),
                    receipt.outcome,
                ),
            )

    @with_connection
    def finish(self, receipt: AcquisitionReceipt) -> None:
        receipt = AcquisitionReceipt.model_validate(receipt.model_dump())
        if receipt.outcome == "pending" or receipt.completed_at is None:
            raise ReceiptConflictError("Acquisition terminal observation required")
        with self.atomic():
            row = (
                self._conn()
                .execute(
                    "SELECT receipt_json,outcome FROM research_acquisitions WHERE acquisition_id=? AND task_id=?",
                    (receipt.acquisition_id, receipt.task_id),
                )
                .fetchone()
            )
            if not row:
                raise ReceiptConflictError("Unknown acquisition")
            old = AcquisitionReceipt.model_validate_json(row[0])
            for name in ("acquisition_id", "task_id", "action_id", "canonical_url", "config_hash", "started_at"):
                if getattr(old, name) != getattr(receipt, name):
                    raise ReceiptConflictError("Acquisition intent is immutable")
            if row[1] != "pending":
                if old != receipt:
                    raise ReceiptConflictError("Acquisition observation is immutable")
                return
            if receipt.outcome == "cache_hit":
                origin_row = (
                    self._conn()
                    .execute(
                        "SELECT receipt_json FROM research_acquisitions WHERE acquisition_id=?",
                        (receipt.origin_acquisition_id,),
                    )
                    .fetchone()
                )
                if not origin_row:
                    raise ReceiptConflictError("Cache access requires durable acquisition origin")
                origin = AcquisitionReceipt.model_validate_json(origin_row[0])
                if origin.outcome != "fetched" or (
                    origin.canonical_url,
                    origin.config_hash,
                    origin.observed_at,
                    origin.valid_until,
                    origin.source_id,
                    origin.source_version,
                ) != (
                    receipt.canonical_url,
                    receipt.config_hash,
                    receipt.observed_at,
                    receipt.valid_until,
                    receipt.source_id,
                    receipt.source_version,
                ):
                    raise ReceiptConflictError("Cache access changed observation lineage")
            self._conn().execute(
                "UPDATE research_acquisitions SET receipt_json=?,outcome=? WHERE acquisition_id=? AND outcome='pending'",
                (receipt.model_dump_json(), receipt.outcome, receipt.acquisition_id),
            )

    @with_connection
    def list_action(self, task_id: str, action_id: str) -> tuple[AcquisitionReceipt, ...]:
        rows = (
            self._conn()
            .execute(
                "SELECT receipt_json FROM research_acquisitions WHERE task_id=? AND action_id=? ORDER BY rowid LIMIT 256",
                (task_id, action_id),
            )
            .fetchall()
        )
        return tuple(AcquisitionReceipt.model_validate_json(row[0]) for row in rows)
