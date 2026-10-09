"""Opt-in explicit-origin intake; source-bound checkpoints without evaluator/adoption authority."""

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal, cast

from pydantic import Field

from backend.errors import ResourceNotFound, SecurityViolation, ValidationGlitch
from backend.services.belief_admission_policy import Candidate, context_issues
from backend.services.belief_review_contracts import (
    Assessment,
    Encounter,
    FrozenRecord,
    LineageEntry,
    Sha256,
    SourceReference,
)
from backend.services.belief_review_store import BeliefReviewStore, _json
from backend.storage.repositories.cognitive.belief_admission import AdmissionRepository
from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository
from backend.storage.repositories.conversation.conversation import ConversationRepository
from backend.storage.repositories.conversation.message import MessageRepository


class EmissionAnnotations(FrozenRecord):
    label: str = Field(min_length=1, max_length=200)
    rationale: str = Field(max_length=2000)
    consequence: str = Field(max_length=1000)
    evidence_quote: str = Field(max_length=2000)
    emission_sha256: Sha256 | None = None
    conversation_id: str = Field(min_length=1, max_length=128)
    parent_message_id: int | None
    parent_sha256: Sha256 | None
    context_issues: tuple[str, ...] = Field(max_length=20)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def explicit_intake(
    db_path: str, conversation_id: str, message_id: int, data: dict[str, Any], *, config: dict[str, Any], origin: str
) -> dict[str, Any] | None:
    """None permits legacy intake only for an origin that has never been promoted."""
    # Entire use case is synchronous/offloaded: no provider port or network await.
    return await asyncio.to_thread(_explicit_intake, db_path, conversation_id, message_id, data, config, origin)


def _explicit_intake(
    db_path: str, conversation_id: str, message_id: int, data: dict[str, Any], config: dict[str, Any], origin: str
) -> dict[str, Any] | None:
    if origin not in {"chat", "dream"}:
        raise ValidationGlitch("Unknown explicit belief origin", entity="belief_intake")
    explicit_origin: Literal["explicit_chat", "explicit_dream"] = (
        "explicit_chat" if origin == "chat" else "explicit_dream"
    )
    settings = config.get("belief_review", {})
    if not isinstance(settings, dict) or not isinstance(settings.get("origin_intake", {}), dict):
        raise ValidationGlitch("Explicit origin settings must be mappings", entity="belief_intake")
    flags = settings.get("origin_intake", {})
    enabled = flags.get(explicit_origin, False)
    if type(enabled) is not bool:
        raise ValidationGlitch("Explicit origin flag must be boolean", entity="belief_intake")
    conv = ConversationRepository(db_path).get(conversation_id)
    if not conv or not conv.agent_id:
        raise SecurityViolation("Explicit belief conversation has no agent owner", entity="belief_intake")
    agent_id = conv.agent_id.lower()
    repo = ExplicitBeliefRepository(db_path)
    if not enabled and not repo.promoted(agent_id, explicit_origin):
        return None
    messages = MessageRepository(db_path)
    message = messages.get_by_id(message_id)
    if not message or message.conversation_id != conversation_id or message.speaker != "apparatus":
        raise SecurityViolation("Explicit emission requires the owning apparatus message", entity="belief_intake")
    candidate = Candidate.model_validate(data)
    parent = messages.get_by_id(message.parent_message_id) if message.parent_message_id else None
    parent_owned = parent is not None and parent.conversation_id == conversation_id
    source_text = parent.content if parent_owned and parent else ""
    issues = context_issues(candidate, source_text)
    if not parent_owned:
        issues.append("parent_context_unavailable")
    annotation = EmissionAnnotations(
        label=candidate.label,
        rationale=candidate.rationale,
        consequence=candidate.consequence,
        evidence_quote=candidate.evidence_quote,
        emission_sha256=data.get("emission_sha256"),
        conversation_id=conversation_id,
        parent_message_id=message.parent_message_id,
        parent_sha256=_hash(source_text) if parent_owned else None,
        context_issues=tuple(issues),
    )
    annotation_json = _json(annotation)
    fallback_segment = _hash(json.dumps(candidate.model_dump(), sort_keys=True, ensure_ascii=False))
    segment_id = str(data.get("segment_id") or "legacy:" + fallback_segment)
    identity = _hash(json.dumps([agent_id, explicit_origin, conversation_id, message_id, segment_id]))
    encounter_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "belief-explicit:" + identity))
    assessment_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "belief-assessment:" + identity))
    store = BeliefReviewStore(db_path)
    existing_candidate_id = None
    try:
        previous = store._get_encounter(agent_id, encounter_id)
        existing_candidate_id = previous.encounter.candidate_id
    except ResourceNotFound:
        if candidate.scope.strip() and candidate.temporal_scope.strip():
            for record in AdmissionRepository(db_path).comparisons(agent_id):
                if (
                    record["statement"] == candidate.statement
                    and record["scope"] == candidate.scope
                    and record["temporal_scope"] == candidate.temporal_scope
                ):
                    existing_candidate_id = str(record["id"])
                    break
    lineage = [
        LineageEntry(source_id=str(message_id), source_sha256=_hash(message.content), independence_status="internal")
    ]
    if parent_owned and parent:
        lineage.append(
            LineageEntry(
                source_id=str(parent.id),
                source_sha256=_hash(parent.content),
                independence_status="internal" if origin == "dream" or parent.speaker == "apparatus" else "unknown",
                uncertainty="Parent provenance alone does not establish independent warrant",
            )
        )
    encounter = Encounter(
        id=encounter_id,
        agent_id=agent_id,
        origin=explicit_origin,
        segment_id=segment_id,
        received_at=datetime.now(UTC),
        statement=candidate.statement,
        statement_sha256=_hash(candidate.statement),
        scope=candidate.scope,
        temporal_scope=candidate.temporal_scope,
        candidate_id=existing_candidate_id,
        trigger=cast(
            Literal["insight", "conflict", "counterexample", "evidence", "unknown"],
            candidate.trigger
            if candidate.trigger in {"insight", "conflict", "counterexample", "evidence"}
            else "unknown",
        ),
        source=SourceReference(
            source_type="message",
            source_id=str(message_id),
            source_sha256=_hash(message.content),
            activity="internal",
            context_status="ambiguous" if issues else "available",
            reference=f"{conversation_id}/message/{message_id}",
            unavailable_reason="; ".join(issues)[:500] if issues else "",
        ),
        lineage=tuple(lineage),
    )
    _json(encounter)
    # Promotion is an irreversible local routing marker, never a standing decision.
    repo.promote(agent_id, explicit_origin, encounter.received_at.isoformat())
    saved = store._register(encounter)
    repo.annotate(agent_id, saved.encounter.id, assessment_id, annotation_json)
    pending = Assessment(
        id=assessment_id,
        agent_id=agent_id,
        encounter_id=saved.encounter.id,
        candidate_id=saved.record_id,
        policy_version="belief-v2-explicit-deferred",
        rubric_version="explicit-context-v1",
        context_hash=_hash(annotation_json),
        referent_status="unknown" if not issues else "missing",
        evaluator_status="pending",
        started_at=saved.encounter.received_at,
        consequence_or_tension=candidate.consequence,
        exclusions=tuple(issues),
    )
    current = store._start_assessment(pending)
    if current.evaluator_status == "pending":
        repo.trace(agent_id, saved.encounter.id, "received")
        done = Assessment.model_validate(
            current.model_dump()
            | {
                "evaluator_status": "abstained" if issues else "unavailable",
                "completed_at": current.started_at,
                "abstain_reason": "origin_paused" if not enabled else "v2_evaluator_pending_T9",
            }
        )
        repo.complete(store._assessment_write(done))
    repo.trace(agent_id, saved.encounter.id, "assessed")
    return repo.projection(agent_id, saved.encounter.id)
