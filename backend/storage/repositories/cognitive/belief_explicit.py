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
        if e["origin"] in {"document", "shared_note", "web"}:
            from backend.storage.repositories.cognitive.belief_sources import BeliefSourceRepository

            if (
                not self._conn()
                .execute(
                    "SELECT 1 FROM conversations WHERE id=? AND LOWER(agent_id)=?", (n["conversation_id"], agent_id)
                )
                .fetchone()
            ):
                return False
            sources = BeliefSourceRepository(self._db_path)
            if e["source"]["context_status"] == "available":
                material = sources.bound_snapshot(agent_id, e["origin"], e["source"]["source_id"])
                return bool(material and material["hash"] == e["source"]["source_sha256"])
            material = sources.snapshot(agent_id, n["conversation_id"], e["origin"], e["source"]["source_id"])
            return bool(
                e["source"]["context_status"] != "available"
                and (e["origin"] == "web" or material["hash"] == e["source"]["source_sha256"])
            )
        if e["origin"] == "conversation_pattern":
            # No owned originating messages supplied: retained as unavailable, never warrant.
            return e["source"]["context_status"] != "available" and n["conversation_id"] is None
        bindings = [(e["source"]["source_id"], e["source"]["source_sha256"], e["origin"] != "passive_chat")]
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
    def projection(self, agent_id: str, encounter_id: str, assessment_id: str | None = None) -> dict[str, Any]:
        row = (
            self._conn()
            .execute(
                "SELECT e.encounter_json,e.request_hash,e.claim_id,c.record_id,n.annotations_json,COALESCE(a.id,n.assessment_id) assessment_id,l.receipt,"
                "(SELECT MIN(e2.rowid) FROM belief_encounters e2 WHERE e2.agent_id=e.agent_id AND e2.claim_id=e.claim_id)=e.rowid first_occurrence "
                "FROM belief_encounters e JOIN belief_review_claims c ON c.agent_id=e.agent_id AND c.id=e.claim_id "
                "JOIN belief_explicit_annotations n ON n.agent_id=e.agent_id AND n.encounter_id=e.id "
                "LEFT JOIN belief_review_assessments a ON a.agent_id=e.agent_id AND a.encounter_id=e.id AND a.id=COALESCE(?,"
                "(SELECT a2.id FROM belief_review_assessments a2 JOIN belief_admission l2 ON l2.id=a2.ledger_id "
                "WHERE a2.agent_id=e.agent_id AND a2.encounter_id=e.id ORDER BY l2.rowid DESC LIMIT 1)) "
                "LEFT JOIN belief_admission l ON l.id=a.ledger_id WHERE e.agent_id=? AND e.id=?",
                (assessment_id, agent_id, encounter_id),
            )
            .fetchone()
        )
        if row is None or (assessment_id and row["assessment_id"] != assessment_id):
            raise ConstraintViolation("Explicit emission annotation missing", entity="belief_intake")
        e = json.loads(row["encounter_json"])
        from backend.storage.repositories.cognitive.belief_lineage import BeliefLineageRepository

        source_accounting = BeliefLineageRepository(self._db_path).observation(agent_id, encounter_id)
        n = json.loads(row["annotations_json"])
        a = json.loads(row["receipt"]) if row["receipt"] else None
        completed = bool(a and a["completed_at"])
        issues = list(n["context_issues"])
        reason = "V2 evaluator deferred to T9; no adoption authority."
        evaluated = bool(a and a["policy_version"] == "belief-v2-advisory-v1")
        resolved = (
            next((r["context"] for r in a.get("referent_contexts", []) if r["record_id"] == row["record_id"]), None)
            if evaluated and a and a["referent_status"] == "validated"
            else None
        )
        if resolved:
            issues = [
                issue
                for issue in issues
                if issue
                not in {
                    "scope_and_temporal_scope_unresolved",
                    "unresolved_referent",
                    "missing_scope",
                    "missing_temporal_scope",
                }
            ]
        recommendation = "needs_review"
        if evaluated and a:
            reason = "Advisory assessment; relation, consequence and warrant remain separate. No adoption authority."
            if a["evaluator_status"] == "evaluated":
                labels = {r["relation"] for r in a["relations"]}
                recommendation = (
                    "conflict"
                    if "contradiction" in labels
                    else "repetition"
                    if "equivalent" in labels
                    else "extension"
                    if "extension" in labels
                    else "needs_review"
                )
        if a and a["evaluator_status"] == "stale":
            reason = "Emission or parent context changed during checkpoint completion; assessment is stale."
        if issues:
            reason += " Missing or unresolved context: " + ", ".join(issues)
        answers: dict[str, Any] = {}
        uncompared = 0
        if evaluated and a:
            for exclusion in a["exclusions"]:
                prefix, _, count = exclusion.partition(":")
                if prefix == "uncompared_in_bounded_scan" and count.isdecimal() and len(count) <= 3:
                    uncompared = min(200, int(count))
        if evaluated and a and a["evaluator_status"] == "evaluated":
            names = {
                "empirical_traced": "grounding",
                "artistic_axiomatic": "artistic_grounding",
                "unresolved_tension": "tension",
            }
            for dimension in a["warrant_dimensions"]:
                if dimension["name"] in names:
                    answers[names[dimension["name"]]] = {
                        "choice": dimension["basis"].partition("=")[2],
                        "confidence": a["assessment_confidence"],
                    }
            if a["challenge"].startswith("Consequence="):
                answers["consequence"] = {
                    "choice": a["challenge"].split(";", 1)[0].partition("=")[2],
                    "confidence": a["assessment_confidence"],
                }
            for i, relation in enumerate(a["relations"]):
                answers[f"relation_{i}"] = {
                    "choice": relation["raw_relation"],
                    "confidence": relation["assessment_confidence"],
                }
        return {
            "id": row["assessment_id"],
            "encounter_id": e["id"],
            "assessment_id": row["assessment_id"],
            "event_key": e["id"],
            "statement": e["statement"],
            "label": n["label"],
            "rationale": n["rationale"],
            "scope": resolved["scope"] if resolved else e["scope"],
            "temporal_scope": resolved["temporal_scope"] if resolved else e["temporal_scope"],
            "trigger": e["trigger"],
            "consequence": n["consequence"],
            "evidence_quote": n["evidence_quote"],
            "emission_sha256": n["emission_sha256"],
            "proposal_id": row["record_id"],
            "source": {
                "type": "intention" if e["origin"].startswith("explicit_") else e["source"]["source_type"],
                "author": "unknown" if e["origin"] in {"document", "shared_note", "web"} else agent_id,
                "origin": e["origin"].removeprefix("explicit_"),
                "conversation_id": n["conversation_id"],
                "message_id": int(e["source"]["source_id"])
                if n["conversation_id"] and e["source"]["source_type"] in {"message", "chat_turn"}
                else None,
                "source_id": e["source"]["source_id"],
                "source_version": e["source"]["source_version"],
                "reference": e["source"]["reference"],
                "unavailable_reason": e["source"]["unavailable_reason"],
                "message_sha256": e["source"]["source_sha256"],
                "parent_message_id": n["parent_message_id"],
                "evidence_sha256": n["parent_sha256"],
                "activity": e["source"]["activity"],
                "context_status": e["source"]["context_status"],
                "lineage": e["lineage"],
                "scope": e["scope"],
                "temporal_scope": e["temporal_scope"],
            },
            "policy_version": a["policy_version"] if a else "belief-v2-explicit-deferred",
            "mode": "shadow",
            "created_at": a["started_at"] if a else e["received_at"],
            "assessed_at": a["completed_at"] if a else None,
            "status": "complete" if completed else "assessing",
            "decision": "needs_review" if row["first_occurrence"] else "repetition",
            "reason": reason,
            "recommendation": recommendation,
            "context_issues": issues,
            "origin_context_issues": n["context_issues"],
            "source_accounting": source_accounting,
            "exclusions": a["exclusions"] if a else [],
            "comparisons": [
                {
                    "id": c["record_id"],
                    "label": c["record_id"],
                    "kind": c["record_kind"],
                    "statement": c["statement"],
                    "statement_sha256": c["statement_sha256"],
                    "scope": c["scope"],
                    "temporal_scope": c["temporal_scope"],
                }
                for c in a["comparison_snapshots"]
            ]
            if a
            else [],
            "relations": a["relations"] if a else [],
            "warrant_dimensions": a["warrant_dimensions"] if a else [],
            "challenge": a["challenge"] if a else "",
            "referent_status": a["referent_status"] if a else "unknown",
            "referent_contexts": a.get("referent_contexts", []) if a else [],
            "previous_assessment_id": a["previous_assessment_id"] if a else None,
            "uncompared_count": uncompared,
            "evaluation": {
                "status": a["evaluator_status"] if a else "pending",
                "answers": answers,
                "reason": a["abstain_reason"] if a else "assessment_pending",
                "input_sha256": a["context_hash"] if evaluated and a else row["request_hash"],
                "model": a["returned_model"] if a else None,
                "requested_model": a["requested_model"] if a else None,
                "confidence": a["assessment_confidence"] if a else None,
            },
        }

    @with_connection
    def trace(self, agent_id: str, encounter_id: str, phase: str, assessment_id: str | None = None) -> None:
        from backend.storage.repositories.cognitive.belief_admission import AdmissionRepository

        with self.atomic():
            receipt = self.projection(agent_id, encounter_id, assessment_id)
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
                "SELECT e.agent_id,e.id,a.id FROM belief_encounters e JOIN belief_review_claims c "
                "ON c.agent_id=e.agent_id AND c.id=e.claim_id JOIN belief_explicit_annotations n "
                "ON n.agent_id=e.agent_id AND n.encounter_id=e.id JOIN belief_review_assessments a ON a.agent_id=e.agent_id AND a.encounter_id=e.id "
                "JOIN belief_admission l ON l.id=a.ledger_id WHERE c.record_id=? ORDER BY l.rowid DESC LIMIT 50",
                (proposal_id,),
            )
            .fetchall()
        )
        return [self.projection(str(row[0]), str(row[1]), str(row[2])) for row in rows]
