"""Two approved gathering scopes deliver archives to the parent Cortex."""

import asyncio
import json

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import ConsolidatePayload, StepEnvelope, StepOutput
from backend.storage.repositories.research.action_receipt import ReceiptConflictError
from backend.storage.repositories.research.child_run import ResearchChildRunRepository
from backend.storage.research_branch_proposal import BranchScope
from backend.storage.research_children import ChildEvidencePacket
from backend.storage.research_evidence import EvidenceBundle


class BranchGatherStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "branch_gathering"

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        parent_id = envelope.task_id
        state = orch._get_state(parent_id)
        action_id = state["active_action_id"]
        repo = ResearchChildRunRepository(orch.task_repo._db_path)
        children = await asyncio.to_thread(repo.allocate, parent_id, action_id)

        async def gather(row: dict) -> ChildEvidencePacket:
            child_id = row["child_task_id"]
            if row["packet_json"]:
                return ChildEvidencePacket.model_validate_json(row["packet_json"])
            started = await asyncio.to_thread(repo.start, child_id, action_id)
            if not started:
                current = await asyncio.to_thread(repo.list_parent, parent_id)
                return ChildEvidencePacket.model_validate_json(
                    next(item["packet_json"] for item in current if item["child_task_id"] == child_id)
                )
            child_state = await asyncio.to_thread(orch.init_task, child_id)
            status = "complete"
            objections = []
            try:
                # Only these three actions are reachable for a child; no recursive planning.
                for _ in range(3):
                    parent = await asyncio.to_thread(orch.task_repo.get, parent_id)
                    if not parent or parent["status"] != "active":
                        raise asyncio.CancelledError
                    if child_state["phase"] == "complete":
                        break
                    result = await orch.execute_step(child_id)
                    if result.get("status") in {"failed", "error"}:
                        status = "failed"
                        break
                if child_state.get("delivery_degraded"):
                    status = "partial" if status == "complete" else status
                if not child_state.get("all_findings"):
                    status = "partial" if status == "complete" else status
                    objections.append("no_child_interpretations")
            except asyncio.CancelledError:
                await asyncio.to_thread(repo.cancel_parent, parent_id)
                raise
            except (OSError, ValueError, RuntimeError) as exc:
                status = "failed"
                objections.append(type(exc).__name__)
            bundle = EvidenceBundle.model_validate(
                await asyncio.to_thread(orch._evidence_store.repo.export_bundle, child_id)
            )
            packet = ChildEvidencePacket(
                child_task_id=child_id,
                parent_task_id=parent_id,
                proposal_id=row["proposal_id"],
                scope=BranchScope.model_validate_json(row["allocation_json"]),
                status=status,
                evidence=bundle,
                interpretations=tuple(child_state.get("all_findings", [])[:100]),
                unresolved_objections=tuple(objections + ["child_semantic_support_unreviewed"]),
            )
            await asyncio.to_thread(repo.finish, packet, action_id)
            return packet

        # Run sequentially: preserves parent execution capacity and avoids inherited
        # legacy fixture/database concurrency. Fanout stays exactly two durable scopes.
        packets = []
        for row in children:
            try:
                packets.append(await gather(row))
            except ReceiptConflictError:
                await asyncio.to_thread(repo.cancel_parent, parent_id)
                raise
        overlaps: dict[str, list[str]] = {}
        for packet in packets:
            for source in packet.evidence.sources:
                identity = (
                    (source.artifact.canonical_url or source.artifact.authorized_file_id or "")
                    + ":"
                    + (source.artifact.representation_hash or "unavailable")
                )
                overlaps.setdefault(identity, []).append(packet.child_task_id)
        # Full spans/claim edges/exclusions remain in the immutable archives. The
        # prompt view is bounded and explicitly untrusted; agreement is not a vote.
        state["child_evidence_context"] = json.dumps(
            [
                {
                    "child_task_id": p.child_task_id,
                    "scope": p.scope.model_dump(),
                    "status": p.status,
                    "claims": [c.model_dump(mode="json") for c in p.evidence.claims[:30]],
                    "segments": [s.model_dump(mode="json") for s in p.evidence.segments[:20]],
                    "decisions": [d.model_dump(mode="json") for d in p.evidence.decisions[:20]],
                    "objections": p.unresolved_objections,
                    "shared_source_groups": {
                        identity: sorted(set(ids)) for identity, ids in overlaps.items() if len(set(ids)) > 1
                    },
                }
                for p in packets
            ],
            ensure_ascii=False,
        )
        already_merged = set(state.get("merged_child_ids", []))
        new_findings = [
            f"[Unreviewed child {p.scope.scope_id}; norm={p.scope.validation_norm}] {item}"
            for p in packets
            if p.child_task_id not in already_merged
            for item in p.interpretations
        ]
        state["merged_child_ids"] = sorted({*already_merged, *(p.child_task_id for p in packets)})
        return StepOutput(
            status="completed" if all(p.status == "complete" for p in packets) else "partial",
            payload=ConsolidatePayload(),
            new_findings=new_findings,
            message="Approved child evidence archived; parent Cortex owns the diffractive merge",
        )
