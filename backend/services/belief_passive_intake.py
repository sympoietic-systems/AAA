"""T7 origin membrane: bounded passive observations, no semantic/adoption authority."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from backend.errors import SecurityViolation, ValidationGlitch
from backend.services.belief_explicit_intake import EmissionAnnotations
from backend.services.belief_review_contracts import Assessment, Encounter, LineageEntry, SourceReference
from backend.services.belief_review_store import BeliefReviewStore, _agent, _json
from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository
from backend.storage.repositories.conversation.conversation import ConversationRepository
from backend.storage.repositories.conversation.message import MessageRepository

PassiveOrigin = Literal["passive_chat", "conversation_pattern", "scar_fold"]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def passive_intake(
    db_path: str,
    agent_id: str,
    statement: str,
    *,
    origin: PassiveOrigin,
    source_id: str,
    segment_id: str,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Sync use case; async callers offload once. None allows only unpromoted legacy routing."""
    settings = config.get("belief_review", {})
    if not isinstance(settings, dict) or not isinstance(settings.get("origin_intake", {}), dict):
        raise ValidationGlitch("Origin settings must be mappings", entity="belief_intake")
    enabled = settings.get("origin_intake", {}).get(origin, False)
    if type(enabled) is not bool or origin not in {"passive_chat", "conversation_pattern", "scar_fold"}:
        raise ValidationGlitch("Passive origin requires a boolean flag and known origin", entity="belief_intake")
    agent_id = _agent(agent_id)
    repo = ExplicitBeliefRepository(db_path)
    if not enabled and not repo.promoted(agent_id, origin):
        return None
    conversation_id = None
    issues = ["scope_and_temporal_scope_unresolved"]
    if origin == "conversation_pattern":
        source = SourceReference(
            source_type="conversation_pattern",
            source_id=source_id,
            source_sha256=_hash(statement),
            activity="internal",
            context_status="missing",
            unavailable_reason="Originating conversation/messages not supplied; artifact hash is not source provenance",
        )
        issues.append("originating_messages_unavailable")
        lineage = (
            LineageEntry(
                source_id=source_id,
                source_sha256=_hash(statement),
                independence_status="internal",
                uncertainty="Pattern ancestry unknown",
            ),
        )
    else:
        if not source_id.isdecimal():
            raise ValidationGlitch("Message origin requires a stored message ID", entity="belief_intake")
        message = MessageRepository(db_path).get_by_id(int(source_id))
        conv = ConversationRepository(db_path).get(message.conversation_id) if message else None
        if not message or not conv or str(conv.agent_id).lower() != agent_id:
            raise SecurityViolation("Passive source requires the owning agent message", entity="belief_intake")
        if origin == "scar_fold" and message.speaker != "apparatus":
            raise SecurityViolation("Scar-fold source must be apparatus reflection", entity="belief_intake")
        conversation_id = message.conversation_id
        available = statement in message.content
        if not available:
            issues.append("source_quote_not_found")
        internal = message.speaker == "apparatus" or origin == "scar_fold"
        source = SourceReference(
            source_type="message",
            source_id=source_id,
            source_sha256=_hash(message.content),
            activity="internal" if internal else "unknown",
            context_status="available" if available else "ambiguous",
            quote=statement[:2000] if available else "",
            reference=f"{conversation_id}/message/{source_id}",
            unavailable_reason="" if available else "Statement absent from stored source",
        )
        lineage = (
            LineageEntry(
                source_id=source_id,
                source_sha256=source.source_sha256,
                independence_status="internal" if internal else "unknown",
                uncertainty="Source ownership does not establish independent warrant",
            ),
        )
    identity = _hash(json.dumps([agent_id, origin, source_id, segment_id]))
    encounter_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "belief-passive:" + identity))
    assessment_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "belief-assessment:" + identity))
    encounter = Encounter(
        id=encounter_id,
        agent_id=agent_id,
        origin=origin,
        segment_id=segment_id,
        received_at=datetime.now(UTC),
        statement=statement,
        statement_sha256=_hash(statement),
        source=source,
        lineage=lineage,
    )
    annotation = EmissionAnnotations(
        label="scar-monologue-insight" if origin == "scar_fold" else origin.replace("_", "-"),
        rationale="Structural activity nominated this observation; novelty and warrant remain unassessed.",
        consequence="",
        evidence_quote=source.quote,
        conversation_id=conversation_id,
        parent_message_id=None,
        parent_sha256=None,
        context_issues=tuple(issues),
    )
    annotation_json = _json(annotation)
    _json(encounter)
    repo.promote(agent_id, origin, encounter.received_at.isoformat())
    store = BeliefReviewStore(db_path)
    saved = store._register(encounter)
    repo.annotate(agent_id, saved.encounter.id, assessment_id, annotation_json)
    pending = Assessment(
        id=assessment_id,
        agent_id=agent_id,
        encounter_id=saved.encounter.id,
        candidate_id=saved.record_id,
        policy_version="belief-v2-passive-deferred",
        rubric_version="passive-context-v1",
        context_hash=_hash(annotation_json),
        referent_status="unknown",
        evaluator_status="pending",
        started_at=saved.encounter.received_at,
        exclusions=tuple(issues),
    )
    current = store._start_assessment(pending)
    if current.evaluator_status == "pending":
        repo.trace(agent_id, saved.encounter.id, "received")
        done = Assessment.model_validate(
            current.model_dump()
            | {
                "evaluator_status": "abstained",
                "completed_at": current.started_at,
                "abstain_reason": "v2_evaluator_pending_T9" if enabled else "origin_paused",
            }
        )
        repo.complete(store._assessment_write(done))
    repo.trace(agent_id, saved.encounter.id, "assessed")
    return repo.projection(agent_id, saved.encounter.id)
