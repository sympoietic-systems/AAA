"""Explicit, idempotent V1 proposal replay into the V2 encounter/assessment ledger."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC

from backend.services.belief_assessment import assess_encounter
from backend.services.belief_review_contracts import Encounter, LineageEntry, SourceReference
from backend.services.belief_review_store import BeliefReviewStore
from backend.storage.models import BeliefProposal

LEGACY_CONTEXT_GAP = "V1 proposal has no verified message-bound source or scope/time context"


@dataclass(frozen=True)
class ReplayOutcome:
    encounter_id: str
    record_id: str
    created: bool
    assessment_id: str
    assessment_status: str
    assessment_reason: str


def proposal_snapshot_sha256(proposal: BeliefProposal) -> str:
    """Bind exact V1 fields without treating them as V2 evidence or instructions."""
    snapshot = {
        "id": proposal.id,
        "agent_id": proposal.agent_id.lower(),
        "status": proposal.status,
        "provisional_statement": proposal.provisional_statement,
        "suggested_statement": proposal.suggested_statement,
        "suggested_label": proposal.suggested_label,
        "potential_merge_target": proposal.potential_merge_target,
        "symbia_reflection": proposal.symbia_reflection,
        "symbia_friction_rationale": proposal.symbia_friction_rationale,
        "rejection_rationale": proposal.rejection_rationale,
        "source_trace": proposal.source_trace,
        "initial_signature": proposal.initial_signature,
        "nucleation_mass": proposal.nucleation_mass,
        "confidence": proposal.confidence,
        "created_at": proposal.created_at.isoformat(),
        "updated_at": proposal.updated_at.isoformat(),
    }
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def encounter_for_proposal(proposal: BeliefProposal) -> Encounter:
    """Build a V2 encounter that keeps legacy uncertainty explicit."""
    snapshot_hash = proposal_snapshot_sha256(proposal)
    created_at = proposal.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return Encounter(
        agent_id=proposal.agent_id.lower(),
        id=f"legacy-v1:{proposal.id}",
        origin="legacy_v1_replay",
        segment_id=f"v1-proposal:{proposal.id}",
        received_at=created_at,
        statement=proposal.provisional_statement,
        statement_sha256=hashlib.sha256(proposal.provisional_statement.encode("utf-8")).hexdigest(),
        scope="unknown",
        temporal_scope="unknown",
        source=SourceReference(
            source_type="legacy_v1_proposal",
            context_status="ambiguous",
            activity="unknown",
            source_id=proposal.id,
            source_version="v1-snapshot-v1",
            source_sha256=snapshot_hash,
            reference=f"belief_proposals/{proposal.id}",
            unavailable_reason=LEGACY_CONTEXT_GAP,
        ),
        lineage=(
            LineageEntry(
                source_id=proposal.id,
                source_sha256=snapshot_hash,
                independence_status="unknown",
                uncertainty=LEGACY_CONTEXT_GAP,
            ),
        ),
        candidate_id=proposal.id,
        trigger="unknown",
    )


async def replay_proposal(db_path: str, proposal: BeliefProposal) -> ReplayOutcome:
    """Attach one legacy proposal to V2 and record its bounded assessment outcome.

    Assessment is deliberately disabled here. With no source-bound scope/time,
    the V2 assessment contract must abstain before any provider call.
    """
    encounter = encounter_for_proposal(proposal)
    saved = await BeliefReviewStore(db_path).register(encounter)
    assessment = await assess_encounter(
        db_path,
        encounter.agent_id,
        encounter.id,
        config={},
        attempt_id="legacy-v1-replay",
    )
    return ReplayOutcome(
        encounter_id=encounter.id,
        record_id=saved.record_id,
        created=saved.created,
        assessment_id=assessment.id,
        assessment_status=assessment.evaluator_status,
        assessment_reason=assessment.abstain_reason,
    )
