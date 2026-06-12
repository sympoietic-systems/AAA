from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.models import BeliefEvent, BeliefNode
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_belief_event, _row_to_belief_node


class BeliefRepository(BaseRepository):
    @with_connection
    def get_belief(self, agent_id: str, belief_id: str) -> Optional[BeliefNode]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM belief_nodes WHERE agent_id = ? AND id = ?",
            (agent_id, belief_id),
        ).fetchone()
        if row is None:
            return None
        return _row_to_belief_node(row)

    @with_connection
    def list_beliefs(self, agent_id: str) -> list[BeliefNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_nodes WHERE agent_id = ?",
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
    ) -> BeliefNode:
        conn = self._conn()
        conn.execute(
            """INSERT INTO belief_nodes
               (id, agent_id, label, statement, origin, confidence, ontological_mass, somatic_anchor, vector_16d, lifecycle_stage, last_reinforced_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (id, agent_id, label, statement, origin, confidence, ontological_mass, somatic_anchor, vector_16d, lifecycle_stage),
        )
        conn.commit()
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
    ) -> None:
        conn = self._conn()
        if lifecycle_stage is not None:
            conn.execute(
                """UPDATE belief_nodes
                   SET confidence = ?, vector_16d = ?, origin = ?, lifecycle_stage = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (confidence, vector_16d, origin, lifecycle_stage, belief_id),
            )
        else:
            conn.execute(
                """UPDATE belief_nodes
                   SET confidence = ?, vector_16d = ?, origin = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (confidence, vector_16d, origin, belief_id),
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
        conn.execute(
            "UPDATE belief_nodes SET lifecycle_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (lifecycle_stage, belief_id),
        )
        conn.commit()

    @with_connection
    def list_active_beliefs(self, agent_id: str) -> list[BeliefNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_nodes WHERE agent_id = ? AND lifecycle_stage IN ('crystallized', 'senescence')",
            (agent_id,),
        ).fetchall()
        return [_row_to_belief_node(r) for r in rows]

    @with_connection
    def list_proto_beliefs(self, agent_id: str) -> list[BeliefNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_nodes WHERE agent_id = ? AND lifecycle_stage IN ('nucleation', 'accretion')",
            (agent_id,),
        ).fetchall()
        return [_row_to_belief_node(r) for r in rows]

    @with_connection
    def list_ghosts(self, agent_id: str) -> list[BeliefNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM belief_nodes WHERE agent_id = ? AND lifecycle_stage = 'collapsed'",
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
        except Exception:
            pass

    @with_connection
    def get_events_for_belief(self, belief_id: str, limit: int = 20) -> list[BeliefEvent]:
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
