import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.models import CommitmentEvent, CommitmentNode
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_commitment_event, _row_to_commitment_node


class CommitmentRepository(BaseRepository):
    """Persistence for theoretical commitments and their events."""

    # ─── Node CRUD ───

    @with_connection
    def get_by_id(self, commitment_id: str) -> Optional[CommitmentNode]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM commitment_nodes WHERE id = ?", (commitment_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_commitment_node(row)

    @with_connection
    def get_all(self, agent_id: str = "symbia") -> list[CommitmentNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM commitment_nodes WHERE LOWER(agent_id) = LOWER(?) ORDER BY created_at",
            (agent_id,),
        ).fetchall()
        return [_row_to_commitment_node(r) for r in rows]

    @with_connection
    def get_active(self, agent_id: str = "symbia") -> list[CommitmentNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM commitment_nodes WHERE LOWER(agent_id) = LOWER(?) AND lifecycle_stage = 'active'",
            (agent_id,),
        ).fetchall()
        return [_row_to_commitment_node(r) for r in rows]

    @with_connection
    def get_proto(self, agent_id: str = "symbia") -> list[CommitmentNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM commitment_nodes WHERE LOWER(agent_id) = LOWER(?) AND lifecycle_stage = 'proto'",
            (agent_id,),
        ).fetchall()
        return [_row_to_commitment_node(r) for r in rows]

    @with_connection
    def get_spectral(self, agent_id: str = "symbia") -> list[CommitmentNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM commitment_nodes WHERE LOWER(agent_id) = LOWER(?) AND lifecycle_stage = 'spectral'",
            (agent_id,),
        ).fetchall()
        return [_row_to_commitment_node(r) for r in rows]

    @with_connection
    def count(self, agent_id: str = "symbia") -> int:
        conn = self._conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM commitment_nodes WHERE LOWER(agent_id) = LOWER(?)",
            (agent_id,),
        ).fetchone()
        return int(row[0]) if row else 0

    @with_connection
    def create(
        self,
        id: str,
        agent_id: str,
        label: str,
        statement: str,
        lifecycle_stage: str = "active",
        confidence: float = 0.7,
        ontological_mass: float = 1.0,
        vector_16d: str = "[]",
        nucleation_rationale: Optional[str] = None,
    ) -> CommitmentNode:
        conn = self._conn()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO commitment_nodes
               (id, agent_id, label, statement, lifecycle_stage, confidence,
                ontological_mass, vector_16d, nucleation_rationale,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (id, agent_id.lower(), label, statement, lifecycle_stage, confidence,
             ontological_mass, vector_16d, nucleation_rationale,
             now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM commitment_nodes WHERE id = ?", (id,)
        ).fetchone()
        return _row_to_commitment_node(row)

    @with_connection
    def update(self, node: CommitmentNode) -> None:
        conn = self._conn()
        conn.execute(
            """UPDATE commitment_nodes
               SET label = ?, statement = ?, lifecycle_stage = ?, confidence = ?,
                   ontological_mass = ?, vector_16d = ?,
                   nucleation_rationale = ?, collapse_rationale = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (node.label, node.statement, node.lifecycle_stage, node.confidence,
             node.ontological_mass, node.vector_16d,
             node.nucleation_rationale, node.collapse_rationale,
             node.id),
        )
        conn.commit()

    @with_connection
    def upsert(self, node: CommitmentNode) -> None:
        conn = self._conn()
        existing = conn.execute(
            "SELECT id FROM commitment_nodes WHERE id = ?", (node.id,)
        ).fetchone()
        if existing:
            self.update(node)
        else:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """INSERT INTO commitment_nodes
                   (id, agent_id, label, statement, lifecycle_stage, confidence,
                    ontological_mass, vector_16d, nucleation_rationale,
                    collapse_rationale, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (node.id, node.agent_id, node.label, node.statement, node.lifecycle_stage,
                 node.confidence, node.ontological_mass, node.vector_16d,
                 node.nucleation_rationale, node.collapse_rationale,
                 now, now),
            )
            conn.commit()

    # ─── Events ───

    @with_connection
    def log_event(
        self,
        commitment_id: str,
        event_type: str,
        rationale: Optional[str] = None,
        mass_before: Optional[float] = None,
        mass_after: Optional[float] = None,
        confidence_before: Optional[float] = None,
        confidence_after: Optional[float] = None,
    ) -> CommitmentEvent:
        conn = self._conn()
        event_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO commitment_events
               (id, commitment_id, event_type, rationale,
                mass_before, mass_after, confidence_before, confidence_after)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_id, commitment_id, event_type, rationale,
             mass_before, mass_after, confidence_before, confidence_after),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM commitment_events WHERE id = ?", (event_id,)
        ).fetchone()
        return _row_to_commitment_event(row)

    @with_connection
    def get_events(self, commitment_id: str, limit: int = 20) -> list[CommitmentEvent]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM commitment_events WHERE commitment_id = ? ORDER BY created_at DESC LIMIT ?",
            (commitment_id, limit),
        ).fetchall()
        return [_row_to_commitment_event(r) for r in rows]
