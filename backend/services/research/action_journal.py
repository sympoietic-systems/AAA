"""Journal legacy execution; interrupted side effects cannot be replayed safely."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from backend.services.research.task_state import serialize_research_state
from backend.storage.repositories.research.action_receipt import ResearchActionReceiptRepository
from backend.storage.research_receipts import (
    ActionObservation,
    ActionStatus,
    EvidencePacket,
    ProviderAttemptReceipt,
    ResearchActionReceipt,
)


class InterruptedResearchActionError(RuntimeError):
    """Previous execution requires explicit recovery before spending again."""


def input_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


class ResearchActionJournal:
    def __init__(self, repo: ResearchActionReceiptRepository):
        self.repo = repo

    def begin(self, task_id: str, state: dict[str, Any], phase: str, inputs: object) -> ResearchActionReceipt:
        if state.get("active_action_id"):
            raise InterruptedResearchActionError(
                "Interrupted research action requires explicit recovery; automatic replay blocked"
            )
        now = datetime.now(UTC)
        policy = state["action_journal_policy"]
        if policy.get("scheduler_version") == 1 and state.get("last_action_id"):
            dependency = self.repo.get(task_id, state["last_action_id"])
            if dependency is None or dependency.status not in {"complete", "partial"}:
                raise InterruptedResearchActionError("Action dependency is absent or unsuccessful")
        receipt = ResearchActionReceipt(
            action_id=str(uuid.uuid4()),
            task_id=task_id,
            kind=phase,
            intent="legacy_phase",
            input_version=input_hash({"envelope": inputs, "scheduler": state.get("scheduler_state")})
            if policy.get("scheduler_version") == 1
            else input_hash(inputs),
            dependency_ids=(state["last_action_id"],) if state.get("last_action_id") else (),
            rationale=((state.get("scheduler_state") or {}).get("decisions") or [{}])[-1].get("rejection")
            or "Execute registered phase with validated prerequisites and persisted predecessor",
            budget_reserved=0,
            deadline=policy.get("provider_policy", {}).get("deadline"),
            contract_hash=policy["contract_hash"],
            policy_hash=policy["policy_hash"],
        ).transition("running", now)
        checkpoint = {
            **state,
            "active_action_id": receipt.action_id,
            "research_started_at": state.get("research_started_at") or now.isoformat(),
        }
        self.repo.checkpoint(receipt, serialize_research_state(checkpoint), starting=True)
        state.update(checkpoint)
        return receipt

    def finish(
        self,
        receipt: ResearchActionReceipt,
        state: dict[str, Any],
        status: ActionStatus,
        output_refs: tuple[str, ...],
        elapsed: float,
        useful: bool,
        provider_attempts: tuple[ProviderAttemptReceipt, ...] = (),
        evidence_packets: tuple[EvidencePacket, ...] = (),
    ) -> None:
        now = datetime.now(UTC)
        checkpoint = {**state, "active_action_id": None, "last_action_id": receipt.action_id}
        if status in {"failed", "cancelled"} and checkpoint.get("phase") == "waiting_for_branch_approval":
            checkpoint.update(phase="complete", pending_branch_proposal_id=None)
        if useful and checkpoint.get("first_useful_result_seconds") is None:
            started = datetime.fromisoformat(checkpoint["research_started_at"])
            checkpoint["first_useful_result_seconds"] = max(0, (now - started).total_seconds())
        children = []
        if receipt.kind == "branch_gathering":
            from backend.storage.repositories.research.child_run import ResearchChildRunRepository

            children = ResearchChildRunRepository(self.repo._db_path).list_parent(receipt.task_id)
        terminal = receipt.transition(
            status,
            now,
            ActionObservation(
                output_refs=output_refs,
                phase_elapsed_seconds=elapsed,
                provider_attempts=provider_attempts,
                evidence_packets=evidence_packets,
                acquisition_ids=self.acquisition_ids(receipt),
                scheduler_decision=((state.get("scheduler_state") or {}).get("decisions") or [None])[-1],
                branch_proposal_id=state.get("pending_branch_proposal_id"),
                child_task_ids=tuple(child["child_task_id"] for child in children),
                child_packet_hashes={
                    child["child_task_id"]: input_hash(json.loads(child["packet_json"]))
                    for child in children
                    if child["packet_json"]
                },
            ),
        )
        self.repo.checkpoint(terminal, serialize_research_state(checkpoint))
        state.update(checkpoint)

    def acquisition_ids(self, receipt: ResearchActionReceipt) -> tuple[str, ...]:
        from backend.storage.repositories.research.acquisition import ResearchAcquisitionRepository

        acquisitions = ResearchAcquisitionRepository(self.repo._db_path).list_action(receipt.task_id, receipt.action_id)
        return tuple(item.acquisition_id for item in acquisitions)
