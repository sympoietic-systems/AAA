"""Atomic proposal resolution; waiting is a durable state without child spend."""

import json
from datetime import UTC, datetime
from typing import Any

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.research.action_receipt import ReceiptConflictError
from backend.storage.research_branch_proposal import BranchProposal, BranchProposalDraft, BranchScope
from backend.storage.research_evidence import ResearchContract


class ResearchBranchProposalRepository(BaseRepository):
    @with_connection
    def abandon_cancelled_parent(self, task_id: str) -> None:
        with self.atomic():
            task = (
                self._conn()
                .execute("SELECT status,orchestrator_state FROM research_tasks WHERE id=?", (task_id,))
                .fetchone()
            )
            if task is None or task[0] != "cancelled":
                raise ReceiptConflictError("Only a cancelled parent can abandon a pending proposal")
            proposal = self.current(task_id)
            if proposal is None or proposal.status != "pending":
                return
            terminal = proposal.model_copy(
                update={"status": "declined", "resolved_at": datetime.now(UTC), "resolution_reason": "parent_cancelled"}
            )
            self._conn().execute(
                "UPDATE research_branch_proposals SET proposal_json=?,status='declined' WHERE proposal_id=? AND status='pending'",
                (terminal.model_dump_json(), terminal.proposal_id),
            )
            state = json.loads(task[1])
            state.update(phase="complete", pending_branch_proposal_id=None)
            self._conn().execute(
                "UPDATE research_tasks SET orchestrator_state=? WHERE id=?", (json.dumps(state), task_id)
            )

    def _capacity(self, task: dict[str, Any], state: dict[str, Any], draft: BranchProposalDraft) -> None:
        policy = state["action_journal_policy"]["provider_policy"]
        attempts = (
            self._conn()
            .execute("SELECT COUNT(*) FROM research_provider_attempts WHERE task_id=?", (task["id"],))
            .fetchone()[0]
        )
        if (
            sum(scope.attempt_allocation for scope in draft.scopes) + draft.parent_attempt_reserve
            > policy["max_task_attempts"] - attempts
        ):
            raise ReceiptConflictError("Branch allocation consumes the parent attempt reserve")
        contract_row = (
            self._conn()
            .execute(
                "SELECT contract_json FROM research_contracts WHERE task_id=? AND revision=?",
                (task["id"], state.get("contract_revision", 1)),
            )
            .fetchone()
        )
        if contract_row is None:
            raise ReceiptConflictError("Branch allocation requires the frozen parent contract")
        contract = ResearchContract.model_validate_json(contract_row[0])
        ceiling = min(task["budget_limit_usd"], contract.resource_ceilings.get("budget_limit_usd", 0))
        remaining = max(0, ceiling - (task.get("budget_spent_usd") or 0))
        if sum(scope.budget_allocation_usd for scope in draft.scopes) + draft.parent_budget_reserve_usd > remaining:
            raise ReceiptConflictError("Branch allocation exceeds remaining parent budget")

    @with_connection
    def create(self, proposal: BranchProposal) -> BranchProposal:
        from backend.storage.repositories.research.evidence import ResearchEvidenceRepository

        with self.atomic():
            row = self._conn().execute("SELECT * FROM research_tasks WHERE id=?", (proposal.task_id,)).fetchone()
            if row is None:
                raise ReceiptConflictError("Parent task is absent")
            task = dict(row)
            state = json.loads(task["orchestrator_state"])
            policy = state.get("action_journal_policy") or {}
            if (
                task["status"] != "active"
                or policy.get("subresearch_policy", "off") != "propose"
                or state.get("active_action_id") != proposal.action_id
            ):
                raise ReceiptConflictError("Branch proposal is not authorized by the active parent action")
            now = datetime.now(UTC)
            deadline = datetime.fromisoformat(policy["provider_policy"]["deadline"])
            if (
                not now < proposal.expires_at <= deadline
                or proposal.status != "pending"
                or proposal.parent_objective != task["objective"]
            ):
                raise ReceiptConflictError("Invalid proposal boundary or expiry")
            action = (
                self._conn()
                .execute(
                    "SELECT receipt_json FROM research_action_receipts WHERE action_id=? AND task_id=?",
                    (proposal.action_id, proposal.task_id),
                )
                .fetchone()
            )
            if action is None or json.loads(action[0])["kind"] not in {
                "reflection",
                "pure_reflection",
                "consolidating",
                "digesting",
                "document_digestion",
            }:
                raise ReceiptConflictError("Proposal requires post-afferent inspection")
            snapshot = ResearchEvidenceRepository(self._db_path).afferent_snapshot(proposal.task_id)
            anchors = {segment_id for item in snapshot for segment_id in item["segment_ids"]}
            if not set(proposal.draft.witness_segment_ids) <= anchors:
                raise ReceiptConflictError("Proposal lacks current durable afferent anchors")
            self._capacity(task, state, proposal.draft)
            existing = (
                self._conn()
                .execute(
                    "SELECT proposal_json FROM research_branch_proposals WHERE proposal_id=?", (proposal.proposal_id,)
                )
                .fetchone()
            )
            if existing:
                if BranchProposal.model_validate_json(existing[0]) != proposal:
                    raise ReceiptConflictError("Proposal identity is immutable")
                return proposal
            if (
                self._conn()
                .execute("SELECT 1 FROM research_branch_proposals WHERE task_id=?", (proposal.task_id,))
                .fetchone()
            ):
                raise ReceiptConflictError("MVP permits one proposal per parent task")
            self._conn().execute(
                "INSERT INTO research_branch_proposals VALUES (?,?,?,?,?)",
                (proposal.proposal_id, proposal.task_id, proposal.action_id, proposal.model_dump_json(), "pending"),
            )
            return proposal

    @with_connection
    def current(self, task_id: str) -> BranchProposal | None:
        row = (
            self._conn()
            .execute(
                "SELECT proposal_json FROM research_branch_proposals WHERE task_id=? ORDER BY rowid DESC LIMIT 1",
                (task_id,),
            )
            .fetchone()
        )
        return BranchProposal.model_validate_json(row[0]) if row else None

    @with_connection
    def expired_waiting(self) -> list[tuple[str, str]]:
        rows = (
            self._conn()
            .execute(
                "SELECT p.proposal_json FROM research_branch_proposals p JOIN research_tasks t ON t.id=p.task_id WHERE p.status='pending' AND t.status='waiting_for_branch_approval' ORDER BY p.rowid LIMIT 256"
            )
            .fetchall()
        )
        now = datetime.now(UTC)
        proposals = [BranchProposal.model_validate_json(row[0]) for row in rows]
        return [(item.task_id, item.proposal_id) for item in proposals if item.expires_at <= now][:32]

    @with_connection
    def resolve(
        self,
        task_id: str,
        proposal_id: str,
        decision: str,
        *,
        scopes: tuple[BranchScope, ...] | None = None,
        boundary_acknowledged: bool = False,
        manual: bool = False,
    ) -> BranchProposal:
        with self.atomic():
            proposal = self.current(task_id)
            if proposal is None or proposal.proposal_id != proposal_id:
                raise ReceiptConflictError("Proposal is absent")
            if proposal.status != "pending":
                if proposal.status == decision:
                    if decision == "approved" and (scopes or proposal.draft.scopes) != proposal.approved_scopes:
                        raise ReceiptConflictError("Approved scopes are immutable")
                    return proposal
                raise ReceiptConflictError("Proposal already resolved")
            task_row = self._conn().execute("SELECT * FROM research_tasks WHERE id=?", (task_id,)).fetchone()
            if task_row is None:
                raise ReceiptConflictError("Parent task is absent")
            task = dict(task_row)
            state = json.loads(task["orchestrator_state"])
            if task["status"] != "waiting_for_branch_approval" or state.get("active_action_id"):
                raise ReceiptConflictError("Parent is not ready for proposal review")
            now = datetime.now(UTC)
            expired = now >= proposal.expires_at
            status = "expired" if expired else decision
            if status not in {"approved", "declined", "expired"} or status == "expired" and not expired:
                raise ReceiptConflictError("Invalid proposal decision")
            approved = None
            if status == "approved":
                if not boundary_acknowledged:
                    raise ReceiptConflictError("Approval requires review within the parent objective")
                approved = scopes or proposal.draft.scopes
                draft = BranchProposalDraft.model_validate({**proposal.draft.model_dump(), "scopes": approved})
                self._capacity(task, state, draft)
                from backend.storage.repositories.research.evidence import ResearchEvidenceRepository

                anchors = {
                    segment_id
                    for item in ResearchEvidenceRepository(self._db_path).afferent_snapshot(task_id)
                    for segment_id in item["segment_ids"]
                }
                if not set(proposal.draft.witness_segment_ids) <= anchors:
                    raise ReceiptConflictError("Proposal witnesses expired; decline to continue the parent line")

            resolved = proposal.model_copy(
                update={
                    "status": status,
                    "resolved_at": now,
                    "reviewed_by": "user" if status != "expired" else None,
                    "approved_scopes": approved,
                    "resolution_reason": "expiry" if status == "expired" else "human_review",
                }
            )
            self._conn().execute(
                "UPDATE research_branch_proposals SET proposal_json=?,status=? WHERE proposal_id=? AND status='pending'",
                (resolved.model_dump_json(), status, proposal_id),
            )
            state["pending_branch_proposal_id"] = None
            state["approved_branch_proposal_id"] = proposal_id if status == "approved" else None
            deadline = datetime.fromisoformat(state["action_journal_policy"]["provider_policy"]["deadline"])
            state["phase"] = proposal.resume_phase if now < deadline else "complete"
            if now >= deadline:
                state["delivery_degraded"] = True
                state["stop_reason"] = "parent_deadline_expired_while_waiting"
            new_status = "partial" if now >= deadline else "active" if manual else "queued"
            self._conn().execute(
                "UPDATE research_tasks SET orchestrator_state=?,status=? WHERE id=?",
                (json.dumps(state), new_status, task_id),
            )
            return resolved
