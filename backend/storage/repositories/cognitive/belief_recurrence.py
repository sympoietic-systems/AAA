"""Bounded source ancestry for presentation only; no mutation or claim identity."""

import hashlib
from typing import Any

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class BeliefRecurrenceRepository(BaseRepository):
    @with_connection
    def sources(self, agent: str, entries: list[dict[str, Any]]) -> dict[str, frozenset[int]]:
        entries = entries[:50]
        if not entries:
            return {}
        conn = self._conn()
        valid = {}
        for entry in entries:
            source = entry["source"]
            row = conn.execute(
                "SELECT m.content,c.agent_id,s.state,s.statement_hash FROM conversation_log m "
                "JOIN conversations c ON c.id=m.conversation_id JOIN belief_review_state s "
                "ON s.agent_id=LOWER(c.agent_id) AND s.record_id=? "
                "WHERE m.id=? AND m.conversation_id=? AND LOWER(c.agent_id)=?",
                (entry["id"], source["message_id"], source["conversation_id"], agent.lower()),
            ).fetchone()
            if (
                row
                and row["state"] == "awaiting_context"
                and (
                    hashlib.sha256(str(row["content"]).encode()).hexdigest() == source["message_sha256"]
                    and hashlib.sha256(entry["statement"].encode()).hexdigest() == row["statement_hash"]
                )
            ):
                valid[entry["id"]] = source
        paths = {}
        for identity, source in valid.items():
            rows = conn.execute(
                "WITH RECURSIVE ancestry(id,parent_message_id,depth,seen) AS ("
                "SELECT id,parent_message_id,0,','||id||',' FROM conversation_log WHERE id=? AND conversation_id=? "
                "UNION ALL SELECT m.id,m.parent_message_id,a.depth+1,a.seen||m.id||',' "
                "FROM ancestry a JOIN conversation_log m ON m.id=a.parent_message_id "
                "WHERE m.conversation_id=? AND a.depth<127 AND instr(a.seen,','||m.id||',')=0) "
                "SELECT id,parent_message_id,depth FROM ancestry",
                (source["message_id"], source["conversation_id"], source["conversation_id"]),
            ).fetchall()
            if rows and rows[-1]["parent_message_id"] is None:
                paths[identity] = frozenset(int(row["id"]) for row in rows)
        return paths
