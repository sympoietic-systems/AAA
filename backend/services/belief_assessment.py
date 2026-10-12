"""Source/context-bound advisory reassessment. Provider calls never own a DB transaction."""

import asyncio
import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.errors import ConstraintViolation, ResourceNotFound, ValidationGlitch
from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.sensory.belief_assessment import POLICY, RUBRIC, evaluate, questions
from backend.modules.sensory.belief_context import REFERENCE, ClaimContext, context_error
from backend.modules.sensory.evidence_triage import EvidenceTriage
from backend.services.belief_admission import _capacity
from backend.services.belief_review_contracts import (
    Assessment,
    ComparisonSnapshot,
    FrozenRecord,
    ReferentContextSnapshot,
    RelationObservation,
    WarrantDimension,
    adapt_relation,
)
from backend.services.belief_review_store import BeliefReviewStore, _agent, _digest, _identifier, _json
from backend.storage.repositories.cognitive.belief_assessment import BeliefAssessmentRepository
from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository


class AssessmentSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    enabled: bool = False
    confidence_floor: float = Field(default=0.85, ge=0.7, le=1)
    call_timeout: float = Field(default=10.0, ge=1, le=30)
    capacity_wait: float = Field(default=2.0, ge=0, le=5)
    max_active: int = Field(default=128, ge=1, le=1024)


class AssessmentInput(FrozenRecord):
    candidate: dict[str, Any]
    comparisons: tuple[dict[str, Any], ...] = Field(max_length=10)


@dataclass(frozen=True)
class Prepared:
    pending: Assessment
    payload: dict[str, Any]
    fingerprints: tuple[tuple[str, str, str], ...]
    valid_pairs: tuple[bool, ...]
    stop_reason: str
    independence: Literal["internal", "derived", "unknown"]
    quote_source_refs: tuple[str, ...]
    quote_independence: Literal["internal", "derived", "unknown"]


def _context(
    statement: str, scope: str, temporal: str, provenance: str, supplied: ClaimContext | None
) -> ClaimContext | None:
    context = supplied
    if (
        context is None
        and scope.strip().casefold() not in {"", "unknown", "unresolved"}
        and temporal.strip().casefold() not in {"", "unknown", "unresolved"}
        and not REFERENCE.search(statement)
    ):
        context = ClaimContext(
            statement_sha256=hashlib.sha256(statement.encode()).hexdigest(),
            scope=scope,
            temporal_scope=temporal,
            provenance=provenance[:200],
            resolution="resolved",
        )
    if context_error(statement, context) is not None:
        return None
    if context and any(
        value.strip().casefold() in {"unknown", "unresolved"} for value in (context.scope, context.temporal_scope)
    ):
        return None
    return context


def _nominate(statement: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    words = set(re.findall(r"[\w-]{3,}", statement.casefold()))

    def rank(item: dict[str, Any]) -> tuple[float, str]:
        other = set(re.findall(r"[\w-]{3,}", str(item["statement"]).casefold()))
        return -len(words & other) / max(1, len(words | other)), str(item["id"])

    usable = sorted((r for r in records if 0 < len(r["statement"]) <= 4000), key=rank)
    chosen: list[dict[str, Any]] = []
    for group in ("adopted_or_legacy", "pending", "deferred", "history"):
        best = next((r for r in usable if r["stratum"] == group), None)
        if best:
            chosen.append(best)
    selected = {r["id"] for r in chosen}
    chosen.extend(r for r in usable if r["id"] not in selected)
    return chosen[:10]


def _prepare(
    db: str,
    agent: str,
    encounter_id: str,
    model: str | None,
    settings: AssessmentSettings,
    context: ClaimContext | None,
    comparison_contexts: dict[str, ClaimContext],
    attempt: str,
) -> Prepared:
    store = BeliefReviewStore(db)
    repo = BeliefAssessmentRepository(db)
    saved = store._get_encounter(agent, encounter_id)
    encounter = saved.encounter
    annotation = repo.annotations(agent, encounter_id)
    parent_id = annotation.get("parent_message_id") if annotation.get("parent_sha256") else None
    quote_independence: Literal["internal", "derived", "unknown"] = "unknown"
    if parent_id is not None and any(
        entry.source_id == str(parent_id) and entry.independence_status == "internal" for entry in encounter.lineage
    ):
        quote_independence = "internal"
    own = repo.record(agent, saved.record_id, "any")
    current = (
        repo.source_current(agent, encounter_id)
        and hashlib.sha256(str(own["statement"]).encode()).hexdigest() == encounter.statement_sha256
    )
    resolved = _context(
        encounter.statement, encounter.scope, encounter.temporal_scope, "encounter:" + encounter_id, context
    )
    records = repo.nominees(agent, saved.record_id)
    selected = _nominate(encounter.statement, records)
    snapshots = []
    contexts = [ReferentContextSnapshot(record_id=saved.record_id, context=resolved)] if resolved else []
    pairs = []
    payloads = []
    for item in selected:
        declared = _context(
            item["statement"],
            item["scope"],
            item["temporal_scope"],
            item["context_provenance"],
            comparison_contexts.get(item["id"]),
        )
        if not item["source_current"]:
            declared = None
        valid = bool(resolved and declared and current)
        pairs.append(valid)
        if declared:
            contexts.append(ReferentContextSnapshot(record_id=item["id"], context=declared))
        snapshots.append(
            ComparisonSnapshot(
                record_id=item["id"],
                agent_id=agent,
                record_kind=item["kind"],
                statement=item["statement"],
                statement_sha256=hashlib.sha256(item["statement"].encode()).hexdigest(),
                scope=declared.scope if declared else item["scope"],
                temporal_scope=declared.temporal_scope if declared else item["temporal_scope"],
                review_state=item["review_state"],
                review_version=item["review_version"],
                legacy_status=item["legacy_status"],
            )
        )
        payloads.append(
            {
                "id": item["id"],
                "statement": item["statement"],
                "quote": item["quote"],
                "context": declared.model_dump() if declared else None,
            }
        )
    frame = AssessmentInput(
        candidate={
            "id": saved.record_id,
            "statement": encounter.statement,
            "context": resolved.model_dump() if resolved else None,
            "quote": annotation.get("evidence_quote") or encounter.source.quote,
            "rationale": annotation.get("rationale", ""),
            "consequence": annotation.get("consequence", ""),
            "source_activity": encounter.source.activity,
            "quote_source_activity": quote_independence if parent_id is not None else encounter.source.activity,
        },
        comparisons=tuple(payloads),
    )
    _json(frame)
    exclusions = ["nomination_is_not_semantic_verdict", f"uncompared_in_bounded_scan:{len(records) - len(selected)}"]
    if len(records) == 200:
        exclusions.append("nomination_scan_exhausted:200;unseen_count_unknown")
    if len(selected) != len([r for r in records if len(r["statement"]) <= 4000]):
        exclusions.append("comparison_cap_or_oversized_records")
    if not all(pairs):
        exclusions.append("unvalidated_comparison_context")
    stale = encounter.source.context_status == "available" and not current
    stop = (
        "source_or_candidate_stale"
        if stale
        else "candidate_context_unavailable"
        if not current or resolved is None
        else "assessment_disabled"
        if not settings.enabled
        else ""
    )
    identity = str(
        uuid.uuid5(uuid.NAMESPACE_URL, "belief-assessment-v2:" + _digest([agent, encounter_id, attempt, POLICY]))
    )
    previous_json = repo.latest(agent, encounter_id)
    previous = Assessment.model_validate_json(previous_json) if previous_json else None
    if previous and previous.abstain_reason == "origin_paused":
        stop = "origin_paused"
    pending = Assessment(
        id=identity,
        agent_id=agent,
        encounter_id=encounter_id,
        candidate_id=saved.record_id,
        previous_assessment_id=previous.id if previous else None,
        policy_version=POLICY,
        rubric_version=RUBRIC,
        context_hash=_digest(
            {
                "frame": frame.model_dump(mode="json"),
                "questions": questions(sum(pairs)),
                "fingerprints": [r["fingerprint"] for r in selected],
                "floor": settings.confidence_floor,
            }
        ),
        comparison_snapshots=tuple(snapshots),
        referent_contexts=tuple(contexts),
        referent_status="stale" if stale else "validated" if current and resolved else "missing",
        evaluator_status="pending",
        started_at=datetime.now(UTC),
        requested_model=model,
        consequence_or_tension=str(annotation.get("consequence", "")),
        exclusions=tuple(exclusions),
    )
    _json(pending)
    independence: Literal["internal", "derived", "unknown"] = (
        "internal"
        if encounter.source.activity == "internal"
        else "derived"
        if any(entry.independence_status == "derived" for entry in encounter.lineage)
        else "unknown"
    )
    return Prepared(
        pending,
        frame.model_dump(mode="json"),
        tuple((r["id"], r["kind"], r["fingerprint"]) for r in selected),
        tuple(pairs),
        stop,
        independence,
        ("message:" + str(parent_id),) if parent_id is not None else (encounter_id,),
        quote_independence if parent_id is not None else independence,
    )


def _done(pending: Assessment, status: str, reason: str) -> Assessment:
    return Assessment.model_validate(
        pending.model_dump() | {"evaluator_status": status, "abstain_reason": reason, "completed_at": datetime.now(UTC)}
    )


def _finish(db: str, assessment: Assessment, prepared: Prepared) -> Assessment:
    store = BeliefReviewStore(db)
    payload = BeliefAssessmentRepository(db).finish(store._assessment_write(assessment), prepared.fingerprints)
    result = Assessment.model_validate_json(payload)
    if BeliefAssessmentRepository(db).annotations(assessment.agent_id, assessment.encounter_id):
        ExplicitBeliefRepository(db).trace(assessment.agent_id, assessment.encounter_id, "assessed", assessment.id)
    return result


async def assess_encounter(
    db_path: str,
    agent_id: str,
    encounter_id: str,
    *,
    config: dict[str, Any],
    evaluator: EvidenceTriage | None = None,
    context: ClaimContext | None = None,
    comparison_contexts: dict[str, ClaimContext] | None = None,
    attempt_id: str = "initial",
) -> Assessment:
    agent, encounter, attempt = _agent(agent_id), _identifier(encounter_id), _identifier(attempt_id)
    settings = AssessmentSettings.model_validate(config.get("belief_review", {}).get("assessment", {}))
    if evaluator is None and settings.enabled:
        evaluator = EvidenceTriage(TypeSafeDecisionClient.from_config(config.get("typesafe") or {}))
    prepared = await asyncio.to_thread(
        _prepare,
        db_path,
        agent,
        encounter,
        evaluator.client.model if evaluator else None,
        settings,
        context,
        comparison_contexts or {},
        attempt,
    )
    store = BeliefReviewStore(db_path)
    try:
        saved = await store.get_assessment(agent, prepared.pending.id)
    except ResourceNotFound:
        saved = None
    if saved:
        if (
            saved.context_hash != prepared.pending.context_hash
            or saved.requested_model != prepared.pending.requested_model
            or saved.referent_status != prepared.pending.referent_status
        ):
            raise ConstraintViolation(
                "Assessment replay changed context/source; prior receipt is historical", entity="belief_assessment"
            )
        return saved  # Pending/failed/completed operations never automatically replay a provider.
    claimed, payload = await asyncio.to_thread(
        BeliefAssessmentRepository(db_path).claim,
        store._assessment_write(prepared.pending),
        store._assessment_write(_done(prepared.pending, "unavailable", "queue_exhausted")),
        settings.max_active,
    )
    if not claimed:
        return Assessment.model_validate_json(payload)
    if await asyncio.to_thread(BeliefAssessmentRepository(db_path).annotations, agent, encounter):
        await asyncio.to_thread(
            ExplicitBeliefRepository(db_path).trace, agent, encounter, "received", prepared.pending.id
        )
    pending = prepared.pending
    if prepared.stop_reason:
        return await asyncio.to_thread(
            _finish,
            db_path,
            _done(
                pending,
                "stale"
                if pending.referent_status == "stale"
                else "unavailable"
                if prepared.stop_reason == "assessment_disabled"
                else "abstained",
                prepared.stop_reason,
            ),
            prepared,
        )
    acquired = False
    semaphore = _capacity()
    try:
        if settings.capacity_wait == 0:
            if semaphore.locked():
                raise TimeoutError("Capacity unavailable")
            await semaphore.acquire()
        else:
            await asyncio.wait_for(semaphore.acquire(), timeout=settings.capacity_wait)
        acquired = True
        if evaluator is None:
            result: dict[str, Any] = {"status": "unavailable", "reason": "unconfigured", "answers": {}}
        else:
            # Unknown comparison context is excluded from provider classification, then projected as insufficient.
            state = dict(prepared.payload)
            state["comparisons"] = [
                p for p, valid in zip(state["comparisons"], prepared.valid_pairs, strict=True) if valid
            ]
            result = await asyncio.wait_for(
                evaluate(evaluator, state, len(state["comparisons"]), settings.confidence_floor),
                timeout=settings.call_timeout,
            )
    except asyncio.CancelledError:
        await asyncio.shield(
            asyncio.to_thread(
                _finish, db_path, _done(pending, "failed", "provider_outcome_unknown_after_cancellation"), prepared
            )
        )
        raise
    except (TimeoutError, OSError, ValueError, TypeError, AttributeError, RuntimeError) as error:
        result = {
            "status": "unavailable",
            "reason": "capacity_exhausted" if not acquired else type(error).__name__,
            "answers": {},
        }
    finally:
        if acquired:
            semaphore.release()
    completed = _done(pending, str(result["status"]), str(result.get("reason", "")))
    diagnostic_snapshots = [
        snapshot for snapshot, valid in zip(pending.comparison_snapshots, prepared.valid_pairs, strict=True) if valid
    ]
    diagnostics = []
    for observed in result.get("diagnostics", []):
        diagnostic = dict(observed)
        if diagnostic["question_id"].startswith("relation_"):
            snapshot = diagnostic_snapshots[int(diagnostic["question_id"].split("_")[1])]
            diagnostic.update(comparison_id=snapshot.record_id, comparison_statement_sha256=snapshot.statement_sha256)
        diagnostics.append(diagnostic)
    completed = Assessment.model_validate(
        completed.model_dump() | {"evaluation_diagnostics": diagnostics, "returned_model": result.get("returned_model")}
    )
    if result.get("status") == "evaluated":
        answers = result["answers"]
        relations = []
        index = 0
        for snapshot, valid in zip(pending.comparison_snapshots, prepared.valid_pairs, strict=True):
            answer = answers[f"relation_{index}"] if valid else None
            raw = str(answer["choice"]) if answer else "insufficient"
            mismatch = False
            if valid and raw in {"equivalent", "contradiction"}:
                candidate_context = next(
                    c.context for c in pending.referent_contexts if c.record_id == pending.candidate_id
                )
                mismatch = any(
                    a.strip().casefold() != b.strip().casefold()
                    for a, b in (
                        (candidate_context.scope, snapshot.scope),
                        (candidate_context.temporal_scope, snapshot.temporal_scope),
                    )
                )
                valid = not mismatch
            adapted, reason = adapt_relation("admission-v1", raw, context_validated=valid)
            relations.append(
                RelationObservation(
                    comparison_id=snapshot.record_id,
                    comparison_statement_sha256=snapshot.statement_sha256,
                    relation=adapted,
                    scope=snapshot.scope,
                    temporal_scope=snapshot.temporal_scope,
                    raw_relation=raw,
                    raw_contract="admission-v1",
                    reason="scope_or_time_mismatch" if mismatch else reason,
                    assessment_confidence=float(answer["confidence"]) if answer else None,
                )
            )
            index += int(answer is not None)
        dimensions = tuple(
            WarrantDimension(
                name=name,
                basis="Advisory " + key + "=" + str(answers[key]["choice"]),
                source_refs=prepared.quote_source_refs if key == "factual_grounding" else (encounter,),
                independence_status=prepared.quote_independence
                if key == "factual_grounding"
                else prepared.independence,
                uncertainty="Classifier interpretation; no independent support or adoption",
                challenge="Requires situated review",
            )
            for name, key in (
                ("empirical_traced", "factual_grounding"),
                ("artistic_axiomatic", "artistic_grounding"),
                ("unresolved_tension", "tension"),
            )
        )
        completed = Assessment.model_validate(
            completed.model_dump()
            | {
                "relations": tuple(relations),
                "warrant_dimensions": dimensions,
                "challenge": "Consequence="
                + str(answers["consequence"]["choice"])
                + "; warrant uncertainty remains separate from relation.",
                "assessment_confidence": min(float(a["confidence"]) for a in answers.values()),
                "returned_model": result.get("returned_model"),
            }
        )
    try:
        _json(completed)
    except ValidationGlitch:
        completed = _done(pending, "failed", "unsafe_provider_metadata")
    return await asyncio.to_thread(_finish, db_path, completed, prepared)
