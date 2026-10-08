"""T3 schema/adapter oracles. Offline; no provider, route, or persistence wiring."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from backend.api.belief_review_schemas import ReviewDecisionRequest, ReviewExportQuery
from backend.services.belief_review_contracts import (
    Actor,
    Assessment,
    ComparisonSnapshot,
    Encounter,
    LineageEntry,
    ParticipantPosition,
    RelationObservation,
    ReviewDecision,
    ReviewLimits,
    SituatedStanding,
    SkillProjection,
    SourceReference,
    WarrantDimension,
    adapt_relation,
    claim_key,
    encounter_key,
    intake_mode,
    project_legacy,
)

NOW = datetime(2026, 10, 8, 12, tzinfo=UTC)
STATEMENT = "A distinction changes the next decision."
HASH = hashlib.sha256(STATEMENT.encode()).hexdigest()


def encounter(**changes):
    data = dict(
        id="encounter",
        agent_id="symbia",
        origin="explicit_chat",
        segment_id="tag:0",
        received_at=NOW,
        statement=STATEMENT,
        statement_sha256=HASH,
        scope="memory trials",
        temporal_scope="during replay",
        source=SourceReference(
            source_type="message", context_status="available", source_id="42", source_sha256=HASH, quote=STATEMENT
        ),
    )
    return Encounter(**(data | changes))


def assessment(**changes):
    comparison = ComparisonSnapshot(
        record_id="comparison",
        agent_id="symbia",
        record_kind="belief",
        statement=STATEMENT,
        statement_sha256=HASH,
        scope="memory trials",
        temporal_scope="during replay",
    )
    relation = RelationObservation(
        comparison_id="comparison",
        comparison_statement_sha256=HASH,
        relation="contradiction",
        scope="memory trials",
        temporal_scope="during replay",
    )
    data = dict(
        id="assessment",
        agent_id="symbia",
        encounter_id="encounter",
        policy_version="v2-shadow",
        rubric_version="draft-v1",
        context_hash=HASH,
        referent_status="validated",
        comparison_snapshots=(comparison,),
        relations=(relation,),
        evaluator_status="evaluated",
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=1),
    )
    return Assessment(**(data | changes))


def decision(**changes):
    data = dict(
        id="decision",
        agent_id="symbia",
        record_id="candidate",
        statement_sha256=HASH,
        authority="operator_review",
        actor=Actor(kind="operator", principal_id="operator", auth_context_id="request:1"),
        policy_version="operator-review-v1",
        expected_review_version=0,
        previous_state="under_review",
        next_state="adopted",
        scope="memory trials",
        rationale="Adopt a situated constraint.",
        consequence="Change subsequent trials.",
        challenge="A trial with identical behavior challenges the premise.",
        timestamp=NOW,
    )
    return ReviewDecision(**(data | changes))


@pytest.mark.parametrize("status", ["pending", "refined", "rejected", "adopted", "crystallized", "collapsed"])
def test_v21_legacy_status_never_invents_a_review_decision(status):
    projected = project_legacy(status)
    assert projected.legacy_status == status
    assert projected.review_state is None
    assert projected.decision_id is None


def test_v2_encounter_identity_separates_retry_segment_source_version_and_agent():
    original = encounter()
    assert encounter_key(encounter(received_at=NOW + timedelta(hours=1))) == encounter_key(original)
    assert encounter_key(encounter(segment_id="tag:1")) != encounter_key(original)
    assert encounter_key(encounter(agent_id="aaa")) != encounter_key(original)
    source = SourceReference(**(original.source.model_dump() | {"source_version": "2"}))
    assert encounter_key(encounter(source=source)) != encounter_key(original)
    assert claim_key(STATEMENT, "scope A", "today") != claim_key(STATEMENT, "scope B", "today")
    assert claim_key(STATEMENT, "", "today") is None


def test_v3_unknown_source_keeps_reason_without_fabricating_retry_identity():
    source = SourceReference(source_type="document", context_status="missing", unavailable_reason="Passage unavailable")
    assert encounter_key(encounter(source=source)) is None
    with pytest.raises(ValidationError, match="source identity/hash"):
        SourceReference(source_type="document", context_status="available", quote="Some passage")


def test_v3_hashes_and_context_bind_current_statements_and_relations():
    with pytest.raises(ValidationError, match="hash mismatch"):
        encounter(statement="A changed claim.")
    with pytest.raises(ValidationError, match="validated context"):
        assessment(referent_status="ambiguous")
    bad = RelationObservation(comparison_id="comparison", comparison_statement_sha256="0" * 64, relation="distinct")
    with pytest.raises(ValidationError, match="matching comparison snapshot"):
        assessment(relations=(bad,))


@pytest.mark.parametrize("status", ["unavailable", "failed", "abstained", "stale"])
def test_v4_unavailable_assessment_cannot_establish_semantic_relations(status):
    with pytest.raises(ValidationError, match="Unavailable evaluator"):
        assessment(evaluator_status=status)


def test_v5_comparison_snapshot_agent_and_capacity_are_bounded():
    snapshot = assessment().comparison_snapshots[0]
    wrong = ComparisonSnapshot(**(snapshot.model_dump() | {"agent_id": "other"}))
    with pytest.raises(ValidationError, match="another agent"):
        assessment(comparison_snapshots=(wrong,))
    with pytest.raises(ValidationError):
        assessment(comparison_snapshots=(snapshot,) * 11)


def test_v7_internal_encounter_can_reference_external_support_but_cannot_mint_its_own():
    original = encounter()
    source = SourceReference(**(original.source.model_dump() | {"activity": "internal"}))
    with pytest.raises(ValidationError, match="independent warrant"):
        encounter(source=source, lineage=(LineageEntry(source_id="42", independence_status="independent"),))
    retained = encounter(
        source=source, lineage=(LineageEntry(source_id="external-trial", independence_status="independent"),)
    )
    assert retained.lineage[0].source_id == "external-trial"


def test_v8_warrant_dimensions_are_open_and_nonexclusive_without_a_truth_score():
    dimensions = tuple(
        WarrantDimension(name=name, basis="Recorded basis")
        for name in ("empirical", "artistic", "tension", "new-register")
    )
    result = assessment(warrant_dimensions=dimensions)
    assert [d.name for d in result.warrant_dimensions] == ["empirical", "artistic", "tension", "new-register"]
    with pytest.raises(ValidationError):
        WarrantDimension(name="empirical", truth_probability=0.99)


def test_v11_intake_and_agent_cannot_adopt_or_demote_a_commitment():
    with pytest.raises(ValidationError, match="authorization context"):
        decision(actor=Actor(kind="agent", principal_id="jev"))
    with pytest.raises(ValidationError, match="Intake cannot"):
        decision(authority="intake_bookkeeping", actor=Actor(kind="system", principal_id="intake"))
    with pytest.raises(ValidationError, match="Intake cannot"):
        decision(
            authority="intake_bookkeeping",
            actor=Actor(kind="system", principal_id="intake"),
            previous_state="adopted",
            next_state="under_review",
        )


def test_v11_actor_fields_in_commands_and_unattributed_consensus_are_rejected():
    data = dict(
        action="adopt",
        expected_review_version=0,
        expected_statement_sha256=HASH,
        expected_state="under_review",
        scope="memory trials",
        rationale="Explicit decision",
        consequence="Change inquiry",
        challenge="Replay test",
    )
    with pytest.raises(ValidationError):
        ReviewDecisionRequest(**data, actor={"kind": "operator"}, authority="operator_review")
    with pytest.raises(ValidationError, match="attributable source"):
        ParticipantPosition(participant_id="symbia", position="assent", attribution="declared")
    assert decision().positions == ()  # Adoption does not fabricate shared assent.


def test_v11_destructive_target_requires_its_version_and_revision_requires_text():
    data = dict(
        action="merge",
        expected_review_version=1,
        expected_statement_sha256=HASH,
        expected_state="under_review",
        scope="trials",
        rationale="Preserve consequence",
        consequence="New trial",
        challenge="Counterexample",
        target_record_id="target",
    )
    with pytest.raises(ValidationError, match="expected review version"):
        ReviewDecisionRequest(**data)
    assert (
        ReviewDecisionRequest(
            **data, expected_target_review_version=3, expected_target_statement_sha256=HASH
        ).target_record_id
        == "target"
    )
    with pytest.raises(ValidationError, match="requires a statement"):
        ReviewDecisionRequest(**(data | {"action": "revise"}))


def test_v12_completed_nested_records_are_immutable_and_timestamps_are_utc():
    record = assessment()
    with pytest.raises(ValidationError):
        record.relations[0].relation = "equivalent"
    with pytest.raises(ValidationError):
        record.completed_at = NOW
    offset = NOW.astimezone(__import__("datetime").timezone(timedelta(hours=8)))
    assert encounter(received_at=offset).received_at == NOW
    assert encounter(received_at=offset).received_at.utcoffset() == timedelta(0)
    with pytest.raises(ValidationError):
        encounter(received_at=NOW.replace(tzinfo=None))


@pytest.mark.parametrize(
    "contract,raw,expected",
    [
        ("admission-v1", "independent", "distinct"),
        ("admission-v1", "insufficient", "insufficient_context"),
        ("admission-v1", "extension", "extension"),
        ("triage-v1", "contradiction", "contradiction"),
        ("triage-v1", "orthogonal", "distinct"),
        ("triage-v1", "endorsement", "insufficient_context"),
        ("triage-v1", "abstain", "insufficient_context"),
        ("unknown-v1", "equivalent", "insufficient_context"),
    ],
)
def test_v10_relation_adapter_preserves_loss_and_conflict(contract, raw, expected):
    assert adapt_relation(contract, raw, context_validated=True)[0] == expected
    assert adapt_relation(contract, raw, context_validated=False)[0] == "insufficient_context"


def test_v19_safe_defaults_and_finite_limits():
    limits = ReviewLimits()
    assert (limits.workers, limits.comparisons, limits.queue_capacity) == (2, 10, 128)
    assert (limits.exploratory_enabled, limits.exploratory_slots) == (False, 0)
    for changes in (
        {"workers": 5},
        {"queue_capacity": 1025},
        {"comparisons": 11},
        {"evaluator_timeout_seconds": float("inf")},
        {"exploratory_slots": 1},
    ):
        with pytest.raises(ValidationError):
            ReviewLimits(**changes)


def test_v20_export_interval_and_page_are_bounded():
    assert ReviewExportQuery(from_time=NOW, to_time=NOW + timedelta(days=1)).limit == 25
    with pytest.raises(ValidationError):
        ReviewExportQuery(from_time=NOW, to_time=NOW)
    with pytest.raises(ValidationError):
        ReviewExportQuery(from_time=NOW, to_time=NOW + timedelta(days=1), limit=51)


def test_v21_skill_application_never_transfers_semantic_adoption_authority():
    for authority in ("human_skill_application", "autonomous_skill_application", "legacy_unknown"):
        data = dict(agent_id="symbia", belief_id="bridge", skill_id="skill", application_authority=authority)
        if authority != "legacy_unknown":
            with pytest.raises(ValidationError, match="provenance"):
                SkillProjection(**data)
            data.update(
                skill_version=1,
                skill_statement_sha256=HASH,
                skill_event_id="skill-event",
                application_actor=Actor(
                    kind="operator" if authority == "human_skill_application" else "agent",
                    principal_id="application-actor",
                    auth_context_id="request:1",
                ),
            )
        projection = SkillProjection(**data)
        assert projection.semantic_adoption_authority == "none"
    with pytest.raises(ValidationError):
        SkillProjection(
            agent_id="symbia",
            belief_id="bridge",
            skill_id="skill",
            application_authority="legacy_unknown",
            semantic_adoption_authority="operator_review",
        )


def test_v21_pausing_promoted_origin_never_reopens_direct_creation():
    assert intake_mode("explicit_chat", promoted=False, enabled=False) == "legacy_admission"
    assert intake_mode("document", promoted=False, enabled=False) == "legacy_unpromoted"
    assert intake_mode("document", promoted=True, enabled=False) == "paused"
    assert intake_mode("document", promoted=True, enabled=True) == "shadow"
    with pytest.raises(ValueError, match="promotion"):
        intake_mode("document", promoted=False, enabled=True)


def test_v25_standing_requires_receipt_bound_to_current_statement_and_scope():
    data = dict(
        kind="reviewed_commitment",
        agent_id="symbia",
        record_id="candidate",
        statement_sha256=HASH,
        scope="memory trials",
        review_state="adopted",
    )
    with pytest.raises(ValidationError, match="attributable current decision"):
        SituatedStanding(**data)
    assert SituatedStanding(**data, decision=decision()).tool_authority == "none"
    for changes in ({"statement_sha256": "0" * 64}, {"scope": "different trials"}, {"agent_id": "other"}):
        with pytest.raises(ValidationError, match="Standing receipt"):
            SituatedStanding(**(data | changes), decision=decision())


def test_v25_legacy_labels_and_skill_projection_cannot_acquire_reviewed_standing():
    data = dict(kind="legacy_sediment", agent_id="symbia", record_id="candidate", statement_sha256=HASH)
    with pytest.raises(ValidationError, match="Legacy sediment"):
        SituatedStanding(**data, review_state="adopted")
    projection = SkillProjection(
        agent_id="symbia", belief_id="candidate", skill_id="skill", application_authority="legacy_unknown"
    )
    assert SituatedStanding(**(data | {"kind": "skill_projection"}), projection=projection).tool_authority == "none"
    with pytest.raises(ValidationError, match="transfer semantic adoption"):
        SituatedStanding(
            **(data | {"kind": "skill_projection", "scope": "memory trials"}),
            projection=projection,
            review_state="adopted",
            decision=decision(),
        )


def test_v9_candidate_dissent_is_permitted_without_adoption_or_tool_veto():
    standing = SituatedStanding(
        kind="situated_candidate",
        agent_id="symbia",
        record_id="candidate",
        statement_sha256=HASH,
        scope="memory trials",
        review_state="deferred",
        permitted_modes=("scoped_dissent", "provisional_premise"),
    )
    assert standing.decision is None
    assert standing.tool_authority == "none"


def test_v25_superseded_commitment_preserves_adoption_receipt():
    adoption = decision()
    supersession = decision(
        id="supersession", previous_state="adopted", next_state="superseded", expected_review_version=1
    )
    standing = SituatedStanding(
        kind="reviewed_commitment",
        agent_id="symbia",
        record_id="candidate",
        statement_sha256=HASH,
        scope="memory trials",
        review_state="superseded",
        decision=supersession,
        adoption_decision=adoption,
    )
    assert standing.adoption_decision.id == adoption.id
