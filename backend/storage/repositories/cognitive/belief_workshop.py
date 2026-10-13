"""Atomic authenticated-command persistence; no provider, family-merger or tool ports."""

import hashlib
import json
from dataclasses import asdict
from typing import Any, Literal, cast

from backend.errors import ConstraintViolation
from backend.storage.belief_review import DecisionWrite
from backend.storage.connection import with_connection
from backend.storage.repositories.cognitive.belief_assessment import BeliefAssessmentRepository
from backend.storage.repositories.cognitive.belief_review import BeliefDecisionRepository

TRANSITIONS: dict[str, Literal["adopted", "declined", "deferred", "awaiting_context", "under_review"]] = {
    "adopt": "adopted",
    "decline": "declined",
    "defer": "deferred",
    "request_context": "awaiting_context",
    "request_review": "under_review",
}


class BeliefWorkshopRepository(BeliefDecisionRepository):
    @with_connection
    def snapshot(self, agent: str, record: str) -> dict[str, Any]:
        self._record_statement(agent, record)  # Reject conflicting aliases before choosing presentation.
        raw = BeliefAssessmentRepository(self._db_path).record(agent, record, "any")
        state = self.get_state(agent, record)
        raw["statement_sha256"] = self._record_hash(agent, record)
        raw["state"] = asdict(state) if state else None
        return raw

    @with_connection
    def prior(self, agent: str, command: str, input_hash: str) -> dict[str, Any] | None:
        row = (
            self._conn()
            .execute(
                "SELECT input_hash,receipt_json FROM belief_workshop_commands WHERE agent_id=? AND id=?",
                (agent, command),
            )
            .fetchone()
        )
        if row and row[0] != input_hash:
            raise ConstraintViolation("Workshop command identity reused with changed input", entity="belief_workshop")
        return cast(dict[str, Any], json.loads(row[1])) if row else None

    @with_connection
    def commit(
        self,
        write: DecisionWrite,
        command_id: str,
        input_hash: str,
        receipt: str,
        fingerprints: tuple[tuple[str, str], ...],
    ) -> dict[str, Any]:
        with self.atomic():
            prior = self.prior(write.agent_id, command_id, input_hash)
            if prior:
                return prior
            packet = cast(dict[str, Any], json.loads(receipt))
            command = packet["command"]
            action = command["action"]
            if action in TRANSITIONS and write.next_state != TRANSITIONS[action]:
                raise ConstraintViolation("Workshop action/state mismatch", entity="belief_workshop")
            if action not in TRANSITIONS and action not in {"revise", "supersede", "resurface"}:
                raise ConstraintViolation("Workshop action not implemented", entity="belief_workshop")
            if action in TRANSITIONS and write.previous_state in {"adopted", "superseded"}:
                raise ConstraintViolation(
                    "Existing commitment requires linked revision workflow", entity="belief_workshop"
                )
            for record, fingerprint in fingerprints:
                if self.snapshot(write.agent_id, record)["fingerprint"] != fingerprint:
                    raise ConstraintViolation("Workshop source or comparison changed", entity="belief_workshop")
            if action in {"revise", "supersede", "resurface"}:
                source = self.snapshot(write.agent_id, packet["record_id"])
                if (
                    source["statement_sha256"] != command["expected_statement_sha256"]
                    or not source["state"]
                    or source["state"]["state"]
                    not in ({"adopted"} if action in {"revise", "supersede"} else {"adopted", "superseded"})
                ):
                    raise ConstraintViolation("Linked command source is no longer current", entity="belief_workshop")
            if action == "supersede":
                target = self.snapshot(write.agent_id, command["target_record_id"])
                target_state = target["state"]
                if (
                    target["statement_sha256"] != command["expected_target_statement_sha256"]
                    or not target_state
                    or target_state["state"] != "adopted"
                    or target_state["version"] != command["expected_target_review_version"]
                ):
                    raise ConstraintViolation("Supersession target changed or is not adopted", entity="belief_workshop")
            if action == "resurface" and command["assessment_ids"]:
                raise ConstraintViolation("Resurfacing cannot add assessments", entity="belief_workshop")
            if action == "revise":
                if write.record_id != packet["linked_record_id"] or write.next_state != "candidate":
                    raise ConstraintViolation("Revision candidate binding mismatch", entity="belief_workshop")
                if source["kind"] != "belief":
                    raise ConstraintViolation("Only an adopted belief can be revised", entity="belief_workshop")
                source = (
                    self._conn()
                    .execute(
                        "SELECT label FROM belief_nodes WHERE LOWER(agent_id)=? AND id=?",
                        (write.agent_id, packet["record_id"]),
                    )
                    .fetchone()
                )
                if source is None:
                    raise ConstraintViolation("Revision source is not a persisted belief", entity="belief_workshop")
                successor = write.record_id
                statement = command["statement"]
                trace = json.dumps(
                    {
                        "revision_of": packet["record_id"],
                        "prior_statement_sha256": command["expected_statement_sha256"],
                        "warrant": "none_added",
                    }
                )
                self._conn().execute(
                    "INSERT INTO belief_proposals(id,agent_id,provisional_statement,source_trace,initial_signature,nucleation_mass,confidence,status,suggested_label,suggested_statement) "
                    "VALUES (?,?,?,?,?,0,0,'pending',?,?)",
                    (successor, write.agent_id, statement, trace, json.dumps([0.0] * 16), source["label"], statement),
                )
            self.commit_decision(write)
            if action == "adopt":
                self._materialize(write)
            self._conn().execute(
                "INSERT INTO belief_workshop_commands VALUES (?,?,?,?,?,?,?,?)",
                (
                    write.agent_id,
                    command_id,
                    packet["record_id"],
                    input_hash,
                    write.id,
                    action,
                    write.timestamp,
                    receipt,
                ),
            )
            if action in {"revise", "supersede"}:
                target_id = write.record_id if action == "revise" else command["target_record_id"]
                source_id = packet["record_id"]
                self._conn().execute(
                    "INSERT INTO belief_revision_links(agent_id,source_record_id,successor_record_id,action,source_statement_sha256,successor_statement_sha256,command_id,decision_id,timestamp) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        write.agent_id,
                        source_id,
                        target_id,
                        action,
                        command["expected_statement_sha256"],
                        write.statement_hash if action == "revise" else command["expected_target_statement_sha256"],
                        command_id,
                        write.id,
                        write.timestamp,
                    ),
                )
            self._conn().execute(
                "INSERT INTO notifications(id,type,timestamp,snippet,source,source_type,source_id,read,dismissed) "
                "VALUES (?,'trace',?,?,'belief_workshop_v2','belief_review',?,0,0)",
                (write.id + ":review", write.timestamp, receipt, packet["record_id"]),
            )
            return packet

    def _materialize(self, write: DecisionWrite) -> None:
        conn = self._conn()
        existing = conn.execute(
            "SELECT 1 FROM belief_nodes WHERE LOWER(agent_id)=? AND id=?", (write.agent_id, write.record_id)
        ).fetchone()
        if existing:
            return
        proposal = conn.execute(
            "SELECT * FROM belief_proposals WHERE LOWER(agent_id)=? AND id=?", (write.agent_id, write.record_id)
        ).fetchone()
        if proposal is None:
            raise ConstraintViolation("Adoption representation unavailable", entity="belief_workshop")
        from backend.storage.repositories.cognitive.belief import BeliefRepository

        vector = BeliefRepository(self._db_path).validate_and_format_vector(str(proposal["initial_signature"]))
        label = str(proposal["suggested_label"] or "emergent-belief")
        if conn.execute(
            "SELECT 1 FROM belief_nodes WHERE LOWER(agent_id)=? AND label=?", (write.agent_id, label)
        ).fetchone():
            label = f"{label}-{write.record_id[:12]}"
        # Preserve existing structural quantities; missing geometry is an explicit unscored zero projection.
        genesis = json.dumps(
            {
                "source_trace": proposal["source_trace"],
                "adoption_decision_id": write.id,
                "geometry": "structural_projection_no_new_measurement",
            }
        )
        conn.execute(
            "INSERT INTO belief_nodes(id,agent_id,label,statement,origin,confidence,ontological_mass,somatic_anchor,vector_16d,"
            "lifecycle_stage,evolved_from_proposal,genesis_materials,version,last_reinforced_at,atrophy_accounted_at) "
            "VALUES (?,?,?,?,'emergent',?,?,'none',?,'crystallized',?,?,1,?,?)",
            (
                write.record_id,
                write.agent_id,
                label,
                self._record_statement(write.agent_id, write.record_id),
                proposal["confidence"],
                proposal["nucleation_mass"],
                vector,
                write.record_id,
                genesis,
                write.timestamp,
                write.timestamp,
            ),
        )
        conn.execute(
            "UPDATE belief_proposals SET status='adopted',updated_at=? WHERE LOWER(agent_id)=? AND id=?",
            (write.timestamp, write.agent_id, write.record_id),
        )
        conn.execute(
            "INSERT INTO belief_statement_versions(id,belief_id,version,statement,vector_16d,change_reason,created_at) VALUES (?,?,1,?,?,?,?)",
            (
                hashlib.sha256((write.id + ":version").encode()).hexdigest(),
                write.record_id,
                self._record_statement(write.agent_id, write.record_id),
                vector,
                "Operator scoped adoption: " + write.id,
                write.timestamp,
            ),
        )

    @with_connection
    def family(self, agent: str, record: str) -> dict[str, Any]:
        own = self.snapshot(agent, record)
        nominees = BeliefAssessmentRepository(self._db_path).nominees(agent, record)
        terms = set(str(own["statement"]).lower().split())
        nominees.sort(key=lambda row: (-len(terms & set(str(row["statement"]).lower().split())), str(row["id"])))
        members = [self.snapshot(agent, str(row["id"])) for row in nominees[:10]]
        packets = (
            self._conn()
            .execute(
                "SELECT receipt_json FROM belief_workshop_commands WHERE agent_id=? AND record_id=? ORDER BY rowid DESC LIMIT 50",
                (agent, record),
            )
            .fetchall()
        )
        counters = (
            self._conn()
            .execute(
                "SELECT receipt_json FROM belief_workshop_commands WHERE agent_id=? AND record_id=? AND action='decline' ORDER BY rowid DESC LIMIT 50",
                (agent, record),
            )
            .fetchall()
        )
        count = (
            self._conn()
            .execute("SELECT count(*) FROM belief_workshop_commands WHERE agent_id=? AND record_id=?", (agent, record))
            .fetchone()[0]
        )
        declines = (
            self._conn()
            .execute(
                "SELECT count(*) FROM belief_workshop_commands WHERE agent_id=? AND record_id=? AND action='decline'",
                (agent, record),
            )
            .fetchone()[0]
        )
        assessments = (
            self._conn()
            .execute(
                "SELECT l.receipt FROM belief_review_assessments a JOIN belief_admission l ON l.id=a.ledger_id JOIN belief_encounters e "
                "ON e.agent_id=a.agent_id AND e.id=a.encounter_id JOIN belief_review_claims c ON c.agent_id=e.agent_id AND c.id=e.claim_id "
                "WHERE a.agent_id=? AND c.record_id=? ORDER BY l.rowid DESC LIMIT 10",
                (agent, record),
            )
            .fetchall()
        )
        lineage = (
            self._conn()
            .execute(
                "SELECT source_record_id,successor_record_id,action,source_statement_sha256,successor_statement_sha256,command_id,decision_id,timestamp "
                "FROM belief_revision_links WHERE agent_id=? AND (source_record_id=? OR successor_record_id=?) ORDER BY timestamp DESC,command_id DESC LIMIT 50",
                (agent, record, record),
            )
            .fetchall()
        )
        lineage_count = (
            self._conn()
            .execute(
                "SELECT count(*) FROM belief_revision_links WHERE agent_id=? AND (source_record_id=? OR successor_record_id=?)",
                (agent, record, record),
            )
            .fetchone()[0]
        )
        return {
            "agent_id": agent,
            "record": own,
            "family": members,
            "nomination_only": True,
            "uncompared_in_bounded_scan": len(nominees) - len(members),
            "commands": [json.loads(row[0]) for row in packets],
            "counter_traces": [json.loads(row[0])["counter_trace"] for row in counters],
            "history_truncated": count > len(packets),
            "counter_traces_truncated": declines > len(counters),
            "command_count": count,
            "counter_trace_count": declines,
            "lineage_links": [
                {
                    "source_record_id": row[0],
                    "successor_record_id": row[1],
                    "action": row[2],
                    "source_statement_sha256": row[3],
                    "successor_statement_sha256": row[4],
                    "command_id": row[5],
                    "decision_id": row[6],
                    "timestamp": row[7],
                }
                for row in lineage
            ],
            "lineage_count": int(lineage_count),
            "lineage_truncated": lineage_count > len(lineage),
            "advisory_assessments": [
                {"receipt": json.loads(row[0]), "binding": "historical_requires_reassessment", "tool_authority": "none"}
                for row in assessments
            ],
            "command_relations": "historical_operator_declarations_not_current_verdicts",
            "tool_authority": "none",
            "participant_identity": "shared_operator_credential_not_personal_identity",
        }

    @with_connection
    def guard_legacy(self, record: str) -> None:
        if not self._conn().execute("SELECT 1 FROM sqlite_master WHERE name='belief_review_state'").fetchone():
            return
        if (
            self._conn()
            .execute(
                "SELECT 1 FROM belief_review_state WHERE record_id=? UNION ALL SELECT 1 FROM belief_review_claims WHERE record_id=? LIMIT 1",
                (record, record),
            )
            .fetchone()
        ):
            raise ConstraintViolation(
                "Managed belief requires version-bound v2 workshop command", entity="belief_workshop"
            )
