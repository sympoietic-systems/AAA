"""Bounded operator workshop; teachback is reconstruction, never warrant or a tool command."""

import asyncio
import hashlib
from datetime import UTC, datetime
from typing import Any, cast

from pydantic import Field

from backend.errors import ConstraintViolation, SecurityViolation, ValidationGlitch
from backend.services.belief_assessment import _context
from backend.services.belief_review_contracts import Actor, FrozenRecord, ReviewDecision, ReviewState, WorkshopCommand
from backend.services.belief_review_store import _agent, _digest, _identifier, _json, _validated
from backend.storage.belief_review import DecisionWrite
from backend.storage.repositories.cognitive.belief_workshop import TRANSITIONS, BeliefWorkshopRepository


class WorkshopReceipt(FrozenRecord):
    id: str = Field(max_length=128)
    agent_id: str = Field(max_length=64)
    record_id: str = Field(max_length=128)
    command: WorkshopCommand
    decision: ReviewDecision
    record_snapshot: dict[str, Any]
    relation_snapshots: tuple[dict[str, Any], ...] = Field(max_length=10)
    alternative_snapshot: dict[str, Any] | None
    counter_trace: dict[str, Any] | None
    linked_record_id: str | None = None
    tool_authority: str = "none"
    shared_agreement: str = "not_inferred"


class WorkshopView(FrozenRecord):
    payload: dict[str, Any]


class BeliefWorkshop:
    def __init__(self, db_path: str) -> None:
        self.repository = BeliefWorkshopRepository(db_path)

    async def family(self, agent: str, record: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._family, _agent(agent), _identifier(record))

    def _family(self, agent: str, record: str) -> dict[str, Any]:
        result = self.repository.family(agent, record)
        _json(WorkshopView(payload=result))
        return result

    async def command(
        self, agent: str, record: str, key: str, command: WorkshopCommand, *, actor: Actor
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._command, _agent(agent), _identifier(record), _identifier(key), command, actor
        )

    def _command(self, agent: str, record: str, key: str, command: WorkshopCommand, actor: Actor) -> dict[str, Any]:
        command, actor = _validated(command), _validated(actor)
        if actor.kind != "operator" or not actor.auth_context_id:
            raise SecurityViolation("Workshop mutation requires authenticated operator", entity="belief_workshop")
        command_id = "workshop:" + _digest([agent, record, key])
        digest = _digest([agent, record, key, command.model_dump(mode="json"), actor.model_dump(mode="json")])
        prior = self.repository.prior(agent, command_id, digest)
        if prior:
            return prior
        if command.action == "merge" or (
            command.action in TRANSITIONS and (command.statement is not None or command.target_record_id is not None)
        ):
            raise ConstraintViolation(
                "Merge remains unsupported; other workshop actions reject linked fields", entity="belief_workshop"
            )
        if command.action == "revise" and (command.statement is None or command.target_record_id is not None):
            raise ValidationGlitch("Revision requires a new statement and no target record", entity="belief_workshop")
        if command.action == "supersede" and (command.target_record_id is None or command.statement is not None):
            raise ValidationGlitch("Supersession requires an adopted target record", entity="belief_workshop")
        if command.action == "resurface" and (command.statement is not None or command.target_record_id is not None):
            raise ValidationGlitch("Resurfacing cannot change statement or target", entity="belief_workshop")
        if command.action not in TRANSITIONS and command.action not in {"revise", "supersede", "resurface"}:
            raise ConstraintViolation("Unknown workshop action", entity="belief_workshop")
        own = self.repository.snapshot(agent, record)
        if len(own["statement"]) > 4000:
            raise ValidationGlitch("Record statement exceeds workshop boundary", entity="belief_workshop")
        current = own["state"]
        if (
            own["statement_sha256"] != command.expected_statement_sha256
            or (current["version"] if current else 0) != command.expected_review_version
            or (current["state"] if current else None) != command.expected_state
        ):
            raise ConstraintViolation("Stale workshop statement/state/version", entity="belief_workshop")
        if command.action in {"revise", "supersede"} and (not current or current["state"] != "adopted"):
            raise ConstraintViolation("Linked action requires a canonical commitment", entity="belief_workshop")
        if command.action == "resurface" and (not current or current["state"] not in {"adopted", "superseded"}):
            raise ConstraintViolation("Resurfacing requires a canonical commitment", entity="belief_workshop")
        if command.action == "resurface" and command.assessment_ids:
            raise ConstraintViolation("Resurfacing cannot add assessment or warrant", entity="belief_workshop")
        snapshots: dict[str, dict[str, Any]] = {record: own}
        resolved = _context(
            own["statement"], command.scope, command.temporal_scope, "operator:" + command_id, command.context
        )
        for relation in command.relations:
            if relation.record_id == record:
                raise ConstraintViolation("Relation cannot compare record to itself", entity="belief_workshop")
            peer = self.repository.snapshot(agent, relation.record_id)
            state = peer["state"]
            if (
                peer["statement_sha256"] != relation.expected_statement_sha256
                or (state["version"] if state else 0) != relation.expected_review_version
            ):
                raise ConstraintViolation("Stale relation peer hash/version", entity="belief_workshop")
            context = _context(
                peer["statement"], peer["scope"], peer["temporal_scope"], peer["context_provenance"], relation.context
            )
            if relation.relation != "insufficient_context":
                if (
                    not resolved
                    or not context
                    or not own["source_current"]
                    or not peer["source_current"]
                    or not relation.scope.strip()
                    or not relation.temporal_scope.strip()
                ):
                    raise ConstraintViolation(
                        "Scoped semantic relation requires validated source/context", entity="belief_workshop"
                    )
                if relation.relation in {"equivalent", "contradiction"} and (
                    resolved.scope,
                    resolved.temporal_scope,
                    relation.scope,
                    relation.temporal_scope,
                ) != (context.scope, context.temporal_scope, context.scope, context.temporal_scope):
                    raise ConstraintViolation(
                        "Same-condition relation requires matching scope/time", entity="belief_workshop"
                    )
            snapshots[relation.record_id] = peer
        target = None
        if command.target_record_id:
            if command.target_record_id == record:
                raise ConstraintViolation("Supersession target must be a distinct record", entity="belief_workshop")
            target = self.repository.snapshot(agent, command.target_record_id)
            target_state = target["state"]
            if (
                target["statement_sha256"] != command.expected_target_statement_sha256
                or (target_state["version"] if target_state else 0) != command.expected_target_review_version
                or not target_state
                or target_state["state"] != "adopted"
            ):
                raise ConstraintViolation(
                    "Supersession target must be a current adopted commitment", entity="belief_workshop"
                )
            snapshots[command.target_record_id] = target
        alternative = None
        if command.teachback:
            fork = command.teachback
            if fork.alternative_record_id == record:
                raise ConstraintViolation("Teachback requires a distinct alternative", entity="belief_workshop")
            alternative = self.repository.snapshot(agent, fork.alternative_record_id)
            state = alternative["state"]
            if (
                alternative["statement_sha256"] != fork.expected_alternative_statement_sha256
                or (state["version"] if state else 0) != fork.expected_alternative_review_version
            ):
                raise ConstraintViolation("Teachback alternative changed", entity="belief_workshop")
            snapshots[fork.alternative_record_id] = alternative
        positions = []
        for position in command.positions:
            if position.attribution == "declared":
                if position.participant_id != actor.principal_id or position.declaration_source_id != "operator:self":
                    raise SecurityViolation(
                        "Other declared positions require a verified declaration channel", entity="belief_workshop"
                    )
                position = position.model_copy(update={"declaration_source_id": command_id})
            positions.append(position)
        decision_record = "revision:" + _digest([agent, record, key]) if command.action == "revise" else record
        if command.action == "revise":
            decision_state: ReviewState = "candidate"
        elif command.action == "supersede":
            decision_state = "superseded"
        elif command.action == "resurface":
            decision_state = cast(ReviewState, current["state"])
        else:
            decision_state = TRANSITIONS[command.action]
        decision_hash = (
            hashlib.sha256(command.statement.encode()).hexdigest()
            if command.action == "revise" and command.statement
            else command.expected_statement_sha256
        )
        decision = _validated(
            ReviewDecision(
                id="decision:" + _digest([agent, decision_record, key]),
                agent_id=agent,
                record_id=decision_record,
                statement_sha256=decision_hash,
                actor=actor,
                authority="operator_review",
                policy_version="belief-workshop-v1",
                expected_review_version=0 if command.action == "revise" else command.expected_review_version,
                previous_state=None if command.action == "revise" else command.expected_state,
                next_state=decision_state,
                scope=command.scope,
                rationale=command.rationale,
                consequence=command.consequence,
                challenge=command.challenge,
                positions=tuple(positions),
                dissent=command.dissent,
                assessment_ids=command.assessment_ids,
                timestamp=datetime.now(UTC),
            )
        )
        counter = (
            {
                "id": decision.id + ":counter",
                "actor": actor.model_dump(mode="json"),
                "record_id": record,
                "scope": command.scope,
                "temporal_scope": command.temporal_scope,
                "rationale": command.rationale,
                "consequence": command.consequence,
                "challenge": command.challenge,
                "dissent": list(command.dissent),
                "timestamp": decision.timestamp.isoformat(),
                "disposition": "retained_scoped_dissent",
                "tool_authority": "none",
            }
            if command.action == "decline"
            else None
        )
        packet = WorkshopReceipt(
            id=command_id,
            agent_id=agent,
            record_id=record,
            command=command,
            decision=decision,
            record_snapshot=own,
            relation_snapshots=tuple(snapshots[r.record_id] for r in command.relations),
            alternative_snapshot=alternative,
            counter_trace=counter,
            linked_record_id=decision_record if command.action == "revise" else command.target_record_id,
        )
        write = DecisionWrite(
            agent,
            decision.id,
            decision.record_id,
            decision.statement_sha256,
            decision.expected_review_version,
            decision.previous_state,
            decision.next_state,
            decision.scope,
            decision.timestamp.isoformat(),
            _json(decision),
            decision.assessment_ids,
        )
        return self.repository.commit(
            write,
            command_id,
            digest,
            _json(packet),
            tuple((rid, str(snapshot["fingerprint"])) for rid, snapshot in snapshots.items()),
        )
