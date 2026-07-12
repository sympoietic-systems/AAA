import json

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_memory_node


class MemoryNodeRepository(BaseRepository):
    @with_connection
    def save_nodes(self, conversation_id: str, checkpoint_id: int, nodes: list[dict]) -> list[str]:
        conn = self._conn()
        ids = []
        for node in nodes:
            node_id = node.get("id", "")
            conn.execute(
                """INSERT OR REPLACE INTO memory_nodes
                   (id, conversation_id, checkpoint_id, node_type, intensity,
                    scar, glitch_potential, intra_active_text, surface_fragment,
                    agential_symmetry, diffractive_key, tendril_ids,
                    source_type, source_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    node.get("source_type", "conversation"),
                    node.get("source_id", node.get("research_task_id", "")),
                ),
            )
            ids.append(node_id)
        conn.commit()
        return ids

    @with_connection
    def get_nodes(self, conversation_id: str) -> list[dict]:
        """Return memory nodes, deduplicated by id across checkpoints.

        When the same node id exists under multiple checkpoints (each consolidation
        re-writes nodes with the same id), prefer the version with the highest
        revision_count, then highest intensity, then newest last_merged_at.
        """
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM memory_nodes WHERE conversation_id = ? "
            "ORDER BY revision_count DESC, intensity DESC, last_merged_at DESC",
            (conversation_id,),
        ).fetchall()

        seen: set[str] = set()
        result: list[dict] = []
        for r in rows:
            node = _row_to_memory_node(r)
            nid = node.get("id", "")
            if nid and nid not in seen:
                seen.add(nid)
                result.append(node)

        # Sort deduplicated nodes by created_at descending (latest at the top)
        result.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return result

    @with_connection
    def get_node(self, node_id: str) -> dict | None:
        conn = self._conn()
        row = conn.execute("SELECT * FROM memory_nodes WHERE id = ?", (node_id,)).fetchone()
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
    def delete_by_checkpoint(self, checkpoint_id: int) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM memory_nodes WHERE checkpoint_id = ?",
            (checkpoint_id,),
        )
        conn.commit()

    @with_connection
    def get_nodes_by_checkpoint(self, checkpoint_id: int) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM memory_nodes WHERE checkpoint_id = ? ORDER BY intensity DESC",
            (checkpoint_id,),
        ).fetchall()
        return [_row_to_memory_node(r) for r in rows]

    @with_connection
    def get_by_source(self, source_type: str, source_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM memory_nodes WHERE source_type = ? AND source_id = ? "
            "ORDER BY revision_count DESC, intensity DESC",
            (source_type, source_id),
        ).fetchall()
        seen: set[str] = set()
        result: list[dict] = []
        for r in rows:
            node = _row_to_memory_node(r)
            nid = node.get("id", "")
            if nid and nid not in seen:
                seen.add(nid)
                result.append(node)
        result.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return result

    @with_connection
    def get_diffractive_keys(self, conversation_id: str) -> list[str]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT diffractive_key FROM memory_nodes WHERE conversation_id = ? AND diffractive_key != ''",
            (conversation_id,),
        ).fetchall()
        return [r["diffractive_key"] for r in rows]

    @with_connection
    def search_memory_nodes_text(self, query_str: str) -> list[dict]:
        conn = self._conn()
        tokens = [t.strip() for t in query_str.split() if len(t.strip()) >= 2] or [query_str.strip()]
        clauses = ["(scar LIKE ? OR intra_active_text LIKE ? OR surface_fragment LIKE ?)" for _ in tokens]
        params = [v for t in tokens for v in (f"%{t}%", f"%{t}%", f"%{t}%")]
        sql = f"SELECT * FROM memory_nodes WHERE ({' OR '.join(clauses)}) ORDER BY created_at DESC"
        rows = conn.execute(sql, params).fetchall()
        seen = set()
        result = []
        for r in rows:
            node = _row_to_memory_node(r)
            nid = node.get("id", "")
            if nid and nid not in seen:
                seen.add(nid)
                result.append(node)
        return result
