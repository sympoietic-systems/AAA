"""Atomic candidate deduplication and shared admission/trace persistence."""

import json
from typing import Any, cast

from backend.core.logging_config import mask_secrets
from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.cognitive.belief import BeliefRepository
from backend.utils.belief_candidate import statement_key


class AdmissionRepository(BaseRepository):
    @with_connection
    def claim(self, receipt: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        with self.atomic():
            conn = self._conn()
            row = conn.execute(
                "SELECT receipt FROM belief_admission WHERE event_key=?", (receipt["event_key"],)
            ).fetchone()
            if row:
                return False, cast(dict[str, Any], json.loads(row[0]))
            safe = mask_secrets(json.dumps(receipt, ensure_ascii=False))
            conn.execute(
                "INSERT INTO belief_admission (id,event_key,statement_key,status,receipt,created_at) VALUES (?,?,?,'assessing',?,?)",
                (receipt["id"], receipt["event_key"], receipt["statement_key"], safe, receipt["created_at"]),
            )
            self._trace(receipt, phase="received")
            return True, receipt

    @with_connection
    def comparisons(self, agent_id: str) -> list[dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT id,label,statement,'belief' kind,genesis_materials provenance FROM belief_nodes "
            "WHERE LOWER(agent_id)=LOWER(?) AND lifecycle_stage NOT IN ('collapsed','faded') "
            "UNION ALL SELECT id,COALESCE(suggested_label,'emergent-belief'),"
            "COALESCE(suggested_statement,provisional_statement),'proposal',source_trace "
            "FROM belief_proposals WHERE LOWER(agent_id)=LOWER(?) AND status IN ('pending','refined')",
            (agent_id, agent_id),
        ).fetchall()
        records = [dict(row) for row in rows]
        for record in records:
            record.update(scope="unknown", temporal_scope="unknown")
            if record["provenance"]:
                try:
                    provenance = json.loads(record["provenance"])
                except (json.JSONDecodeError, TypeError):
                    provenance = None
                if isinstance(provenance, list) and provenance and isinstance(provenance[0], dict):
                    record["scope"] = provenance[0].get("scope", "unknown")
                    record["temporal_scope"] = provenance[0].get("temporal_scope", "unknown")
        return records

    @with_connection
    def finish(self, receipt: dict[str, Any], confidence: float, signature: str) -> dict[str, Any]:
        """Recheck exact repeats under the writer lock, then commit proposal + receipt + trace together."""
        with self.atomic():
            conn = self._conn()
            row = conn.execute("SELECT status,receipt FROM belief_admission WHERE id=?", (receipt["id"],)).fetchone()
            if row is None:
                raise LookupError("Admission claim missing")
            if row[0] == "complete":
                return cast(dict[str, Any], json.loads(row[1]))
            latest = self.comparisons("symbia")
            equivalent = next(
                (
                    item
                    for item in latest
                    if statement_key(item["statement"]) == receipt["statement_key"]
                    and item["scope"] == receipt["scope"]
                    and item["temporal_scope"] == receipt["temporal_scope"]
                ),
                None,
            )
            current = {r["id"]: r for r in latest}
            changed = any(
                item["id"] not in current
                or statement_key(current[item["id"]]["statement"]) != statement_key(item["statement"])
                for item in receipt.get("comparisons", [])
            )
            source = receipt["source"]
            for field, hash_field in (("message_id", "message_sha256"), ("parent_message_id", "evidence_sha256")):
                row = conn.execute("SELECT content FROM conversation_log WHERE id=?", (source.get(field),)).fetchone()
                if row is not None:
                    import hashlib

                    changed |= hashlib.sha256(row[0].encode()).hexdigest() != source[hash_field]
                elif source.get(field) is not None:
                    changed = True
            if changed:
                receipt["evaluation"]["status"] = "stale"
                receipt["recommendation"] = "needs_review"
                receipt["reason"] = "Source or comparison changed during assessment; human review required."
            proposal_id = receipt["id"]
            if equivalent:
                receipt.update(
                    decision="repetition",
                    reason="Exact claim already exists; recorded occurrence without new proposal.",
                    target_id=equivalent["id"],
                    target_kind=equivalent["kind"],
                )
                proposal_id = equivalent["id"]
            else:
                repo = BeliefRepository(self._db_path)
                repo.create_proposal(
                    id=proposal_id,
                    agent_id="symbia",
                    provisional_statement=receipt["statement"],
                    source_trace=json.dumps([receipt["source"]]),
                    initial_signature=signature,
                    nucleation_mass=0.05 + confidence * 0.15,
                    confidence=confidence,
                    status="pending",
                    suppress_notification=True,
                )
                repo.update_proposal_suggestions(proposal_id, receipt["label"], receipt["statement"], None, "pending")
                if receipt["rationale"]:
                    repo.update_proposal_symbia_reflection(proposal_id, receipt["rationale"])
            receipt.update(proposal_id=proposal_id, status="complete")
            safe = mask_secrets(json.dumps(receipt, ensure_ascii=False))
            conn.execute(
                "UPDATE belief_admission SET proposal_id=?,status='complete',receipt=?,assessed_at=? WHERE id=?",
                (proposal_id, safe, receipt["assessed_at"], receipt["id"]),
            )
            self._trace(json.loads(safe), phase="assessed")
            return cast(dict[str, Any], json.loads(safe))

    def _trace(self, receipt: dict[str, Any], *, phase: str) -> None:
        source = receipt["source"]
        assessed = phase == "assessed"
        snippet = (
            f"Belief candidate {phase}: {receipt['label']}\n"
            f"Decision: {receipt['decision']}\nReason: {receipt['reason']}\n"
            f"Time: {receipt.get('assessed_at') or receipt['created_at']}\n"
            f"Consequence: {receipt['consequence'] or 'Not supplied'}\n"
            f"Scope: {receipt['scope'] or 'Unknown'}; time scope: {receipt['temporal_scope'] or 'Unknown'}\n"
            f"Source: {source.get('conversation_id')} / message {source.get('message_id')}\n"
            f"Policy: {receipt['policy_version']}; mode: shadow\n"
            f"Recommendation: {receipt.get('recommendation', 'not assessed')}\n"
            f"Evaluator: {receipt.get('evaluation', {}).get('status', 'not run')} / "
            f"{receipt.get('evaluation', {}).get('model', 'none')}\n"
            f"Context issues: {', '.join(receipt.get('context_issues', [])) or 'none'}\n"
            f"Compared with: {', '.join(item['label'] for item in receipt.get('comparisons', [])) or 'none'}\n"
            f"Receipt: {receipt['id']}"
        )
        # One shared payload: full detail is loaded lazily by the trace page.
        snippet += "\n\nAdmission receipt:\n" + json.dumps(receipt, ensure_ascii=False, indent=2)
        target_id = receipt.get("proposal_id") if assessed else None
        source_type = "belief" if target_id else "conversation"
        self._conn().execute(
            "INSERT INTO notifications (id,type,timestamp,snippet,conversation_id,message_id,source,source_type,source_id) "
            "VALUES (?,'trace',?,?,?,?,?,?,?)",
            (
                f"{receipt['id']}:{phase}",
                receipt.get("assessed_at") or receipt["created_at"],
                mask_secrets(snippet),
                source.get("conversation_id"),
                source.get("message_id"),
                "belief_admission",
                source_type,
                target_id or source.get("conversation_id"),
            ),
        )

    @with_connection
    def history(self, proposal_id: str) -> list[dict[str, Any]]:
        rows = (
            self._conn()
            .execute(
                "SELECT receipt FROM belief_admission WHERE proposal_id=? AND event_key NOT LIKE 'v2:%' ORDER BY created_at DESC LIMIT 50",
                (proposal_id,),
            )
            .fetchall()
        )
        from backend.storage.repositories.cognitive.belief_explicit import ExplicitBeliefRepository

        legacy = [json.loads(row[0]) for row in rows]
        projected = ExplicitBeliefRepository(self._db_path).history(proposal_id)
        return sorted(legacy + projected, key=lambda r: r["created_at"], reverse=True)[:50]
