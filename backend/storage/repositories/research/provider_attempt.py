"""Durable attempt reservations and immutable terminal delivery."""

import json
from datetime import UTC, datetime

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.research.action_receipt import ReceiptConflictError
from backend.storage.research_receipts import ProviderAttemptReceipt


class ResearchProviderAttemptRepository(BaseRepository):
    @with_connection
    def cost_ceiling(self, task_id: str, provider: str) -> float | None:
        row = self._conn().execute("SELECT orchestrator_state FROM research_tasks WHERE id=?", (task_id,)).fetchone()
        policy = json.loads(row[0] or "{}").get("action_journal_policy", {}) if row else {}
        bounds = policy.get("branch_provider_cost_ceilings_usd", {})
        value = bounds.get(provider)
        if value is not None:
            from math import isfinite

            if type(value) not in {int, float} or not isfinite(value) or value < 0:
                raise ReceiptConflictError("Invalid declared provider cost ceiling")
            return float(value)
        return None

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
                "SELECT orchestrator_state,status FROM research_tasks WHERE id=?", (receipt.task_id,)
            ).fetchone()
            action = conn.execute(
                "SELECT status FROM research_action_receipts WHERE task_id=? AND action_id=?",
                (receipt.task_id, receipt.action_id),
            ).fetchone()
            if (
                not task
                or task[1] != "active"
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
            state = json.loads(task[0])
            policy = state.get("action_journal_policy", {})
            if policy.get("execution_revision", 1) > 1:
                count = conn.execute(
                    "SELECT COUNT(*) FROM research_provider_attempts p JOIN research_action_receipts a ON a.action_id=p.action_id WHERE p.task_id=? AND json_extract(a.request_json,'$.policy_hash')=?",
                    (receipt.task_id, policy["policy_hash"]),
                ).fetchone()[0]
            else:
                count = conn.execute(
                    "SELECT COUNT(*) FROM research_provider_attempts WHERE task_id=?", (receipt.task_id,)
                ).fetchone()[0]
            if count >= max_task_attempts:
                raise ReceiptConflictError("Task provider attempt budget exhausted")
            deadline = state.get("action_journal_policy", {}).get("provider_policy", {}).get("deadline")
            if deadline and datetime.now(UTC) >= datetime.fromisoformat(deadline):
                raise ReceiptConflictError("Task provider deadline exhausted")
            child = conn.execute(
                "SELECT parent_task_id,allocation_json,status FROM research_child_runs WHERE child_task_id=?",
                (receipt.task_id,),
            ).fetchone()
            parent_id = child[0] if child else receipt.task_id
            siblings = conn.execute(
                "SELECT child_task_id,allocation_json,status FROM research_child_runs WHERE parent_task_id=?",
                (parent_id,),
            ).fetchall()
            if siblings:
                parent = conn.execute(
                    "SELECT status,orchestrator_state FROM research_tasks WHERE id=?", (parent_id,)
                ).fetchone()
                if not parent or parent[0] != "active" or child and child[2] != "running":
                    raise ReceiptConflictError("Child provider authority was revoked")
                parent_policy = json.loads(parent[1])["action_journal_policy"]["provider_policy"]
                family_count = conn.execute(
                    "SELECT COUNT(*) FROM research_provider_attempts WHERE task_id=? OR task_id IN (SELECT child_task_id FROM research_child_runs WHERE parent_task_id=?)",
                    (parent_id, parent_id),
                ).fetchone()[0]
                from backend.storage.repositories.research.branch_proposal import ResearchBranchProposalRepository

                proposal = ResearchBranchProposalRepository(self._db_path).current(parent_id)
                if not proposal:
                    raise ReceiptConflictError("Shared allocation lost approval")
                ceiling = self.cost_ceiling(receipt.task_id, receipt.provider)
                if ceiling is None or receipt.budget_reserved_usd != ceiling:
                    raise ReceiptConflictError("Family provider call requires a declared monetary ceiling")
                family_spend = conn.execute(
                    "SELECT COALESCE(SUM(MAX(COALESCE(json_extract(receipt_json,'$.known_cost_usd'),0),COALESCE(json_extract(receipt_json,'$.budget_reserved_usd'),0))),0) FROM research_provider_attempts WHERE task_id=? OR task_id IN (SELECT child_task_id FROM research_child_runs WHERE parent_task_id=?)",
                    (parent_id, parent_id),
                ).fetchone()[0]
                budget_row = conn.execute(
                    "SELECT budget_limit_usd,budget_spent_usd FROM research_tasks WHERE id=?", (parent_id,)
                ).fetchone()
                ceiling_budget = budget_row[0]
                if max(family_spend, budget_row[1] or 0) + ceiling > ceiling_budget - (
                    proposal.draft.parent_budget_reserve_usd if child else 0
                ):
                    raise ReceiptConflictError("Shared monetary budget and parent reserve exhausted")
                if family_count >= parent_policy["max_task_attempts"]:
                    raise ReceiptConflictError("Shared parent attempt budget exhausted")
                if child:
                    allocation = json.loads(child[1])
                    own_spend = conn.execute(
                        "SELECT COALESCE(SUM(MAX(COALESCE(json_extract(receipt_json,'$.known_cost_usd'),0),COALESCE(json_extract(receipt_json,'$.budget_reserved_usd'),0))),0) FROM research_provider_attempts WHERE task_id=?",
                        (receipt.task_id,),
                    ).fetchone()[0]
                    if own_spend + ceiling > allocation["budget_allocation_usd"]:
                        raise ReceiptConflictError("Child monetary allocation exhausted")
                    if count >= json.loads(child[1])["attempt_allocation"]:
                        raise ReceiptConflictError("Child attempt allocation exhausted")
                    if family_count >= parent_policy["max_task_attempts"] - proposal.draft.parent_attempt_reserve:
                        raise ReceiptConflictError("Parent verification reserve protected")
                else:
                    unused_money = sum(
                        max(
                            0,
                            json.loads(sibling[1])["budget_allocation_usd"]
                            - conn.execute(
                                "SELECT COALESCE(SUM(MAX(COALESCE(json_extract(receipt_json,'$.known_cost_usd'),0),COALESCE(json_extract(receipt_json,'$.budget_reserved_usd'),0))),0) FROM research_provider_attempts WHERE task_id=?",
                                (sibling[0],),
                            ).fetchone()[0],
                        )
                        for sibling in siblings
                        if sibling[2] in {"allocated", "running"}
                    )
                    if max(family_spend, budget_row[1] or 0) + ceiling + unused_money > ceiling_budget:
                        raise ReceiptConflictError("Approved child monetary allocations protected")
                    unused = sum(
                        max(
                            0,
                            json.loads(sibling[1])["attempt_allocation"]
                            - conn.execute(
                                "SELECT COUNT(*) FROM research_provider_attempts WHERE task_id=?", (sibling[0],)
                            ).fetchone()[0],
                        )
                        for sibling in siblings
                        if sibling[2] in {"allocated", "running"}
                    )
                    if family_count + unused >= parent_policy["max_task_attempts"]:
                        raise ReceiptConflictError("Approved child allocations protected")
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
                "budget_reserved_usd",
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
