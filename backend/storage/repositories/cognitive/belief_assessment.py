"""Bounded advisory nomination and atomic provider claim/completion, without decisions."""

import hashlib
import json
from typing import Any, cast

from backend.errors import ConstraintViolation, ResourceNotFound
from backend.storage.belief_review import AssessmentWrite
from backend.storage.connection import with_connection
from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository
from backend.storage.repositories.cognitive.belief_review import BeliefReviewRepository


class BeliefAssessmentRepository(BeliefReviewRepository):
    @with_connection
    def latest(self, agent: str, encounter: str) -> str | None:
        row = (
            self._conn()
            .execute(
                "SELECT l.receipt FROM belief_review_assessments a JOIN belief_admission l ON l.id=a.ledger_id "
                "WHERE a.agent_id=? AND a.encounter_id=? ORDER BY l.rowid DESC LIMIT 1",
                (agent, encounter),
            )
            .fetchone()
        )
        return str(row[0]) if row else None

    @with_connection
    def annotations(self, agent: str, encounter: str) -> dict[str, Any]:
        row = (
            self._conn()
            .execute(
                "SELECT annotations_json FROM belief_explicit_annotations WHERE agent_id=? AND encounter_id=?",
                (agent, encounter),
            )
            .fetchone()
        )
        return cast(dict[str, Any], json.loads(row[0])) if row else {}

    @with_connection
    def source_current(self, agent: str, encounter: str) -> bool:
        row = self._encounter_row(agent, encounter)
        if not row["context_available"]:
            return False
        try:
            current = self._source_hash(agent, str(row["source_type"]), row["source_id"])
        except ResourceNotFound:
            return False
        if current is None or current != row["source_hash"]:
            return False
        if self.annotations(agent, encounter):
            return ExplicitBeliefRepository(self._db_path)._current_bindings(agent, encounter)
        return True

    @with_connection
    def record(self, agent: str, record: str, kind: str) -> dict[str, Any]:
        if kind == "belief":
            row = (
                self._conn()
                .execute(
                    "SELECT id,label,substr(statement,1,4001),lifecycle_stage FROM belief_nodes "
                    "WHERE id=? AND LOWER(agent_id)=?",
                    (record, agent),
                )
                .fetchone()
            )
        else:
            row = (
                self._conn()
                .execute(
                    "SELECT id,COALESCE(suggested_label,'emergent-belief'),substr(COALESCE(suggested_statement,provisional_statement),1,4001),status "
                    "FROM belief_proposals WHERE id=? AND LOWER(agent_id)=?",
                    (record, agent),
                )
                .fetchone()
            )
        if row is None:
            if kind == "any":
                return self.record(agent, record, "belief")
            raise ResourceNotFound("Comparison not found", entity="belief_assessment")
        state = (
            self._conn()
            .execute(
                "SELECT state,version,scope FROM belief_review_state WHERE agent_id=? AND record_id=?",
                (agent, record),
            )
            .fetchone()
        )
        linked = (
            self._conn()
            .execute(
                "SELECT e.id,e.encounter_json FROM belief_encounters e JOIN belief_review_claims c "
                "ON c.agent_id=e.agent_id AND c.id=e.claim_id WHERE e.agent_id=? AND c.record_id=? ORDER BY e.rowid DESC LIMIT 1",
                (agent, record),
            )
            .fetchone()
        )
        context = json.loads(linked[1]) if linked else None
        result: dict[str, Any] = {
            "id": str(row[0]),
            "label": str(row[1]),
            "statement": str(row[2]),
            "kind": "belief" if kind == "belief" else "proposal",
            "legacy_status": str(row[3]),
            "review_state": str(state[0]) if state else None,
            "review_version": int(state[1]) if state else None,
            "scope": context["scope"] if context else "",
            "temporal_scope": context["temporal_scope"] if context else "",
            "quote": context["source"]["quote"] if context else "",
            "source_hash": context["source"]["source_sha256"] if context else None,
            "source_current": self.source_current(agent, str(linked[0])) if linked else True,
            "context_provenance": "encounter:" + str(linked[0]) if linked else "stored-record:" + record,
            "state_scope": str(state[2]) if state else "",
        }
        result["fingerprint"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        return result

    @with_connection
    def nominees(self, agent: str, candidate: str) -> list[dict[str, Any]]:
        base = (
            "SELECT b.id,'belief' kind,b.lifecycle_stage legacy,s.state FROM belief_nodes b LEFT JOIN belief_review_state s "
            "ON s.agent_id=LOWER(b.agent_id) AND s.record_id=b.id WHERE LOWER(b.agent_id)=? AND b.label NOT LIKE 'skill:%' "
            "UNION ALL SELECT p.id,'proposal',p.status,s.state FROM belief_proposals p LEFT JOIN belief_review_state s "
            "ON s.agent_id=LOWER(p.agent_id) AND s.record_id=p.id WHERE LOWER(p.agent_id)=?"
        )
        strata = [
            (
                "adopted_or_legacy",
                100,
                "state='adopted' OR (state IS NULL AND kind='belief' AND legacy NOT IN ('collapsed','faded'))",
            ),
            (
                "pending",
                64,
                "kind='proposal' AND legacy IN ('pending','refined') AND (state IS NULL OR state IN ('candidate','awaiting_context','under_review'))",
            ),
            ("deferred", 32, "state='deferred'"),
            ("history", 4, "kind='belief' AND legacy IN ('collapsed','faded') AND (state IS NULL OR state!='adopted')"),
        ]
        result = []
        seen: set[str] = set()
        for stratum, limit, predicate in strata:
            rows = (
                self._conn()
                .execute(
                    "SELECT id,kind FROM (" + base + ") WHERE id!=? AND (" + predicate + ") ORDER BY id LIMIT ?",
                    (agent, agent, candidate, limit),
                )
                .fetchall()
            )
            for row in rows:
                if row[0] not in seen:
                    seen.add(str(row[0]))
                    item = self.record(agent, str(row[0]), str(row[1]))
                    item["stratum"] = stratum
                    result.append(item)
        return result

    @with_connection
    def claim(self, pending: AssessmentWrite, deferred: AssessmentWrite, limit: int) -> tuple[bool, str]:
        with self.atomic():
            row = (
                self._conn()
                .execute(
                    "SELECT 1 FROM belief_review_assessments WHERE agent_id=? AND id=?",
                    (pending.agent_id, pending.id),
                )
                .fetchone()
            )
            if row:
                saved = str(self._assessment_row(pending.agent_id, pending.id)["receipt"])
                old, new = json.loads(saved), json.loads(pending.receipt_json)
                if any(
                    old[key] != new[key]
                    for key in ("context_hash", "requested_model", "candidate_id", "policy_version", "rubric_version")
                ):
                    raise ConstraintViolation("Assessment retry changed context", entity="belief_assessment")
                return False, saved
            count = (
                self._conn()
                .execute(
                    "SELECT count(*) FROM belief_admission WHERE agent_id=? AND assessment_id IS NOT NULL AND status='assessing'",
                    (pending.agent_id,),
                )
                .fetchone()[0]
            )
            payload = self.start_assessment(pending)
            if count >= limit:
                return False, self.complete_assessment(deferred)
            return True, payload

    @with_connection
    def finish(self, write: AssessmentWrite, fingerprints: tuple[tuple[str, str, str], ...]) -> str:
        with self.atomic():
            changed = False
            for record, kind, expected in fingerprints:
                try:
                    changed |= self.record(write.agent_id, record, kind)["fingerprint"] != expected
                except ResourceNotFound:
                    changed = True
            if changed:
                from dataclasses import replace

                write = replace(write, receipt_json=write.stale_json)
            if self.annotations(write.agent_id, write.encounter_id):
                return ExplicitBeliefRepository(self._db_path).complete(write)
            return self.complete_assessment(write)
