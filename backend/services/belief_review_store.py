"""Validated v2 persistence use cases; each async operation offloads SQLite exactly once."""

import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from typing import TypeVar

from pydantic import TypeAdapter

from backend.core.logging_config import mask_secrets
from backend.errors import ConstraintViolation, SecurityViolation, ValidationGlitch
from backend.services.belief_review_contracts import (
    Actor,
    AgentId,
    Assessment,
    Encounter,
    FrozenRecord,
    Identifier,
    ReviewDecision,
    claim_key,
    encounter_key,
)
from backend.storage.belief_review import (
    AssessmentWrite,
    DecisionWrite,
    EncounterWrite,
    RecoveryRecord,
    ReviewStateRecord,
)
from backend.storage.repositories.cognitive.belief_review import BeliefDecisionRepository, BeliefReviewRepository

T = TypeVar("T", bound=FrozenRecord)


def _agent(value: str) -> str:
    return TypeAdapter(AgentId).validate_python(value).lower()


def _identifier(value: str) -> str:
    return TypeAdapter(Identifier).validate_python(value)


def _json(value: FrozenRecord) -> str:
    # Reject unsafe input instead of silently changing statement/source hashes during redaction.
    payload = value.model_dump_json()
    configured = [
        part
        for key, raw in os.environ.items()
        if raw and (key.endswith("API_KEY") or key == "AAA_PASSWORD")
        for part in raw.split(",")
        if part
    ]
    known_secret = any(
        (secret in payload if len(secret) >= 8 else json.dumps(secret) in payload) for secret in configured
    )
    if mask_secrets(payload) != payload or known_secret:
        raise ValidationGlitch("Secret-bearing review input must be sanitized before binding", entity="belief_review")
    return payload


def _validated(value: T) -> T:
    _json(value)
    result = type(value).model_validate_json(value.model_dump_json())
    agent = getattr(result, "agent_id", None)
    if agent is not None and agent != _agent(agent):
        raise ValidationGlitch("Review writes require canonical lower-case agent identity", entity="belief_review")
    return result


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class SavedEncounter:
    encounter: Encounter
    record_id: str
    claim_id: str
    created: bool


class BeliefReviewStore:
    """Intake/assessment operations have no decision method or provider replay capability."""

    def __init__(self, db_path: str) -> None:
        self.repository = BeliefReviewRepository(db_path)

    async def register(self, encounter: Encounter) -> SavedEncounter:
        return await asyncio.to_thread(self._register, encounter)

    def _register(self, encounter: Encounter) -> SavedEncounter:
        value = _validated(encounter)
        if value.source.context_status == "available" and value.source.source_type not in {"message", "chat_turn"}:
            value = Encounter.model_validate(
                {
                    **value.model_dump(),
                    "source": value.source.model_copy(
                        update={
                            "context_status": "ambiguous",
                            "unavailable_reason": "No agent-owned source resolver for this source kind in T5",
                        }
                    ),
                }
            )
        payload = _json(value)
        scoped_key = claim_key(value.statement, value.scope, value.temporal_scope)
        if value.scope.strip().casefold() == "unknown" or value.temporal_scope.strip().casefold() == "unknown":
            scoped_key = None
        claim_id = "claim:" + _digest([value.agent_id, scoped_key or value.id])
        record_id = value.candidate_id or "candidate:" + _digest([value.agent_id, claim_id])
        inputs = value.model_dump(mode="json", exclude={"id", "received_at"})
        write = EncounterWrite(
            value.agent_id,
            value.id,
            encounter_key(value),
            _digest(inputs),
            scoped_key,
            claim_id,
            record_id,
            value.candidate_id is not None,
            value.statement,
            value.statement_sha256,
            value.scope,
            value.temporal_scope,
            value.received_at.isoformat(),
            payload,
            json.dumps([value.source.model_dump(mode="json")]),
            value.source.context_status == "available",
            value.source.source_type,
            value.source.source_id,
            value.source.source_sha256,
            value.source.quote,
        )
        stored = self.repository.register(write)
        return SavedEncounter(
            Encounter.model_validate_json(stored.encounter_json), stored.record_id, stored.claim_id, stored.created
        )

    async def get_encounter(self, agent_id: str, encounter_id: str) -> SavedEncounter:
        return await asyncio.to_thread(self._get_encounter, agent_id, encounter_id)

    def _get_encounter(self, agent_id: str, encounter_id: str) -> SavedEncounter:
        stored = self.repository.get_encounter(_agent(agent_id), _identifier(encounter_id))
        return SavedEncounter(
            Encounter.model_validate_json(stored.encounter_json), stored.record_id, stored.claim_id, False
        )

    async def get_assessment(self, agent_id: str, assessment_id: str) -> Assessment:
        return await asyncio.to_thread(self._get_assessment, agent_id, assessment_id)

    def _get_assessment(self, agent_id: str, assessment_id: str) -> Assessment:
        payload = self.repository.get_assessment(_agent(agent_id), _identifier(assessment_id))
        return Assessment.model_validate_json(payload)

    def _assessment_write(self, value: Assessment) -> AssessmentWrite:
        if not value.candidate_id:
            raise ValidationGlitch("Assessment requires resolved candidate identity", entity="belief_assessment")
        fields = {
            name: value.model_dump(mode="json")[name]
            for name in (
                "id",
                "agent_id",
                "encounter_id",
                "candidate_id",
                "previous_assessment_id",
                "policy_version",
                "rubric_version",
                "context_hash",
                "comparison_snapshots",
                "started_at",
                "requested_model",
            )
        }
        stale = value
        unavailable = value
        if value.completed_at is not None:
            stale = Assessment.model_validate(
                {
                    **value.model_dump(),
                    "evaluator_status": "stale",
                    "referent_status": "stale",
                    "abstain_reason": "Source, candidate or comparison changed before completion",
                    "relations": tuple(
                        r.model_copy(
                            update={"relation": "insufficient_context", "raw_relation": r.raw_relation or r.relation}
                        )
                        for r in value.relations
                    ),
                }
            )
            unavailable = Assessment.model_validate(
                {
                    **stale.model_dump(),
                    "evaluator_status": "abstained",
                    "referent_status": "missing",
                    "abstain_reason": "Encounter context unavailable; semantic relations cannot be established",
                }
            )
        return AssessmentWrite(
            value.agent_id,
            value.id,
            value.encounter_id,
            value.candidate_id,
            value.previous_assessment_id,
            _digest(fields),
            _json(value),
            _json(stale),
            _json(unavailable),
            any(r.relation != "insufficient_context" for r in value.relations),
            tuple((c.record_id, c.statement_sha256) for c in value.comparison_snapshots),
            value.started_at.isoformat(),
            value.completed_at.isoformat() if value.completed_at else None,
        )

    async def start_assessment(self, assessment: Assessment) -> Assessment:
        return await asyncio.to_thread(self._start_assessment, assessment)

    def _start_assessment(self, assessment: Assessment) -> Assessment:
        value = _validated(assessment)
        if value.evaluator_status != "pending":
            raise ValidationGlitch(
                "Assessment must be checkpointed pending before evaluation", entity="belief_assessment"
            )
        write = self._assessment_write(value)
        payload = self.repository.start_assessment(write)
        return Assessment.model_validate_json(payload)

    async def complete_assessment(self, assessment: Assessment) -> Assessment:
        return await asyncio.to_thread(self._complete_assessment, assessment)

    def _complete_assessment(self, assessment: Assessment) -> Assessment:
        value = _validated(assessment)
        if value.evaluator_status == "pending":
            raise ValidationGlitch("Completion needs an explicit evaluator outcome", entity="belief_assessment")
        write = self._assessment_write(value)
        payload = self.repository.complete_assessment(write)
        return Assessment.model_validate_json(payload)

    async def unfinished(self, agent_id: str, after_id: str = "", limit: int = 25) -> list[RecoveryRecord]:
        return await asyncio.to_thread(self._unfinished, agent_id, after_id, limit)

    def _unfinished(self, agent_id: str, after_id: str, limit: int) -> list[RecoveryRecord]:
        if after_id:
            _identifier(after_id)
        return self.repository.unfinished(_agent(agent_id), after_id, limit)


class BeliefDecisionStore:
    """Trusted operator/bookkeeping command boundary; authentication is supplied by the future API, never a model."""

    def __init__(self, db_path: str) -> None:
        self.repository = BeliefDecisionRepository(db_path)

    async def get_state(self, agent_id: str, record_id: str) -> ReviewStateRecord | None:
        return await asyncio.to_thread(self._get_state, agent_id, record_id)

    def _get_state(self, agent_id: str, record_id: str) -> ReviewStateRecord | None:
        return self.repository.get_state(_agent(agent_id), _identifier(record_id))

    async def get_decision(self, agent_id: str, decision_id: str) -> ReviewDecision:
        return await asyncio.to_thread(self._get_decision, agent_id, decision_id)

    def _get_decision(self, agent_id: str, decision_id: str) -> ReviewDecision:
        payload = self.repository.get_decision(_agent(agent_id), _identifier(decision_id))
        return ReviewDecision.model_validate_json(payload)

    async def commit(self, decision: ReviewDecision, *, authenticated_actor: Actor) -> ReviewDecision:
        return await asyncio.to_thread(self._commit, decision, authenticated_actor)

    def _commit(self, decision: ReviewDecision, authenticated_actor: Actor) -> ReviewDecision:
        value = _validated(decision)
        actor = _validated(authenticated_actor)
        if value.actor != actor or (
            value.authority == "operator_review" and (actor.kind != "operator" or not actor.auth_context_id)
        ):
            raise SecurityViolation("Decision actor does not match trusted caller", entity="belief_decision")
        if value.next_state == "superseded":
            raise ConstraintViolation(
                "Supersession requires the later linked-revision command", entity="belief_decision"
            )
        write = DecisionWrite(
            value.agent_id,
            value.id,
            value.record_id,
            value.statement_sha256,
            value.expected_review_version,
            value.previous_state,
            value.next_state,
            value.scope,
            value.timestamp.isoformat(),
            _json(value),
            value.assessment_ids,
        )
        payload = self.repository.commit_decision(write)
        return ReviewDecision.model_validate_json(payload)
