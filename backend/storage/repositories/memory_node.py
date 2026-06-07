import json

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_memory_node


class MemoryNodeRepository(BaseRepository):
    @with_connection
    def save_nodes(
        self, conversation_id: str, checkpoint_id: int, nodes: list[dict]
    ) -> list[str]:
        conn = self._conn()
        ids = []
        for node in nodes:
            node_id = node.get("id", "")
            conn.execute(
                """INSERT OR REPLACE INTO memory_nodes
                   (id, conversation_id, checkpoint_id, node_type, intensity,
                    scar, glitch_potential, intra_active_text, surface_fragment,
                    agential_symmetry, diffractive_key, tendril_ids)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node_id,
                    conversation_id,
                    checkpoint_id,
                    node.get("type", "concept"),
                    node.get("intensity", 0.5),
                    node.get("scar", ""),
                    node.get("glitch_potential", 0.0),
                    node.get("intra_active_text", ""),
                    node.get("surface_fragment", ""),
                    node.get("agential_symmetry", "negotiated"),
                    node.get("diffractive_key", ""),
                    json.dumps(node.get("tendrils", [])),
                ),
            )
            ids.append(node_id)
        conn.commit()
        return ids

    @with_connection
    def get_nodes(self, conversation_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM memory_nodes WHERE conversation_id = ? ORDER BY intensity DESC",
            (conversation_id,),
        ).fetchall()
        return [_row_to_memory_node(r) for r in rows]

    @with_connection
    def get_node(self, node_id: str) -> dict | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM memory_nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_memory_node(row)

    @with_connection
    def delete_by_conversation(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM memory_nodes WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.commit()

    @with_connection
    def get_diffractive_keys(self, conversation_id: str) -> list[str]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT diffractive_key FROM memory_nodes WHERE conversation_id = ? AND diffractive_key != ''",
            (conversation_id,),
        ).fetchall()
        return [r["diffractive_key"] for r in rows]
