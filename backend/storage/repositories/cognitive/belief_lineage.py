"""Atomic forward source accounting and agent-scoped bounded readers, without decisions."""

import hashlib
import json
from typing import Any, cast

from backend.errors import ConstraintViolation
from backend.storage.belief_review import EncounterWrite
from backend.storage.connection import with_connection
from backend.storage.repositories.cognitive.belief_review import BeliefReviewRepository


class BeliefLineageRepository(BeliefReviewRepository):
    @with_connection
    def append(self, value: EncounterWrite, claim: str, record: str) -> None:
        # Called inside encounter registration's writer transaction; never retrofits old encounters.
        if value.accounting_json is None:
            raise ConstraintViolation("Source accounting snapshot required", entity="belief_lineage")
        receipt = cast(dict[str, Any], json.loads(value.accounting_json))
        previous = (
            self._conn()
            .execute(
                "SELECT count(*) FROM belief_source_observations WHERE agent_id=? AND claim_id=?",
                (value.agent_id, claim),
            )
            .fetchone()[0]
        )
        receipt.update(record_id=record, claim_id=claim, recurrence=previous > 0)
        payload = json.dumps(receipt, sort_keys=True)
        self._conn().execute(
            "INSERT INTO belief_source_observations VALUES (?,?,?,?,?,?,?,?)",
            (
                value.agent_id,
                value.id,
                record,
                claim,
                int(receipt["internal_activity"]),
                int(previous > 0),
                value.received_at,
                payload,
            ),
        )
        quantities = [("source_lineage_observed", "source_lineage")]
        if receipt["internal_activity"]:
            quantities.append(("internal_activity_recorded", "internal_activity"))
        if previous:
            quantities.append(("recurrence_recorded", "recurrence"))
        for kind, quantity in quantities:
            event = {
                "id": hashlib.sha256((value.agent_id + ":" + value.id + ":" + kind).encode()).hexdigest(),
                "agent_id": value.agent_id,
                "record_id": record,
                "encounter_id": value.id,
                "event_type": kind,
                "source_type": value.source_type,
                "source_id": value.source_id,
                "timestamp": value.received_at,
                "impact_quantity": quantity,
                "impact_unit": "encounter_observation",
                "impact_value": 1.0,
                "delta_mass": 0.0,
                "confidence_delta": 0.0,
                "policy_version": receipt["policy_version"],
                "independent_warrant": "unverified",
            }
            self._conn().execute(
                "INSERT INTO belief_review_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    value.agent_id,
                    event["id"],
                    record,
                    value.id,
                    kind,
                    quantity,
                    event["impact_unit"],
                    1.0,
                    0.0,
                    0.0,
                    value.received_at,
                    json.dumps(event, sort_keys=True),
                ),
            )

    @with_connection
    def observation(self, agent: str, encounter: str) -> dict[str, Any] | None:
        self._encounter_row(agent, encounter)
        row = (
            self._conn()
            .execute(
                "SELECT receipt_json FROM belief_source_observations WHERE agent_id=? AND encounter_id=?",
                (agent, encounter),
            )
            .fetchone()
        )
        return cast(dict[str, Any], json.loads(row[0])) if row else None

    @with_connection
    def summary(self, agent: str, record: str, limit: int = 50) -> dict[str, Any]:
        self._record_statement(agent, record)
        limit = min(50, max(1, limit))
        rows = (
            self._conn()
            .execute(
                "SELECT receipt_json FROM belief_source_observations WHERE agent_id=? AND record_id=? ORDER BY rowid DESC LIMIT ?",
                (agent, record, limit),
            )
            .fetchall()
        )
        counts = (
            self._conn()
            .execute(
                "SELECT count(*),COALESCE(sum(internal_activity),0),COALESCE(sum(recurrence),0) "
                "FROM belief_source_observations WHERE agent_id=? AND record_id=?",
                (agent, record),
            )
            .fetchone()
        )
        total = (
            self._conn()
            .execute(
                "SELECT count(*) FROM belief_encounters e JOIN belief_review_claims c ON c.agent_id=e.agent_id AND c.id=e.claim_id "
                "WHERE e.agent_id=? AND c.record_id=?",
                (agent, record),
            )
            .fetchone()[0]
        )
        return {
            "record_id": record,
            "agent_id": agent,
            "observed_encounters": counts[0],
            "internal_activity": counts[1],
            "recurrence": counts[2],
            "verified_independent_groups": 0,
            "independent_warrant": "unverified",
            "historical_unrecorded_encounters": total - counts[0],
            "truncated": counts[0] > len(rows),
            "observations": [json.loads(row[0]) for row in rows],
        }

    @with_connection
    def events(self, agent: str, record: str, limit: int = 50) -> list[dict[str, Any]]:
        self._record_statement(agent, record)
        rows = (
            self._conn()
            .execute(
                "SELECT receipt_json FROM belief_review_events WHERE agent_id=? AND record_id=? ORDER BY rowid DESC LIMIT ?",
                (agent, record, min(50, max(1, limit))),
            )
            .fetchall()
        )
        return [json.loads(row[0]) for row in rows]
