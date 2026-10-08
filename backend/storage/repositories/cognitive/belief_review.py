"""Agent-scoped atomic v2 persistence. No provider calls or interpretation of warrant."""

import hashlib
import sqlite3
from typing import cast

from backend.errors import ConstraintViolation, ResourceNotFound
from backend.storage.belief_review import (
    AssessmentWrite,
    DecisionWrite,
    EncounterResult,
    EncounterWrite,
    RecoveryRecord,
    ReviewStateRecord,
)
from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.cognitive.belief import BeliefRepository
from backend.utils.belief_candidate import statement_key


class BeliefReviewRepository(BaseRepository):
    def _record_statement(self, agent_id: str, record_id: str) -> str:
        rows = (
            self._conn()
            .execute(
                "SELECT COALESCE(suggested_statement,provisional_statement) FROM belief_proposals "
                "WHERE LOWER(agent_id)=? AND id=? UNION ALL SELECT statement FROM belief_nodes WHERE LOWER(agent_id)=? AND id=?",
                (agent_id, record_id, agent_id, record_id),
            )
            .fetchall()
        )
        if not rows:
            raise ResourceNotFound("Belief review record not found", entity="belief_review")
        if len(rows) != 1:
            raise ConstraintViolation("Ambiguous belief review record identity", entity="belief_review")
        return str(rows[0][0])

    def _record_hash(self, agent_id: str, record_id: str) -> str:
        return hashlib.sha256(self._record_statement(agent_id, record_id).encode()).hexdigest()

    def _source_hash(self, agent_id: str, source_type: str, source_id: str | None, quote: str = "") -> str | None:
        if source_type not in {"message", "chat_turn"} or source_id is None:
            return None
        row = (
            self._conn()
            .execute(
                "SELECT m.content FROM conversation_log m JOIN conversations c ON c.id=m.conversation_id "
                "WHERE m.id=? AND LOWER(c.agent_id)=?",
                (source_id, agent_id),
            )
            .fetchone()
        )
        if row is None:
            raise ResourceNotFound("Encounter source not found", entity="belief_encounter")
        if quote and quote not in str(row[0]):
            raise ConstraintViolation("Encounter quote is absent from source", entity="belief_encounter")
        return hashlib.sha256(str(row[0]).encode()).hexdigest()

    def _encounter_row(self, agent_id: str, encounter_id: str) -> sqlite3.Row:
        row = (
            self._conn()
            .execute(
                "SELECT e.*,c.record_id FROM belief_encounters e JOIN belief_review_claims c "
                "ON c.agent_id=e.agent_id AND c.id=e.claim_id WHERE e.agent_id=? AND e.id=?",
                (agent_id, encounter_id),
            )
            .fetchone()
        )
        if row is None:
            raise ResourceNotFound("Belief encounter not found", entity="belief_encounter")
        return cast(sqlite3.Row, row)

    def _assessment_row(self, agent_id: str, assessment_id: str) -> sqlite3.Row:
        row = (
            self._conn()
            .execute(
                "SELECT a.*,l.receipt,l.status FROM belief_review_assessments a JOIN belief_admission l ON l.id=a.ledger_id "
                "WHERE a.agent_id=? AND a.id=?",
                (agent_id, assessment_id),
            )
            .fetchone()
        )
        if row is None:
            raise ResourceNotFound("Belief assessment not found", entity="belief_assessment")
        return cast(sqlite3.Row, row)

    @with_connection
    def register(self, value: EncounterWrite) -> EncounterResult:
        with self.atomic():
            conn = self._conn()
            prior = conn.execute(
                "SELECT e.*,c.record_id FROM belief_encounters e JOIN belief_review_claims c "
                "ON c.agent_id=e.agent_id AND c.id=e.claim_id WHERE e.agent_id=? AND (e.id=? OR e.event_key=?)",
                (value.agent_id, value.id, value.event_key),
            ).fetchall()
            if prior:
                if (
                    len(prior) != 1
                    or prior[0]["request_hash"] != value.request_hash
                    or prior[0]["event_key"] != value.event_key
                ):
                    raise ConstraintViolation("Encounter retry changed its bound input", entity="belief_encounter")
                row = prior[0]
                return EncounterResult(False, str(row["encounter_json"]), str(row["claim_id"]), str(row["record_id"]))
            observed = (
                self._source_hash(value.agent_id, value.source_type, value.source_id, value.source_quote)
                if value.context_available
                else None
            )
            if value.context_available and observed is not None and observed != value.source_hash:
                raise ConstraintViolation("Encounter source changed before persistence", entity="belief_encounter")
            claims = conn.execute(
                "SELECT id,record_id,claim_key FROM belief_review_claims WHERE agent_id=? "
                "AND (claim_key=? OR (?=1 AND record_id=?))",
                (value.agent_id, value.claim_key, int(value.existing_record), value.record_id),
            ).fetchall()
            if len(claims) > 1:
                raise ConstraintViolation("Explicit record conflicts with scoped claim identity", entity="belief_claim")
            claim = claims[0] if claims else None
            record_id = value.record_id
            claim_id = value.claim_id
            if claim:
                if claim["claim_key"] != value.claim_key:
                    raise ConstraintViolation(
                        "Explicit record has a different scoped claim identity", entity="belief_claim"
                    )
                claim_id, record_id = str(claim[0]), str(claim[1])
                if value.existing_record and record_id != value.record_id:
                    raise ConstraintViolation("Scoped claim already binds another record", entity="belief_claim")
                if statement_key(self._record_statement(value.agent_id, record_id)) != statement_key(value.statement):
                    raise ConstraintViolation(
                        "Scoped claim statement changed; explicit revision required", entity="belief_claim"
                    )
            else:
                if value.existing_record:
                    if self._record_hash(value.agent_id, record_id) != value.statement_hash:
                        raise ConstraintViolation("Existing record statement mismatch", entity="belief_claim")
                else:
                    BeliefRepository(self._db_path).create_proposal(
                        id=record_id,
                        agent_id=value.agent_id,
                        provisional_statement=value.statement,
                        source_trace=value.source_json,
                        initial_signature="",
                        suppress_notification=True,
                    )
                    initial_state = "candidate" if value.context_available and value.claim_key else "awaiting_context"
                    conn.execute(
                        "INSERT INTO belief_review_state VALUES (?,?,?,?,0,?,NULL)",
                        (value.agent_id, record_id, value.statement_hash, initial_state, value.scope),
                    )
                conn.execute(
                    "INSERT INTO belief_review_claims VALUES (?,?,?,?)",
                    (value.agent_id, claim_id, value.claim_key, record_id),
                )
            conn.execute(
                "INSERT INTO belief_encounters (agent_id,id,event_key,request_hash,claim_id,received_at,encounter_json,"
                "source_type,source_id,source_hash,context_available) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    value.agent_id,
                    value.id,
                    value.event_key,
                    value.request_hash,
                    claim_id,
                    value.received_at,
                    value.encounter_json,
                    value.source_type,
                    value.source_id,
                    value.source_hash,
                    int(value.context_available),
                ),
            )
            return EncounterResult(True, value.encounter_json, claim_id, record_id)

    @with_connection
    def get_encounter(self, agent_id: str, encounter_id: str) -> EncounterResult:
        row = self._encounter_row(agent_id, encounter_id)
        return EncounterResult(False, str(row["encounter_json"]), str(row["claim_id"]), str(row["record_id"]))

    @with_connection
    def get_assessment(self, agent_id: str, assessment_id: str) -> str:
        return str(self._assessment_row(agent_id, assessment_id)["receipt"])

    @with_connection
    def start_assessment(self, value: AssessmentWrite) -> str:
        with self.atomic():
            conn = self._conn()
            existing = conn.execute(
                "SELECT 1 FROM belief_review_assessments WHERE agent_id=? AND id=?", (value.agent_id, value.id)
            ).fetchone()
            if existing:
                row = self._assessment_row(value.agent_id, value.id)
                if row["input_hash"] != value.input_hash:
                    raise ConstraintViolation("Assessment retry changed input", entity="belief_assessment")
                return str(row["receipt"])
            encounter = self._encounter_row(value.agent_id, value.encounter_id)
            if encounter["record_id"] != value.record_id:
                raise ConstraintViolation("Assessment candidate link mismatch", entity="belief_assessment")
            if encounter["context_available"]:
                source_hash = self._source_hash(value.agent_id, str(encounter["source_type"]), encounter["source_id"])
                if source_hash != encounter["source_hash"]:
                    raise ConstraintViolation("Encounter source changed before assessment", entity="belief_assessment")
            if value.previous_id:
                previous = self._assessment_row(value.agent_id, value.previous_id)
                if previous["encounter_id"] != value.encounter_id or previous["status"] != "complete":
                    raise ConstraintViolation(
                        "Reassessment requires completed encounter predecessor", entity="belief_assessment"
                    )
            if conn.execute(
                "SELECT 1 FROM belief_admission WHERE agent_id=? AND encounter_id=? AND assessment_id IS NOT NULL AND status='assessing'",
                (value.agent_id, value.encounter_id),
            ).fetchone():
                raise ConstraintViolation("Encounter already has an unfinished assessment", entity="belief_assessment")
            candidate_hash = self._record_hash(value.agent_id, value.record_id)
            latest = conn.execute(
                "SELECT a.id,l.assessed_at FROM belief_review_assessments a JOIN belief_admission l ON l.id=a.ledger_id "
                "WHERE a.agent_id=? AND a.encounter_id=? ORDER BY l.rowid DESC LIMIT 1",
                (value.agent_id, value.encounter_id),
            ).fetchone()
            if latest and (latest[0] != value.previous_id or value.timestamp < str(latest[1])):
                raise ConstraintViolation(
                    "Reassessment must follow its latest completed predecessor", entity="belief_assessment"
                )
            for record_id, expected in value.comparisons:
                if record_id == value.record_id:
                    raise ConstraintViolation("Candidate cannot be its own comparison", entity="belief_assessment")
                if self._record_hash(value.agent_id, record_id) != expected:
                    raise ConstraintViolation("Comparison changed before assessment", entity="belief_assessment")
            ledger_id = hashlib.sha256(f"v2:{value.agent_id}:{value.id}".encode()).hexdigest()
            conn.execute(
                "INSERT INTO belief_admission (id,event_key,proposal_id,statement_key,status,receipt,created_at,agent_id,encounter_id,assessment_id) "
                "VALUES (?,?,?,?,'assessing',?,?,?,?,?)",
                (
                    ledger_id,
                    "v2:" + ledger_id,
                    value.record_id,
                    candidate_hash,
                    value.receipt_json,
                    value.timestamp,
                    value.agent_id,
                    value.encounter_id,
                    value.id,
                ),
            )
            conn.execute(
                "INSERT INTO belief_review_assessments (agent_id,id,encounter_id,ledger_id,previous_id,candidate_hash,input_hash) VALUES (?,?,?,?,?,?,?)",
                (
                    value.agent_id,
                    value.id,
                    value.encounter_id,
                    ledger_id,
                    value.previous_id,
                    candidate_hash,
                    value.input_hash,
                ),
            )
            return value.receipt_json

    @with_connection
    def complete_assessment(self, value: AssessmentWrite) -> str:
        with self.atomic():
            row = self._assessment_row(value.agent_id, value.id)
            if row["input_hash"] != value.input_hash:
                raise ConstraintViolation("Assessment completion changed its input", entity="belief_assessment")
            if row["status"] == "complete":
                if row["receipt"] not in {value.receipt_json, value.stale_json, value.unavailable_json}:
                    raise ConstraintViolation("Completed assessment is immutable", entity="belief_assessment")
                return str(row["receipt"])
            encounter = self._encounter_row(value.agent_id, value.encounter_id)
            stale = False
            try:
                stale = self._record_hash(value.agent_id, value.record_id) != row["candidate_hash"]
                stale |= any(self._record_hash(value.agent_id, rid) != sha for rid, sha in value.comparisons)
                observed = self._source_hash(value.agent_id, str(encounter["source_type"]), encounter["source_id"])
                stale |= observed is not None and observed != encounter["source_hash"]
            except ResourceNotFound:
                stale = True  # Missing current inputs produce an explicit stale receipt, never approval.
            payload = value.stale_json if stale else value.receipt_json
            if not encounter["context_available"] and value.semantic_relations:
                payload = value.unavailable_json
            self._conn().execute(
                "UPDATE belief_admission SET status='complete',receipt=?,assessed_at=? WHERE id=? AND status='assessing'",
                (payload, value.completed_at, row["ledger_id"]),
            )
            return payload

    @with_connection
    def get_state(self, agent_id: str, record_id: str) -> ReviewStateRecord | None:
        current_hash = self._record_hash(agent_id, record_id)
        row = (
            self._conn()
            .execute("SELECT * FROM belief_review_state WHERE agent_id=? AND record_id=?", (agent_id, record_id))
            .fetchone()
        )
        if row is None:
            return None
        return ReviewStateRecord(
            agent_id,
            record_id,
            str(row["statement_hash"]),
            str(row["state"]),
            int(row["version"]),
            str(row["scope"]),
            row["decision_id"],
            current_hash,
            "current" if row["statement_hash"] == current_hash else "stale",
        )

    @with_connection
    def unfinished(self, agent_id: str, after_id: str = "", limit: int = 25) -> list[RecoveryRecord]:
        rows = (
            self._conn()
            .execute(
                "SELECT e.encounter_json,c.record_id,l.assessment_id FROM belief_encounters e "
                "JOIN belief_review_claims c ON c.agent_id=e.agent_id AND c.id=e.claim_id "
                "LEFT JOIN belief_review_assessments a ON a.agent_id=e.agent_id AND a.encounter_id=e.id "
                "LEFT JOIN belief_admission l ON l.id=a.ledger_id WHERE e.agent_id=? AND e.id>? "
                "AND (a.id IS NULL OR l.status='assessing') ORDER BY e.id LIMIT ?",
                (agent_id, after_id, max(1, min(50, limit))),
            )
            .fetchall()
        )
        return [RecoveryRecord(str(row[0]), str(row[1]), row[2]) for row in rows]


class BeliefDecisionRepository(BeliefReviewRepository):
    """Decision write capability is absent from the repository used by intake workers."""

    @with_connection
    def commit_decision(self, value: DecisionWrite) -> str:
        with self.atomic():
            conn = self._conn()
            prior = conn.execute(
                "SELECT decision_json FROM belief_review_decisions WHERE agent_id=? AND id=?",
                (value.agent_id, value.id),
            ).fetchone()
            if prior:
                if prior[0] != value.decision_json:
                    raise ConstraintViolation("Decision identity reused with changed input", entity="belief_decision")
                return str(prior[0])
            if self._record_hash(value.agent_id, value.record_id) != value.statement_hash:
                raise ConstraintViolation("Decision statement changed", entity="belief_decision")
            state = self.get_state(value.agent_id, value.record_id)
            if (state.version if state else 0) != value.expected_version or (
                state.state if state else None
            ) != value.previous_state:
                raise ConstraintViolation("Stale review version or previous state", entity="belief_decision")
            if state and state.statement_hash != value.statement_hash:
                raise ConstraintViolation(
                    "Review standing requires explicit statement revision", entity="belief_decision"
                )
            for assessment_id in value.assessment_ids:
                assessment = self._assessment_row(value.agent_id, assessment_id)
                encounter = self._encounter_row(value.agent_id, str(assessment["encounter_id"]))
                if encounter["record_id"] != value.record_id or assessment["status"] != "complete":
                    raise ConstraintViolation(
                        "Decision requires completed record-bound assessments", entity="belief_decision"
                    )
            version = value.expected_version + 1
            conn.execute(
                "INSERT INTO belief_review_decisions VALUES (?,?,?,?,?,?)",
                (value.agent_id, value.id, value.record_id, version, value.decision_json, value.timestamp),
            )
            conn.execute(
                "INSERT INTO belief_review_state VALUES (?,?,?,?,?,?,?) ON CONFLICT(agent_id,record_id) DO UPDATE SET "
                "statement_hash=excluded.statement_hash,state=excluded.state,version=excluded.version,scope=excluded.scope,decision_id=excluded.decision_id",
                (
                    value.agent_id,
                    value.record_id,
                    value.statement_hash,
                    value.next_state,
                    version,
                    value.scope,
                    value.id,
                ),
            )
            return value.decision_json

    @with_connection
    def get_decision(self, agent_id: str, decision_id: str) -> str:
        row = (
            self._conn()
            .execute(
                "SELECT decision_json FROM belief_review_decisions WHERE agent_id=? AND id=?", (agent_id, decision_id)
            )
            .fetchone()
        )
        if row is None:
            raise ResourceNotFound("Belief decision not found", entity="belief_decision")
        return str(row[0])
