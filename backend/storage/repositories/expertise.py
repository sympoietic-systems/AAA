import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.models import ExpertiseNode
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_expertise_node


class ExpertiseRepository(BaseRepository):
    """Persistence for domain expertise accretion state."""

    @with_connection
    def get_all(self, agent_id: str = "symbia") -> list[ExpertiseNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM expertise_nodes WHERE agent_id = ? ORDER BY ontological_mass DESC",
            (agent_id,),
        ).fetchall()
        return [_row_to_expertise_node(r) for r in rows]

    @with_connection
    def get_active(self, agent_id: str = "symbia") -> list[ExpertiseNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM expertise_nodes WHERE agent_id = ? AND lifecycle_stage = 'active'",
            (agent_id,),
        ).fetchall()
        return [_row_to_expertise_node(r) for r in rows]

    @with_connection
    def get_by_domain(self, domain: str, agent_id: str = "symbia") -> Optional[ExpertiseNode]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM expertise_nodes WHERE agent_id = ? AND domain = ?",
            (agent_id, domain),
        ).fetchone()
        if row is None:
            return None
        return _row_to_expertise_node(row)

    @with_connection
    def get_dormant(self, agent_id: str = "symbia") -> list[ExpertiseNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM expertise_nodes WHERE agent_id = ? AND lifecycle_stage = 'dormant'",
            (agent_id,),
        ).fetchall()
        return [_row_to_expertise_node(r) for r in rows]

    @with_connection
    def count(self, agent_id: str = "symbia") -> int:
        conn = self._conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM expertise_nodes WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        return int(row[0]) if row else 0

    @with_connection
    def create(
        self,
        id: str,
        agent_id: str,
        domain: str,
        lifecycle_stage: str = "proto",
        ontological_mass: float = 0.05,
        level_label: str = "nascent",
        vector_16d: str = "[]",
        signal_count: int = 0,
        last_signal_at: Optional[str] = None,
        crystallization_rationale: Optional[str] = None,
    ) -> ExpertiseNode:
        conn = self._conn()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO expertise_nodes
               (id, agent_id, domain, lifecycle_stage, ontological_mass, level_label,
                vector_16d, signal_count, last_signal_at, crystallization_rationale,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (id, agent_id, domain, lifecycle_stage, ontological_mass, level_label,
             vector_16d, signal_count, last_signal_at, crystallization_rationale,
             now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM expertise_nodes WHERE id = ?", (id,)
        ).fetchone()
        return _row_to_expertise_node(row)

    @with_connection
    def update(self, node: ExpertiseNode) -> None:
        conn = self._conn()
        conn.execute(
            """UPDATE expertise_nodes
               SET domain = ?, lifecycle_stage = ?, ontological_mass = ?,
                   level_label = ?, vector_16d = ?, signal_count = ?,
                   last_signal_at = ?, crystallization_rationale = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (node.domain, node.lifecycle_stage, node.ontological_mass,
             node.level_label, node.vector_16d, node.signal_count,
             node.last_signal_at, node.crystallization_rationale,
             node.id),
        )
        conn.commit()

    @with_connection
    def upsert(self, node: ExpertiseNode) -> None:
        conn = self._conn()
        existing = conn.execute(
            "SELECT id FROM expertise_nodes WHERE id = ?", (node.id,)
        ).fetchone()
        if existing:
            self.update(node)
        else:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """INSERT INTO expertise_nodes
                   (id, agent_id, domain, lifecycle_stage, ontological_mass, level_label,
                    vector_16d, signal_count, last_signal_at, crystallization_rationale,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (node.id, node.agent_id, node.domain, node.lifecycle_stage,
                 node.ontological_mass, node.level_label, node.vector_16d,
                 node.signal_count, node.last_signal_at, node.crystallization_rationale,
                 now, now),
            )
            conn.commit()
