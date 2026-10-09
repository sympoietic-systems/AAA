"""Bounded representations of external sources; ownership is not independent warrant."""

import hashlib
import json
from typing import Any

from backend.errors import SecurityViolation
from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class BeliefSourceRepository(BaseRepository):
    @with_connection
    def snapshot(self, agent: str, conversation: str, origin: str, source: str) -> dict[str, Any]:
        conn = self._conn()
        owner = conn.execute("SELECT agent_id FROM conversations WHERE id=?", (conversation,)).fetchone()
        if owner is None or str(owner[0]).lower() != agent:
            raise SecurityViolation("External belief source requires an owned conversation", entity="belief_intake")
        result: dict[str, Any] = {"text": "", "comment": "", "parents": [], "reason": "source_unavailable"}
        if origin == "document":
            row = conn.execute(
                "SELECT p.id,substr(p.chunk_text,1,50001),p.opacity,f.status,f.id "
                "FROM perception_sediment p JOIN perception_files f "
                "ON f.conversation_id=p.conversation_id AND f.file_name=p.file_name "
                "WHERE p.conversation_id=? AND p.file_name=? ORDER BY p.chunk_index,p.id LIMIT 1",
                (conversation, source),
            ).fetchone()
            if row and row[3] == "ready" and not row[2] and len(row[1]) <= 50000:
                result.update(
                    text=row[1],
                    parents=[
                        "document-container:" + hashlib.sha256(json.dumps([conversation, source]).encode()).hexdigest()
                    ],
                    reason="upstream_file_hash_unavailable",
                )
                result["chunk_id"] = row[0]
                result["source_id"] = "file:" + str(row[4])
        elif origin == "shared_note":
            row = conn.execute(
                "SELECT n.selected_text,n.comment,n.asset_id,m.content,m.speaker "
                "FROM notes n JOIN conversation_log m ON CAST(m.id AS TEXT)=n.asset_id "
                "AND m.conversation_id=n.conversation_id WHERE n.id=? AND n.conversation_id=? "
                "AND n.visibility='shared' AND n.asset_type IN ('message','conversation_message') "
                "AND length(n.selected_text)<=50000 AND length(n.comment)<=2000 AND length(m.content)<=50000",
                (source, conversation),
            ).fetchone()
            if row and row[0] and row[0] in row[3]:
                result.update(
                    text=row[0],
                    comment=row[1],
                    parents=["message:" + str(row[2])],
                    parent_hash=hashlib.sha256(row[3].encode()).hexdigest(),
                    parent_activity="internal" if row[4] == "apparatus" else "unknown",
                    reason="note_is_derived_from_message",
                )
        result["hash"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        return result

    @with_connection
    def bound_snapshot(self, agent: str, origin: str, source: str) -> dict[str, Any] | None:
        if origin == "document":
            row = (
                self._conn()
                .execute(
                    "SELECT f.conversation_id,f.file_name FROM perception_files f JOIN conversations c "
                    "ON c.id=f.conversation_id WHERE CAST(f.id AS TEXT)=? AND LOWER(c.agent_id)=?",
                    (source.removeprefix("file:"), agent),
                )
                .fetchone()
            )
        else:
            row = (
                self._conn()
                .execute(
                    "SELECT n.conversation_id,n.id FROM notes n JOIN conversations c ON c.id=n.conversation_id "
                    "WHERE n.id=? AND LOWER(c.agent_id)=?",
                    (source, agent),
                )
                .fetchone()
            )
        return self.snapshot(agent, str(row[0]), origin, str(row[1])) if row else None
