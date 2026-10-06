"""Allocate exactly the approved scopes; no allocation reset on restart."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from backend.services.research.action_journal import input_hash
from backend.services.research.evidence_store import ResearchEvidenceStore
from backend.services.research.task_state import make_initial_state, serialize_research_state
from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.research.action_receipt import ReceiptConflictError
from backend.storage.repositories.research.branch_proposal import ResearchBranchProposalRepository
from backend.storage.research_children import ChildEvidencePacket


class ResearchChildRunRepository(BaseRepository):
    @with_connection
    def list_parent(self, parent_id: str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self._conn()
            .execute("SELECT * FROM research_child_runs WHERE parent_task_id=? ORDER BY scope_id LIMIT 2", (parent_id,))
            .fetchall()
        ]

    @with_connection
    def allocate(self, parent_id: str, action_id: str) -> list[dict[str, Any]]:
        with self.atomic():
            conn = self._conn()
            row = conn.execute("SELECT * FROM research_tasks WHERE id=?", (parent_id,)).fetchone()
            if row is None:
                raise ReceiptConflictError("Parent is absent")
            parent = dict(row)
            state = json.loads(parent["orchestrator_state"])
            policy = state.get("action_journal_policy") or {}
            action = conn.execute(
                "SELECT receipt_json,status FROM research_action_receipts WHERE task_id=? AND action_id=?",
                (parent_id, action_id),
            ).fetchone()
            if (
                parent["status"] != "active"
                or state.get("active_action_id") != action_id
                or not action
                or action[1] != "running"
                or json.loads(action[0])["kind"] != "branch_gathering"
                or policy.get("child_execution_version") != 1
            ):
                raise ReceiptConflictError("Allocation requires the current parent gathering action")
            if conn.execute("SELECT 1 FROM research_child_runs WHERE child_task_id=?", (parent_id,)).fetchone():
                raise ReceiptConflictError("Grandchildren are forbidden")
            proposal = ResearchBranchProposalRepository(self._db_path).current(parent_id)
            if (
                not proposal
                or proposal.status != "approved"
                or not proposal.approved_scopes
                or state.get("approved_branch_proposal_id") != proposal.proposal_id
            ):
                raise ReceiptConflictError("Child execution requires approved scopes")
            if datetime.now(UTC) >= datetime.fromisoformat(policy["provider_policy"]["deadline"]):
                raise ReceiptConflictError("Parent deadline exhausted")
            existing = self.list_parent(parent_id)
            if existing:
                if len(existing) != 2 or any(item["proposal_id"] != proposal.proposal_id for item in existing):
                    raise ReceiptConflictError("Child allocation identity changed")
                return existing
            draft = proposal.draft.model_copy(update={"scopes": proposal.approved_scopes})
            ResearchBranchProposalRepository(self._db_path)._capacity(parent, state, draft)
            for scope in proposal.approved_scopes:
                child_id = str(uuid.uuid5(uuid.NAMESPACE_URL, proposal.proposal_id + ":" + scope.scope_id))
                child_task = {
                    "objective": scope.question,
                    "max_depth": 1,
                    "budget_limit_usd": scope.budget_allocation_usd,
                    "orchestrator_state": json.dumps(
                        {
                            "phase": "searching",
                            "plan": {"search_queries": [scope.question + " " + " ".join(scope.retrieval_vocabulary)]},
                        }
                    ),
                }
                child_state = make_initial_state(child_task)
                child_state["research_child"] = {
                    "parent_task_id": parent_id,
                    "proposal_id": proposal.proposal_id,
                    "scope": scope.model_dump(mode="json"),
                    "parent_objective": parent["objective"],
                }
                contract = ResearchEvidenceStore.initial_contract(child_id, child_state, 7)
                child_policy = {
                    **policy,
                    "subresearch_policy": "off",
                    "child_execution_version": 0,
                    "contract_hash": contract.content_hash(),
                    "policy_hash": input_hash({"parent_policy": policy["policy_hash"], "scope": scope.model_dump()}),
                    "provider_policy": {
                        **policy["provider_policy"],
                        "max_task_attempts": scope.attempt_allocation,
                        "max_request_attempts": min(
                            policy["provider_policy"]["max_request_attempts"], scope.attempt_allocation
                        ),
                    },
                }
                child_state["action_journal_policy"] = child_policy
                conn.execute(
                    """INSERT INTO research_tasks
                    (id,title,objective,trigger_source,status,priority,max_depth,max_breadth,budget_limit_usd,orchestrator_state,subresearch_policy)
                    VALUES (?,?,?,'approved_child','active',1,1,1,?,?,'off')""",
                    (
                        child_id,
                        scope.question[:200],
                        scope.question,
                        scope.budget_allocation_usd,
                        serialize_research_state(child_state),
                    ),
                )
                conn.execute(
                    "INSERT INTO research_contracts VALUES (?,?,?,?)",
                    (child_id, 1, contract.content_hash(), contract.model_dump_json()),
                )
                conn.execute(
                    "INSERT INTO research_child_runs (child_task_id,parent_task_id,proposal_id,scope_id,allocation_json,parent_action_id) VALUES (?,?,?,?,?,?)",
                    (child_id, parent_id, proposal.proposal_id, scope.scope_id, scope.model_dump_json(), action_id),
                )
            return self.list_parent(parent_id)

    @with_connection
    def start(self, child_id: str, parent_action_id: str) -> bool:
        with self.atomic():
            row = (
                self._conn().execute("SELECT * FROM research_child_runs WHERE child_task_id=?", (child_id,)).fetchone()
            )
            if not row:
                raise ReceiptConflictError("Child allocation is absent")
            if row["packet_json"]:
                return False
            parent = (
                self._conn()
                .execute("SELECT status,orchestrator_state FROM research_tasks WHERE id=?", (row["parent_task_id"],))
                .fetchone()
            )
            if not parent or parent[0] != "active" or json.loads(parent[1]).get("active_action_id") != parent_action_id:
                raise ReceiptConflictError("Parent ownership was lost")
            if row["status"] == "running":
                raise ReceiptConflictError("Interrupted child requires explicit recovery")
            if row["status"] != "allocated":
                raise ReceiptConflictError("Child allocation was revoked")
            self._conn().execute(
                "UPDATE research_child_runs SET status='running',parent_action_id=? WHERE child_task_id=?",
                (parent_action_id, child_id),
            )
            return True

    @with_connection
    def finish(self, packet: ChildEvidencePacket, parent_action_id: str) -> None:
        if packet.evidence.task_id != packet.child_task_id:
            raise ReceiptConflictError("Child packet changed evidence ownership")
        with self.atomic():
            conn = self._conn()
            row = conn.execute(
                "SELECT * FROM research_child_runs WHERE child_task_id=?", (packet.child_task_id,)
            ).fetchone()
            if (
                not row
                or row["parent_task_id"] != packet.parent_task_id
                or row["proposal_id"] != packet.proposal_id
                or json.loads(row["allocation_json"]) != packet.scope.model_dump(mode="json")
            ):
                raise ReceiptConflictError("Child packet changed its allocation")
            if row["packet_json"]:
                if ChildEvidencePacket.model_validate_json(row["packet_json"]) != packet:
                    raise ReceiptConflictError("Child delivery is immutable")
                return
            if row["status"] != "running":
                raise ReceiptConflictError("Child delivery authority was revoked")
            parent = conn.execute(
                "SELECT status,orchestrator_state FROM research_tasks WHERE id=?", (packet.parent_task_id,)
            ).fetchone()
            state = json.loads(parent[1]) if parent else {}
            if (
                not parent
                or parent[0] != "active"
                or state.get("active_action_id") != parent_action_id
                or row["parent_action_id"] != parent_action_id
            ):
                raise ReceiptConflictError("Late child delivery lost parent ownership")
            if (
                datetime.now(UTC)
                >= datetime.fromisoformat(state["action_journal_policy"]["provider_policy"]["deadline"])
                and packet.status == "complete"
            ):
                raise ReceiptConflictError("Late child cannot deliver complete evidence")
            conn.execute(
                "UPDATE research_child_runs SET status=?,packet_json=? WHERE child_task_id=?",
                (packet.status, packet.model_dump_json(), packet.child_task_id),
            )
            conn.execute(
                "UPDATE research_tasks SET status=? WHERE id=?",
                ("completed" if packet.status == "complete" else packet.status, packet.child_task_id),
            )

    @with_connection
    def cancel_parent(self, parent_id: str) -> None:
        """Revoke child authority before a cancellation-resistant call can finish."""
        with self.atomic():
            for row in self.list_parent(parent_id):
                if row["packet_json"] is None:
                    self._conn().execute(
                        "UPDATE research_child_runs SET status='cancelled' WHERE child_task_id=?",
                        (row["child_task_id"],),
                    )
                    self._conn().execute(
                        "UPDATE research_tasks SET status='cancelled' WHERE id=?", (row["child_task_id"],)
                    )
