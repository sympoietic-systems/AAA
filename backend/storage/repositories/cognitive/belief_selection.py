"""Bounded agent-owned selection snapshots; reads cannot change belief standing."""

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from backend.errors import ConstraintViolation, GlitchError
from backend.services.belief_review_contracts import ReviewDecision
from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


@dataclass(frozen=True)
class SelectionRecord:
    id: str
    label: str
    statement: str
    confidence: float
    ontological_mass: float
    vector_16d: str
    lifecycle_stage: str
    stratum: str
    review_state: str
    standing: str
    scope: str
    temporal_scope: str
    challenges: tuple[str, ...]
    dissent: tuple[str, ...]
    decision_id: str | None
    history_truncated: bool
    counter_trace: dict[str, Any] | None
    kind: str


@dataclass(frozen=True)
class SelectionSnapshot:
    records: tuple[SelectionRecord, ...]
    truncated: bool


class BeliefSelectionRepository(BaseRepository):
    @with_connection
    def snapshot(self, agent: str) -> SelectionSnapshot:
        # One SQL statement supplies a consistent read snapshot. Four overflow probes
        # disclose truncation; at most 200 nominations survive those probes.
        base = (
            "SELECT b.id,substr(b.label,1,201) label,substr(b.statement,1,4001) statement,b.confidence,b.ontological_mass mass,substr(b.vector_16d,1,4097) vector_16d,b.lifecycle_stage legacy,'belief' kind "
            "FROM belief_nodes b WHERE LOWER(b.agent_id)=? UNION ALL "
            "SELECT p.id,substr(COALESCE(p.suggested_label,'emergent-belief'),1,201),substr(COALESCE(p.suggested_statement,p.provisional_statement),1,4001),"
            "p.confidence,p.nucleation_mass,substr(p.initial_signature,1,4097),p.status,'proposal' FROM belief_proposals p "
            "WHERE LOWER(p.agent_id)=? AND NOT EXISTS (SELECT 1 FROM belief_nodes b WHERE LOWER(b.agent_id)=? AND b.id=p.id)"
        )
        query = (
            "WITH base AS ("
            + base
            + "), classified AS (SELECT b.*,s.state,s.statement_hash,s.scope state_scope,s.decision_id,s.version state_version,d.version decision_version,"
            "substr(d.decision_json,1,32769) decision_json,"
            "(SELECT substr(e.encounter_json,1,32769) FROM belief_encounters e JOIN belief_review_claims c "
            "ON c.agent_id=e.agent_id AND c.id=e.claim_id WHERE e.agent_id=? AND c.record_id=b.id ORDER BY e.rowid DESC LIMIT 1) encounter_json,"
            "(SELECT substr(w.receipt_json,1,32769) FROM belief_workshop_commands w WHERE w.agent_id=? AND w.record_id=b.id "
            "AND w.action='decline' ORDER BY w.rowid DESC LIMIT 1) decline_json,"
            "CASE WHEN s.state IN ('declined','superseded') OR (b.kind='proposal' AND b.legacy='rejected') OR (b.kind='belief' AND (b.legacy IN ('collapsed','faded') OR b.confidence<0.20)) THEN 'history' "
            "WHEN s.state='deferred' THEN 'deferred' "
            "WHEN b.kind='proposal' OR s.state IN ('candidate','awaiting_context','under_review') THEN 'pending' ELSE 'active' END stratum "
            "FROM base b LEFT JOIN belief_review_state s ON s.agent_id=? AND s.record_id=b.id "
            "LEFT JOIN belief_review_decisions d ON d.agent_id=s.agent_id AND d.id=s.decision_id) "
            + " UNION ALL ".join(
                f"SELECT * FROM (SELECT *,substr(statement,1,4001) bounded_statement FROM classified WHERE stratum='{name}' ORDER BY id LIMIT {limit + 1})"
                for name, limit in (("active", 100), ("pending", 64), ("deferred", 32), ("history", 4))
            )
        )
        conn = self._conn()
        deadline = time.monotonic() + 3.0
        conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        try:
            rows = conn.execute(query, (agent,) * 6).fetchall()
        except sqlite3.OperationalError as error:
            if error.sqlite_errorcode == sqlite3.SQLITE_INTERRUPT:
                raise GlitchError(
                    "Belief selection read budget exceeded",
                    status_code=503,
                    kind="resource_exhausted",
                    entity="belief_selection",
                ) from error
            raise
        finally:
            conn.set_progress_handler(None, 0)
        records: list[SelectionRecord] = []
        counts: dict[str, int] = {}
        truncated = False
        limits = {"active": 100, "pending": 64, "deferred": 32, "history": 4}
        for row in rows:
            name = str(row["stratum"])
            counts[name] = counts.get(name, 0) + 1
            if counts[name] > limits[name]:
                truncated = True
                continue
            statement = str(row["bounded_statement"])
            if len(statement) > 4000:
                truncated = True
                continue
            digest = hashlib.sha256(statement.encode()).hexdigest()
            state = str(row["state"] or "legacy_unreviewed")
            standing = "provisional" if row["state"] else "legacy_unreviewed"
            scope, temporal = str(row["state_scope"] or "unknown"), "unknown"
            challenges: list[str] = []
            dissent: list[str] = []
            decision_id = None
            history_truncated = False
            counter_trace = None
            for field in ("encounter_json", "decline_json"):
                raw = row[field]
                if raw and len(raw) > 32768:
                    history_truncated = True
                    continue
                try:
                    content: dict[str, Any] = json.loads(raw) if raw else {}
                except (ValueError, TypeError) as error:
                    raise ConstraintViolation("Invalid stored selection context", entity="belief_selection") from error
                if field == "encounter_json":
                    if content and row["state"] is None and row["kind"] == "proposal":
                        state = (
                            "candidate"
                            if content.get("source", {}).get("context_status") == "available"
                            else "awaiting_context"
                        )
                        standing = "provisional"
                    if not row["state_scope"]:
                        scope = str(content.get("scope") or "unknown")[:500]
                    temporal = str(content.get("temporal_scope") or "unknown")[:250]
                else:
                    counter = content.get("counter_trace") or {}
                    if counter:
                        counter_trace = counter
                        challenges.append(str(counter.get("challenge") or "unknown")[:1000])
                        dissent.extend(str(x)[:2000] for x in counter.get("dissent", [])[:2])
            raw_decision = row["decision_json"]
            if raw_decision and len(raw_decision) <= 32768:
                try:
                    decision = ReviewDecision.model_validate_json(raw_decision)
                except ValidationError as error:
                    raise ConstraintViolation("Invalid stored selection decision", entity="belief_selection") from error
                current = (
                    decision.agent_id == agent
                    and decision.record_id == row["id"]
                    and decision.id == row["decision_id"]
                    and decision.statement_sha256 == digest
                    and row["statement_hash"] == digest
                    and decision.next_state == row["state"]
                    and decision.scope == row["state_scope"]
                    and decision.expected_review_version + 1 == row["state_version"] == row["decision_version"]
                )
                if current:
                    decision_id = decision.id
                    scope = decision.scope
                    challenges.append(decision.challenge)
                    dissent.extend(decision.dissent[:2])
                    if state == "adopted" and decision.authority == "operator_review":
                        standing = "situated_commitment"
                else:
                    standing = "stale_review_binding"
            elif state == "adopted":
                standing = "unverified_adoption"
                history_truncated = bool(raw_decision)
            records.append(
                SelectionRecord(
                    str(row["id"]),
                    str(row["label"])[:200],
                    statement,
                    float(row["confidence"]),
                    float(row["mass"]),
                    str(row["vector_16d"]),
                    str(row["legacy"]),
                    name,
                    state,
                    standing,
                    scope,
                    temporal,
                    tuple(dict.fromkeys(challenges))[:3],
                    tuple(dict.fromkeys(dissent))[:4],
                    decision_id,
                    history_truncated,
                    counter_trace,
                    str(row["kind"]),
                )
            )
        return SelectionSnapshot(tuple(records), truncated)
