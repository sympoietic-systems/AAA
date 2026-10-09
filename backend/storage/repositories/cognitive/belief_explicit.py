"""Explicit-origin promotion, annotation links and legacy presentation projection."""

import json
from dataclasses import replace
from typing import Any

from backend.errors import ConstraintViolation
from backend.storage.belief_review import AssessmentWrite
from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.cognitive.belief_review import BeliefReviewRepository


class ExplicitBeliefRepository(BaseRepository):
    def _current_bindings(self, agent_id: str, encounter_id: str) -> bool:
        import hashlib

        row = (
            self._conn()
            .execute(
                "SELECT e.encounter_json,n.annotations_json FROM belief_encounters e JOIN belief_explicit_annotations n "
                "ON n.agent_id=e.agent_id AND n.encounter_id=e.id WHERE e.agent_id=? AND e.id=?",
                (agent_id, encounter_id),
            )
            .fetchone()
        )
        if row is None:
            raise ConstraintViolation("Emission bindings missing", entity="belief_intake")
        e, n = json.loads(row[0]), json.loads(row[1])
        bindings = [(e["source"]["source_id"], e["source"]["source_sha256"], True)]
        if n["parent_sha256"] is not None:
            bindings.append((n["parent_message_id"], n["parent_sha256"], False))
        for message_id, expected, apparatus in bindings:
            current = (
                self._conn()
                .execute(
                    "SELECT m.content,m.speaker FROM conversation_log m JOIN conversations c ON c.id=m.conversation_id "
                    "WHERE m.id=? AND m.conversation_id=? AND LOWER(c.agent_id)=?",
                    (message_id, n["conversation_id"], agent_id),
                )
                .fetchone()
            )
            if (
                current is None
                or (apparatus and current[1] != "apparatus")
                or hashlib.sha256(str(current[0]).encode()).hexdigest() != expected
            ):
                return False
        return True

    @with_connection
    def complete(self, write: AssessmentWrite) -> str:
        with self.atomic():
            if not self._current_bindings(write.agent_id, write.encounter_id):
                write = replace(write, receipt_json=write.stale_json)
            return BeliefReviewRepository(self._db_path).complete_assessment(write)

    @with_connection
    def promoted(self, agent_id: str, origin: str) -> bool:
        if (
            not self._conn()
            .execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='belief_origin_promotions'")
            .fetchone()
        ):
            return False
        return (
            self._conn()
            .execute("SELECT 1 FROM belief_origin_promotions WHERE agent_id=? AND origin=?", (agent_id, origin))
            .fetchone()
            is not None
        )

    @with_connection
    def promote(self, agent_id: str, origin: str, timestamp: str) -> None:
        with self.atomic():
            if (
                not self._conn()
                .execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='belief_origin_promotions'")
                .fetchone()
            ):
                raise ConstraintViolation("Explicit intake requires migration 065", entity="belief_intake")
            self._conn().execute(
                "INSERT OR IGNORE INTO belief_origin_promotions VALUES (?,?,?)", (agent_id, origin, timestamp)
            )

    @with_connection
    def annotate(self, agent_id: str, encounter_id: str, assessment_id: str, annotations: str) -> None:
        with self.atomic():
            prior = (
                self._conn()
                .execute(
                    "SELECT assessment_id,annotations_json FROM belief_explicit_annotations WHERE agent_id=? AND encounter_id=?",
                    (agent_id, encounter_id),
                )
                .fetchone()
            )
            if prior:
                if tuple(prior) != (assessment_id, annotations):
                    raise ConstraintViolation("Emission retry changed annotations", entity="belief_intake")
                return
            self._conn().execute(
                "INSERT INTO belief_explicit_annotations VALUES (?,?,?,?)",
                (agent_id, encounter_id, assessment_id, annotations),
            )
            if not self._current_bindings(agent_id, encounter_id):
                raise ConstraintViolation("Emission source changed before annotation", entity="belief_intake")
            n = json.loads(annotations)
            self._conn().execute(
                "UPDATE belief_proposals SET suggested_label=?,symbia_reflection=COALESCE(symbia_reflection,?) "
                "WHERE LOWER(agent_id)=? AND suggested_label IS NULL AND id LIKE 'candidate:%' "
                "AND id=(SELECT record_id FROM belief_review_claims c JOIN belief_encounters e "
                "ON e.agent_id=c.agent_id AND e.claim_id=c.id WHERE e.agent_id=? AND e.id=?)",
                (n["label"], n["rationale"], agent_id, agent_id, encounter_id),
            )

    @with_connection
    def projection(self, agent_id: str, encounter_id: str) -> dict[str, Any]:
        row = (
            self._conn()
            .execute(
                "SELECT e.encounter_json,e.request_hash,e.claim_id,c.record_id,n.annotations_json,n.assessment_id,l.receipt,"
                "(SELECT MIN(e2.rowid) FROM belief_encounters e2 WHERE e2.agent_id=e.agent_id AND e2.claim_id=e.claim_id)=e.rowid first_occurrence "
                "FROM belief_encounters e JOIN belief_review_claims c ON c.agent_id=e.agent_id AND c.id=e.claim_id "
                "JOIN belief_explicit_annotations n ON n.agent_id=e.agent_id AND n.encounter_id=e.id "
                "LEFT JOIN belief_review_assessments a ON a.agent_id=n.agent_id AND a.id=n.assessment_id "
                "LEFT JOIN belief_admission l ON l.id=a.ledger_id WHERE e.agent_id=? AND e.id=?",
                (agent_id, encounter_id),
            )
            .fetchone()
        )
        if row is None:
            raise ConstraintViolation("Explicit emission annotation missing", entity="belief_intake")
        e = json.loads(row["encounter_json"])
        n = json.loads(row["annotations_json"])
        a = json.loads(row["receipt"]) if row["receipt"] else None
        completed = bool(a and a["completed_at"])
        issues = n["context_issues"]
        reason = "V2 evaluator deferred to T9; no adoption authority."
        if a and a["evaluator_status"] == "stale":
            reason = "Emission or parent context changed during checkpoint completion; assessment is stale."
        if issues:
            reason += " Missing or unresolved context: " + ", ".join(issues)
        return {
            "id": row["assessment_id"],
            "encounter_id": e["id"],
            "assessment_id": row["assessment_id"],
            "event_key": e["id"],
            "statement": e["statement"],
            "label": n["label"],
            "rationale": n["rationale"],
            "scope": e["scope"],
            "temporal_scope": e["temporal_scope"],
            "trigger": e["trigger"],
            "consequence": n["consequence"],
            "evidence_quote": n["evidence_quote"],
            "emission_sha256": n["emission_sha256"],
            "proposal_id": row["record_id"],
            "source": {
                "type": "intention",
                "author": agent_id,
                "origin": e["origin"].removeprefix("explicit_"),
                "conversation_id": n["conversation_id"],
                "message_id": int(e["source"]["source_id"]),
                "message_sha256": e["source"]["source_sha256"],
                "parent_message_id": n["parent_message_id"],
                "evidence_sha256": n["parent_sha256"],
                "activity": "internal",
                "lineage": e["lineage"],
                "scope": e["scope"],
                "temporal_scope": e["temporal_scope"],
            },
            "policy_version": a["policy_version"] if a else "belief-v2-explicit-deferred",
            "mode": "shadow",
            "created_at": e["received_at"],
            "assessed_at": a["completed_at"] if a else None,
            "status": "complete" if completed else "assessing",
            "decision": "needs_review" if row["first_occurrence"] else "repetition",
            "reason": reason,
            "recommendation": "needs_review",
            "context_issues": issues,
            "comparisons": [],
            "uncompared_count": 0,
            "evaluation": {
                "status": a["evaluator_status"] if a else "pending",
                "answers": {},
                "reason": a["abstain_reason"] if a else "assessment_pending",
                "input_sha256": row["request_hash"],
            },
        }

    @with_connection
    def trace(self, agent_id: str, encounter_id: str, phase: str) -> None:
        from backend.storage.repositories.cognitive.belief_admission import AdmissionRepository

        with self.atomic():
            receipt = self.projection(agent_id, encounter_id)
            if (
                not self._conn()
                .execute("SELECT 1 FROM notifications WHERE id=?", (f"{receipt['id']}:{phase}",))
                .fetchone()
            ):
                AdmissionRepository(self._db_path)._trace(receipt, phase=phase)

    @with_connection
    def history(self, proposal_id: str) -> list[dict[str, Any]]:
        if (
            not self._conn()
            .execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='belief_explicit_annotations'")
            .fetchone()
        ):
            return []
        rows = (
            self._conn()
            .execute(
                "SELECT e.agent_id,e.id FROM belief_encounters e JOIN belief_review_claims c "
                "ON c.agent_id=e.agent_id AND c.id=e.claim_id JOIN belief_explicit_annotations n "
                "ON n.agent_id=e.agent_id AND n.encounter_id=e.id WHERE c.record_id=? ORDER BY e.received_at DESC,e.rowid DESC LIMIT 50",
                (proposal_id,),
            )
            .fetchall()
        )
        return [self.projection(str(row[0]), str(row[1])) for row in rows]
