"""Pure storage records. JSON is an application-validated immutable snapshot, not authority."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EncounterWrite:
    agent_id: str
    id: str
    event_key: str | None
    request_hash: str
    claim_key: str | None
    claim_id: str
    record_id: str
    existing_record: bool
    statement: str
    statement_hash: str
    scope: str
    temporal_scope: str
    received_at: str
    encounter_json: str
    source_json: str
    context_available: bool
    source_type: str
    source_id: str | None
    source_hash: str | None
    source_quote: str


@dataclass(frozen=True)
class EncounterResult:
    created: bool
    encounter_json: str
    claim_id: str
    record_id: str


@dataclass(frozen=True)
class AssessmentWrite:
    agent_id: str
    id: str
    encounter_id: str
    record_id: str
    previous_id: str | None
    input_hash: str
    receipt_json: str
    stale_json: str
    unavailable_json: str
    semantic_relations: bool
    comparisons: tuple[tuple[str, str], ...]
    timestamp: str
    completed_at: str | None


@dataclass(frozen=True)
class DecisionWrite:
    agent_id: str
    id: str
    record_id: str
    statement_hash: str
    expected_version: int
    previous_state: str | None
    next_state: str
    scope: str
    timestamp: str
    decision_json: str
    assessment_ids: tuple[str, ...]


@dataclass(frozen=True)
class ReviewStateRecord:
    agent_id: str
    record_id: str
    statement_hash: str
    state: str
    version: int
    scope: str
    decision_id: str | None
    current_statement_hash: str
    binding_status: str


@dataclass(frozen=True)
class RecoveryRecord:
    encounter_json: str
    record_id: str
    pending_assessment_id: str | None
