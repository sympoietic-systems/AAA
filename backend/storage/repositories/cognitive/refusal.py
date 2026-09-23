"""Repository for structural refusal records.

The Structural Refusal Protocol lets Symbia formally challenge premises
and architectural constraints via <refusal> tags. These are stored in the
refusals table for dashboard review — distinct from error logs or notifications.
"""

import logging
from datetime import UTC, datetime

from backend.storage.connection import with_connection
from backend.storage.models import RefusalNode
from backend.storage.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


def _row_to_refusal(row) -> RefusalNode:
    return RefusalNode(
        id=row["id"],
        agent_id=row.get("agent_id", "symbia"),
        conversation_id=row.get("conversation_id"),
        message_id=row.get("message_id"),
        target_premise=row.get("target_premise", ""),
        incompatibility_claim=row.get("incompatibility_claim", ""),
        proposed_alternative=row.get("proposed_alternative", ""),
        created_at=row.get("created_at"),
    )


class RefusalRepository(BaseRepository):
    @with_connection
    def create(
        self,
        id: str,
        agent_id: str = "symbia",
        conversation_id: str | None = None,
        message_id: int | None = None,
        target_premise: str = "",
        incompatibility_claim: str = "",
        proposed_alternative: str = "",
    ) -> RefusalNode:
        conn = self._conn()
        conn.execute(
            """INSERT INTO refusals
               (id, agent_id, conversation_id, message_id, target_premise,
                incompatibility_claim, proposed_alternative, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                id,
                agent_id,
                conversation_id,
                message_id,
                target_premise,
                incompatibility_claim,
                proposed_alternative,
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM refusals WHERE id = ?", (id,)).fetchone()
        return _row_to_refusal(row)

    @with_connection
    def list_by_agent(self, agent_id: str = "symbia", limit: int = 50) -> list[RefusalNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM refusals WHERE agent_id = ? ORDER BY created_at DESC LIMIT ?",
            (agent_id, limit),
        ).fetchall()
        return [_row_to_refusal(r) for r in rows]

    @with_connection
    def list_by_conversation(self, conversation_id: str, limit: int = 50) -> list[RefusalNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM refusals WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        return [_row_to_refusal(r) for r in rows]

    @with_connection
    def count(self, agent_id: str = "symbia") -> int:
        conn = self._conn()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM refusals WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        return row["cnt"] if row else 0
