import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.models import BeliefEvent, BeliefNode, BeliefProposal, BeliefStatementVersion
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import (
    _row_to_belief_event,
    _row_to_belief_node,
    _row_to_belief_proposal,
    _row_to_belief_statement_version,
)


class BeliefRepository(BaseRepository):
    def validate_and_format_vector(self, vector_str: str) -> str:
        fallback = [0.0] * 16
        if not vector_str:
            return json.dumps(fallback)
        try:
            data = json.loads(vector_str)
        except Exception:
            return json.dumps(fallback)

        # Extract 16D array if it's in a dict format
        if isinstance(data, dict):
            if "v16d" in data and isinstance(data["v16d"], list):
                data = data["v16d"]
            else:
                return json.dumps(fallback)

        if not isinstance(data, list):
            return json.dumps(fallback)

        if len(data) == 0:
            return json.dumps(fallback)

        if len(data) != 16:
            if len(data) < 16:
                data = data + [0.0] * (16 - len(data))
            else:
                data = data[:16]

        # Ensure all elements are floats/numbers
        try:
            data = [float(x) for x in data]
        except (ValueError, TypeError):
            return json.dumps(fallback)

        return json.dumps(data)

    @with_connection
    def get_belief(self, agent_id: str, belief_id: str) -> Optional[BeliefNode]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM belief_nodes WHERE LOWER(agent_id) = LOWER(?) AND id = ?",
            (agent_id, belief_id),
        ).fetchone()
        if row is None:
            return None
        return _row_to_belief_node(row)

    @with_connection
    def list_beliefs(self, agent_id: str) -> list[BeliefNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_nodes WHERE LOWER(agent_id) = LOWER(?)",
            (agent_id,),
        ).fetchall()
        return [_row_to_belief_node(r) for r in rows]

    @with_connection
    def create_belief(
        self,
        id: str,
        agent_id: str,
        label: str,
        statement: str,
        origin: str,
        confidence: float,
        ontological_mass: float,
        somatic_anchor: str,
        vector_16d: str,
        lifecycle_stage: str = "crystallized",
        evolved_from_proposal: Optional[str] = None,
        genesis_materials: Optional[str] = None,
        version: int = 1,
    ) -> BeliefNode:
        validated_vector = self.validate_and_format_vector(vector_16d)
        conn = self._conn()
        conn.execute(
            """INSERT INTO belief_nodes
               (id, agent_id, label, statement, origin, confidence, ontological_mass, somatic_anchor, vector_16d, lifecycle_stage, evolved_from_proposal, genesis_materials, version, last_reinforced_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (id, agent_id.lower(), label, statement, origin, confidence, ontological_mass, somatic_anchor, validated_vector, lifecycle_stage, evolved_from_proposal, genesis_materials, version),
        )
        conn.commit()

        # Automatic persistence notification for new belief creation
        try:

            snippet = f"New belief '{label}' crystallized (initial confidence: {confidence:.2f}). Origin: {origin}"
            conn.execute(
                """INSERT INTO notifications (id, type, timestamp, snippet, source, read, dismissed)
                   VALUES (?, 'trace', ?, ?, ?, 0, 0)""",
                (str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), snippet, f"belief:{label}"),
            )
            conn.commit()
        except Exception:
            pass

        row = conn.execute(
            "SELECT * FROM belief_nodes WHERE id = ?", (id,)
        ).fetchone()
        return _row_to_belief_node(row)

    @with_connection
    def update_belief(
        self,
        belief_id: str,
        confidence: float,
        vector_16d: str,
        origin: str,
        lifecycle_stage: str | None = None,
        suppress_stage_notification: bool = False,
    ) -> None:
        validated_vector = self.validate_and_format_vector(vector_16d)
        conn = self._conn()
        
        # Check for stage transition
        if lifecycle_stage is not None and not suppress_stage_notification:
            try:
                row = conn.execute("SELECT label, lifecycle_stage FROM belief_nodes WHERE id = ?", (belief_id,)).fetchone()
                if row and row["lifecycle_stage"] != lifecycle_stage:
                    old_stage = row["lifecycle_stage"]
                    label = row["label"]
                    snippet = f"Belief '{label}' transitioned stage: {old_stage} \u2192 {lifecycle_stage}."

                    conn.execute(
                        """INSERT INTO notifications (id, type, timestamp, snippet, source, read, dismissed)
                           VALUES (?, 'trace', ?, ?, ?, 0, 0)""",
                        (str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), snippet, f"belief:{label}"),
                    )
            except Exception:
                pass

        if lifecycle_stage is not None:
            conn.execute(
                """UPDATE belief_nodes
                   SET confidence = ?, vector_16d = ?, origin = ?, lifecycle_stage = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (confidence, validated_vector, origin, lifecycle_stage, belief_id),
            )
        else:
            conn.execute(
                """UPDATE belief_nodes
                   SET confidence = ?, vector_16d = ?, origin = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (confidence, validated_vector, origin, belief_id),
            )
        conn.commit()

    @with_connection
    def update_belief_mass(self, belief_id: str, ontological_mass: float) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE belief_nodes SET ontological_mass = ?, last_reinforced_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (ontological_mass, belief_id),
        )
        conn.commit()

    @with_connection
    def update_belief_stage(self, belief_id: str, lifecycle_stage: str) -> None:
        conn = self._conn()
        try:
            row = conn.execute("SELECT label, lifecycle_stage FROM belief_nodes WHERE id = ?", (belief_id,)).fetchone()
            if row and row["lifecycle_stage"] != lifecycle_stage:
                old_stage = row["lifecycle_stage"]
                label = row["label"]
                snippet = f"Belief '{label}' transitioned stage: {old_stage} \u2192 {lifecycle_stage}."

                conn.execute(
                    """INSERT INTO notifications (id, type, timestamp, snippet, source, read, dismissed)
                       VALUES (?, 'trace', ?, ?, ?, 0, 0)""",
                    (str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), snippet, f"belief:{label}"),
                )
        except Exception:
            pass

        conn.execute(
            "UPDATE belief_nodes SET lifecycle_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (lifecycle_stage, belief_id),
        )
        conn.commit()

    @with_connection
    def create_notification(
        self,
        snippet: str,
        notif_type: str = "trace",
        source: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
    ) -> None:
        """Create a notification entry in the notifications table."""
        try:

            conn = self._conn()
            conn.execute(
                """INSERT INTO notifications (id, type, timestamp, snippet, source, source_type, source_id, read, dismissed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)""",
                (str(uuid.uuid4()), notif_type, datetime.now(timezone.utc).isoformat(), snippet, source, source_type, source_id),
            )
            conn.commit()
        except Exception:
            logging.getLogger(__name__).warning(
                "Failed to create notification: type=%s source=%s", notif_type, source, exc_info=True,
            )

    @with_connection
    def fold_ghost_into(self, ghost_id: str, keeper_id: str) -> None:
        """13C: Mark a ghost belief as folded and record which keeper absorbed it."""
        conn = self._conn()
        conn.execute(
            "UPDATE belief_nodes SET lifecycle_stage = 'folded', merged_into = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (keeper_id, ghost_id),
        )
        conn.commit()
        logger = logging.getLogger(__name__)
        logger.info("Ghost '%s' folded into '%s'", ghost_id, keeper_id)

    @with_connection
    def list_active_beliefs(self, agent_id: str) -> list[BeliefNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_nodes WHERE LOWER(agent_id) = LOWER(?) AND lifecycle_stage IN ('crystallized', 'senescence')",
            (agent_id,),
        ).fetchall()
        return [_row_to_belief_node(r) for r in rows]

    @with_connection
    def list_proto_beliefs(self, agent_id: str) -> list[BeliefNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_nodes WHERE LOWER(agent_id) = LOWER(?) AND lifecycle_stage IN ('nucleation', 'accretion')",
            (agent_id,),
        ).fetchall()
        return [_row_to_belief_node(r) for r in rows]

    @with_connection
    def list_ghosts(self, agent_id: str) -> list[BeliefNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_nodes WHERE LOWER(agent_id) = LOWER(?) AND lifecycle_stage = 'collapsed' AND (merged_into IS NULL OR merged_into = '')",
            (agent_id,),
        ).fetchall()
        return [_row_to_belief_node(r) for r in rows]

    @with_connection
    def get_belief_last_reinforced(self, belief_id: str) -> str | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT last_reinforced_at FROM belief_nodes WHERE id = ?", (belief_id,)
        ).fetchone()
        if row:
            return row["last_reinforced_at"]
        return None

    @with_connection
    def update_belief_last_dreamed(self, belief_id: str, timestamp: Optional[str] = None) -> None:
        conn = self._conn()
        if timestamp:
            conn.execute(
                "UPDATE belief_nodes SET last_dreamed_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (timestamp, belief_id),
            )
        else:
            conn.execute(
                "UPDATE belief_nodes SET last_dreamed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (belief_id,),
            )
        conn.commit()

    @with_connection
    def insert_belief_event(
        self,
        event_id: str,
        belief_id: str,
        source_type: str,
        source_id: Optional[str],
        alignment: Optional[float],
        perturbation: Optional[float],
        event_type: str,
        impact: float,
        rationale: Optional[str],
        suppress_notification: bool = False,
    ) -> None:
        try:
            conn = self._conn()
            conn.execute(
                """INSERT INTO belief_events
                   (id, belief_id, source_type, source_id, alignment_coefficient, perturbation_magnitude, event_type, impact_score, rationale)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, belief_id, source_type, source_id, alignment, perturbation, event_type, impact, rationale),
            )
            conn.commit()

            if not suppress_notification:
                # Automatic notification for belief dynamics events (metabolism updates)
                try:
                    belief_row = conn.execute("SELECT label FROM belief_nodes WHERE id = ?", (belief_id,)).fetchone()
                    belief_label = belief_row["label"] if belief_row else "unknown"
                    
                    snippet = f"Belief '{belief_label}' {event_type} (impact: {impact or 0.0:.2f}). {rationale or ''}"
                    snippet = snippet.strip()

                    conn.execute(
                        """INSERT INTO notifications (id, type, timestamp, snippet, source, source_type, source_id, read, dismissed)
                           VALUES (?, 'trace', ?, ?, ?, ?, ?, 0, 0)""",
                        (str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), snippet, f"belief:{belief_label}", source_type, belief_id),
                    )
                    conn.commit()
                except Exception:
                    logging.getLogger(__name__).warning(
                        "Failed to create notification for belief event %s on belief '%s'",
                        event_type, belief_id, exc_info=True,
                    )

        except Exception:
            logging.getLogger(__name__).warning(
                "Failed to insert belief event %s for belief '%s'",
                event_type, belief_id, exc_info=True,
            )

    @with_connection
    def get_events_for_belief(self, belief_id: str, limit: int = 100) -> list[BeliefEvent]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_events WHERE belief_id = ? ORDER BY timestamp DESC LIMIT ?",
            (belief_id, limit),
        ).fetchall()
        return [_row_to_belief_event(r) for r in rows]

    @with_connection
    def update_conversation_somatic_state(
        self,
        conversation_id: str,
        somatic_reservoir_ad: float,
        matrix_warping: float,
        immunological_directive_active: int,
    ) -> None:
        conn = self._conn()
        conn.execute(
            """UPDATE conversations
               SET somatic_reservoir_ad = ?, matrix_warping = ?, immunological_directive_active = ?
               WHERE id = ?""",
            (somatic_reservoir_ad, matrix_warping, immunological_directive_active, conversation_id),
        )
        conn.commit()

    @with_connection
    def get_conversation_somatic_state(self, conversation_id: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT somatic_reservoir_ad, matrix_warping, immunological_directive_active FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "somatic_reservoir_ad": row["somatic_reservoir_ad"] or 0.0,
            "matrix_warping": row["matrix_warping"] or 0.0,
            "immunological_directive_active": row["immunological_directive_active"] or 0,
        }

    @with_connection
    def upsert_tension(self, belief_a_id: str, belief_b_id: str, cosine_similarity: float, tension_magnitude: float) -> None:
        conn = self._conn()
        a, b = sorted([belief_a_id, belief_b_id])
        conn.execute(
            """INSERT INTO belief_tensions (belief_a_id, belief_b_id, cosine_similarity, tension_magnitude, last_updated)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(belief_a_id, belief_b_id) DO UPDATE SET
               cosine_similarity = excluded.cosine_similarity,
               tension_magnitude = excluded.tension_magnitude,
               last_updated = CURRENT_TIMESTAMP""",
            (a, b, cosine_similarity, tension_magnitude),
        )
        conn.commit()

    @with_connection
    def get_tensions_for_belief(self, belief_id: str) -> list:
        conn = self._conn()
        rows = conn.execute(
            """SELECT * FROM belief_tensions WHERE belief_a_id = ? OR belief_b_id = ?
               ORDER BY tension_magnitude DESC""",
            (belief_id, belief_id),
        ).fetchall()
        return [
            {
                "other_id": row["belief_a_id"] if row["belief_b_id"] == belief_id else row["belief_b_id"],
                "cosine_similarity": row["cosine_similarity"],
                "tension_magnitude": row["tension_magnitude"],
                "last_updated": row["last_updated"],
            }
            for row in rows
        ]

    @with_connection
    def get_active_tension_pairs(self, min_magnitude: float = 0.01) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_tensions WHERE tension_magnitude >= ? ORDER BY tension_magnitude DESC",
            (min_magnitude,),
        ).fetchall()
        return [
            {
                "belief_a_id": row["belief_a_id"],
                "belief_b_id": row["belief_b_id"],
                "cosine_similarity": row["cosine_similarity"],
                "tension_magnitude": row["tension_magnitude"],
                "last_updated": row["last_updated"],
            }
            for row in rows
        ]

    @with_connection
    def get_total_system_tension(self) -> float:
        conn = self._conn()
        row = conn.execute("SELECT SUM(tension_magnitude) FROM belief_tensions").fetchone()
        return float(row[0]) if row[0] is not None else 0.0

    @with_connection
    def remove_tension(self, belief_a_id: str, belief_b_id: str) -> None:
        conn = self._conn()
        a, b = sorted([belief_a_id, belief_b_id])
        conn.execute("DELETE FROM belief_tensions WHERE belief_a_id = ? AND belief_b_id = ?", (a, b))
        conn.commit()

    @with_connection
    def delete_belief_by_label(self, label: str) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM belief_nodes WHERE label = ?", (label,))
        conn.commit()

    @with_connection
    def update_belief_details(
        self,
        belief_id: str,
        label: str,
        statement: str,
        confidence: float,
        ontological_mass: float,
        lifecycle_stage: str,
        vector_16d: str,
        version: int,
    ) -> None:
        validated_vector = self.validate_and_format_vector(vector_16d)
        conn = self._conn()
        
        # Check for stage transition
        try:
            row = conn.execute("SELECT label, lifecycle_stage FROM belief_nodes WHERE id = ?", (belief_id,)).fetchone()
            if row and row["lifecycle_stage"] != lifecycle_stage:
                old_stage = row["lifecycle_stage"]
                snippet = f"Belief '{row['label']}' transitioned stage: {old_stage} \u2192 {lifecycle_stage}."

                conn.execute(
                    """INSERT INTO notifications (id, type, timestamp, snippet, source, read, dismissed)
                       VALUES (?, 'trace', ?, ?, ?, 0, 0)""",
                    (str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), snippet, f"belief:{row['label']}"),
                )
        except Exception:
            pass

        conn.execute(
            """UPDATE belief_nodes
               SET label = ?, statement = ?, confidence = ?, ontological_mass = ?, lifecycle_stage = ?, vector_16d = ?, version = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (label, statement, confidence, ontological_mass, lifecycle_stage, validated_vector, version, belief_id),
        )
        conn.commit()

    @with_connection
    def delete_belief(self, belief_id: str) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM belief_statement_versions WHERE belief_id = ?", (belief_id,))
        conn.execute("DELETE FROM belief_events WHERE belief_id = ?", (belief_id,))
        conn.execute("DELETE FROM belief_nodes WHERE id = ?", (belief_id,))
        conn.commit()

    @with_connection
    def update_belief_statement(self, belief_id: str, statement: str, vector_16d: str, version: int) -> None:
        validated_vector = self.validate_and_format_vector(vector_16d)
        conn = self._conn()
        conn.execute(
            """UPDATE belief_nodes
               SET statement = ?, vector_16d = ?, version = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (statement, validated_vector, version, belief_id),
        )
        conn.commit()

    @with_connection
    def create_proposal(
        self,
        id: str,
        agent_id: str,
        provisional_statement: str,
        source_trace: str,
        initial_signature: str,
        nucleation_mass: float = 0.1,
        confidence: float = 0.15,
        status: str = "pending",
        potential_merge_target: Optional[str] = None,
    ) -> BeliefProposal:
        validated_vector = self.validate_and_format_vector(initial_signature)
        conn = self._conn()
        conn.execute(
            """INSERT INTO belief_proposals
               (id, agent_id, provisional_statement, source_trace, initial_signature, nucleation_mass, confidence, status, potential_merge_target, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            (id, agent_id.lower(), provisional_statement, source_trace, validated_vector, nucleation_mass, confidence, status, potential_merge_target),
        )
        
        # Automatic notification insertion

        snippet = f"A new belief proposal has emerged in the workshop ('{provisional_statement}')"
        conn.execute(
            """INSERT INTO notifications (id, type, timestamp, snippet, source, read, dismissed)
               VALUES (?, 'trace', ?, ?, 'belief_workshop', 0, 0)""",
            (str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), snippet),
        )
        
        conn.commit()
        row = conn.execute("SELECT * FROM belief_proposals WHERE id = ?", (id,)).fetchone()
        return _row_to_belief_proposal(row)

    @with_connection
    def get_proposal(self, proposal_id: str) -> Optional[BeliefProposal]:
        conn = self._conn()
        row = conn.execute("SELECT * FROM belief_proposals WHERE id = ?", (proposal_id,)).fetchone()
        if row is None:
            return None
        return _row_to_belief_proposal(row)

    @with_connection
    def list_proposals(self, agent_id: str) -> list[BeliefProposal]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_proposals WHERE LOWER(agent_id) = LOWER(?) ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
        return [_row_to_belief_proposal(r) for r in rows]

    @with_connection
    def list_pending_proposals(self, agent_id: str) -> list[BeliefProposal]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_proposals WHERE LOWER(agent_id) = LOWER(?) AND status IN ('pending', 'refined') ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
        return [_row_to_belief_proposal(r) for r in rows]

    @with_connection
    def update_proposal_status(self, proposal_id: str, status: str, rejection_rationale: Optional[str] = None) -> None:
        conn = self._conn()
        if rejection_rationale is not None:
            conn.execute(
                "UPDATE belief_proposals SET status = ?, rejection_rationale = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, rejection_rationale, proposal_id),
            )
        else:
            conn.execute(
                "UPDATE belief_proposals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, proposal_id),
            )
        conn.commit()

    @with_connection
    def update_proposal_suggestions(self, proposal_id: str, suggested_label: str, suggested_statement: str, potential_merge_target: Optional[str] = None, status: str = "refined") -> None:
        conn = self._conn()
        conn.execute(
            """UPDATE belief_proposals
               SET suggested_label = ?, suggested_statement = ?, potential_merge_target = ?, status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (suggested_label, suggested_statement, potential_merge_target, status, proposal_id),
        )
        conn.commit()

    @with_connection
    def update_proposal_symbia_reflection(self, proposal_id: str, symbia_reflection: str, symbia_friction_rationale: Optional[str] = None) -> None:
        conn = self._conn()
        conn.execute(
            """UPDATE belief_proposals
               SET symbia_reflection = ?, symbia_friction_rationale = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (symbia_reflection, symbia_friction_rationale, proposal_id),
        )
        conn.commit()

    @with_connection
    def create_statement_version(
        self,
        id: str,
        belief_id: str,
        version: int,
        statement: str,
        vector_16d: str,
        change_reason: Optional[str] = None,
    ) -> BeliefStatementVersion:
        validated_vector = self.validate_and_format_vector(vector_16d)
        conn = self._conn()
        conn.execute(
            """INSERT INTO belief_statement_versions
               (id, belief_id, version, statement, vector_16d, change_reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (id, belief_id, version, statement, validated_vector, change_reason),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM belief_statement_versions WHERE id = ?", (id,)).fetchone()
        return _row_to_belief_statement_version(row)

    @with_connection
    def list_statement_versions(self, belief_id: str) -> list[BeliefStatementVersion]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_statement_versions WHERE belief_id = ? ORDER BY version ASC",
            (belief_id,),
        ).fetchall()
        return [_row_to_belief_statement_version(r) for r in rows]

    @with_connection
    def get_statement_version(self, belief_id: str, version: int) -> Optional[BeliefStatementVersion]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM belief_statement_versions WHERE belief_id = ? AND version = ?",
            (belief_id, version),
        ).fetchone()
        if row is None:
            return None
        return _row_to_belief_statement_version(row)
