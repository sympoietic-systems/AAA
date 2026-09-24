"""Message repository vector collaborator."""

from typing import Any

import numpy as np

from backend.storage.connection import with_connection
from backend.storage.models import Message
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_message


class MessageVectorRepository(BaseRepository):
    @with_connection
    def get_embeddings_by_speaker(
        self,
        speaker: str,
        limit: int = 5,
        conversation_id: str | None = None,
        exclude_message_id: int | None = None,
    ) -> list[np.ndarray]:
        conn = self._conn()
        exclude_clause = "AND id != ?" if exclude_message_id is not None else ""
        if conversation_id is not None:
            params = (
                (speaker, conversation_id)
                + ((exclude_message_id,) if exclude_message_id is not None else ())
                + (limit,)
            )
            rows = conn.execute(
                f"SELECT embedding, embedding_dim FROM conversation_log "
                f"WHERE speaker = ? AND conversation_id = ? {exclude_clause} ORDER BY id DESC LIMIT ?",
                params,
            ).fetchall()
        else:
            params = (speaker,) + ((exclude_message_id,) if exclude_message_id is not None else ()) + (limit,)
            rows = conn.execute(
                f"SELECT embedding, embedding_dim FROM conversation_log "
                f"WHERE speaker = ? {exclude_clause} ORDER BY id DESC LIMIT ?",
                params,
            ).fetchall()
        result: list[np.ndarray] = []
        for row in rows:
            blob = row["embedding"]
            dim = row["embedding_dim"]
            if blob and dim:
                vec = np.frombuffer(blob, dtype="float32")
                if len(vec) == dim:
                    result.append(vec)
        return result

    @with_connection
    def get_last_embedding_by_speaker(
        self, speaker: str, conversation_id: str | None = None, exclude_message_id: int | None = None
    ) -> np.ndarray | None:
        conn = self._conn()
        exclude_clause = "AND id != ?" if exclude_message_id is not None else ""
        if conversation_id is not None:
            params = (speaker, conversation_id) + ((exclude_message_id,) if exclude_message_id is not None else ())
            row = conn.execute(
                f"SELECT embedding, embedding_dim FROM conversation_log "
                f"WHERE speaker = ? AND conversation_id = ? {exclude_clause} ORDER BY id DESC LIMIT 1",
                params,
            ).fetchone()
        else:
            params = (speaker,) + ((exclude_message_id,) if exclude_message_id is not None else ())
            row = conn.execute(
                f"SELECT embedding, embedding_dim FROM conversation_log "
                f"WHERE speaker = ? {exclude_clause} ORDER BY id DESC LIMIT 1",
                params,
            ).fetchone()
        if row is None:
            return None
        blob = row["embedding"]
        dim = row["embedding_dim"]
        if not blob or not dim:
            return None
        vec = np.frombuffer(blob, dtype="float32")
        if len(vec) != dim:
            return None
        return vec

    @with_connection
    def get_recent_embeddings(
        self, limit: int = 10, conversation_id: str | None = None, exclude_message_id: int | None = None
    ) -> list[np.ndarray]:
        conn = self._conn()
        exclude_clause = "AND id != ?" if exclude_message_id is not None else ""
        if conversation_id is not None:
            params = (conversation_id,) + ((exclude_message_id,) if exclude_message_id is not None else ()) + (limit,)
            rows = conn.execute(
                f"SELECT embedding, embedding_dim FROM conversation_log "
                f"WHERE conversation_id = ? {exclude_clause} ORDER BY id DESC LIMIT ?",
                params,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT embedding, embedding_dim FROM conversation_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result: list[np.ndarray] = []
        for row in rows:
            blob = row["embedding"]
            dim = row["embedding_dim"]
            if blob and dim:
                vec = np.frombuffer(blob, dtype="float32")
                if len(vec) == dim:
                    result.append(vec)
        return result

    @with_connection
    def get_all_embeddings_except(
        self, exclude_conversation_id: str, limit: int = 500
    ) -> list[tuple[int, str, np.ndarray]]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT id, speaker, embedding, embedding_dim FROM conversation_log
               WHERE conversation_id != ? AND conversation_id != ''
               ORDER BY id DESC LIMIT ?""",
            (exclude_conversation_id, limit),
        ).fetchall()
        result: list[tuple[int, str, np.ndarray]] = []
        for row in rows:
            blob = row["embedding"]
            dim = row["embedding_dim"]
            if blob and dim:
                vec = np.frombuffer(blob, dtype="float32")
                if len(vec) == dim:
                    result.append((row["id"], row["speaker"], vec))
        return result

    @with_connection
    def get_embeddings_in_similarity_range(
        self,
        query_vec: np.ndarray,
        exclude_conversation_id: str,
        min_sim: float,
        max_sim: float,
        limit: int = 1000,
    ) -> list[tuple[float, int]]:
        candidates = self.get_all_embeddings_except(exclude_conversation_id, limit=limit)
        scored: list[tuple[float, int]] = []
        for msg_id, _speaker, vec in candidates:
            if len(vec) != len(query_vec):
                continue
            sim = float(np.dot(query_vec, vec))
            if min_sim <= sim <= max_sim:
                scored.append((sim, msg_id))
        return scored

    @with_connection
    def get_structural_signatures_except(
        self, exclude_conversation_id: str, limit: int = 500
    ) -> list[tuple[int, np.ndarray]]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT id, structural_signature FROM conversation_log
               WHERE conversation_id != ? AND conversation_id != '' AND structural_signature IS NOT NULL
               ORDER BY id DESC LIMIT ?""",
            (exclude_conversation_id, limit),
        ).fetchall()
        result: list[tuple[int, np.ndarray]] = []
        for row in rows:
            blob = row["structural_signature"]
            if blob:
                vec = np.frombuffer(blob, dtype="float32")
                result.append((row["id"], vec))
        return result

    @with_connection
    def get_embeddings_and_signatures_except(
        self, exclude_conversation_id: str, limit: int = 500
    ) -> list[tuple[int, np.ndarray, np.ndarray | None]]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT id, embedding, embedding_dim, structural_signature FROM conversation_log
               WHERE conversation_id != ? AND conversation_id != '' AND embedding IS NOT NULL
               ORDER BY id DESC LIMIT ?""",
            (exclude_conversation_id, limit),
        ).fetchall()
        result = []
        for row in rows:
            emb_blob = row["embedding"]
            dim = row["embedding_dim"]
            sig_blob = row["structural_signature"]

            emb_vec = None
            if emb_blob and dim:
                vec = np.frombuffer(emb_blob, dtype="float32")
                if len(vec) == dim:
                    emb_vec = vec

            sig_vec = None
            if sig_blob:
                sig_vec = np.frombuffer(sig_blob, dtype="float32")

            if emb_vec is not None:
                result.append((row["id"], emb_vec, sig_vec))
        return result

    @with_connection
    def get_parallel_messages_by_similarity(
        self,
        conversation_id: str,
        message_id: int,
        ancestor_ids: list[int],
        threshold: float,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        import numpy as np

        conn = self._conn()
        row = conn.execute(
            "SELECT embedding, embedding_dim FROM conversation_log WHERE id = ?",
            (message_id,),
        ).fetchone()
        if not row or not row["embedding"] or not row["embedding_dim"]:
            return []

        query_vec = np.frombuffer(row["embedding"], dtype="float32")
        query_dim = row["embedding_dim"]
        if len(query_vec) != query_dim:
            return []

        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm

        # Fetch recursive descendants of message_id to exclude them too (direct lineage check)
        descendant_rows = conn.execute(
            """
            WITH RECURSIVE descendants AS (
                SELECT id FROM conversation_log WHERE parent_message_id = ?
                UNION ALL
                SELECT cl.id FROM conversation_log cl
                JOIN descendants d ON cl.parent_message_id = d.id
            )
            SELECT id FROM descendants
            """,
            (message_id,),
        ).fetchall()
        descendant_ids = [r["id"] for r in descendant_rows]

        exclude_ids = list(set((ancestor_ids or []) + descendant_ids))
        exclude_placeholders = ",".join(["?"] * len(exclude_ids)) if exclude_ids else "NULL"

        query_str = f"""
            SELECT id, speaker, content, embedding, embedding_dim, timestamp
            FROM conversation_log
            WHERE conversation_id = ? AND id != ? AND id NOT IN ({exclude_placeholders})
              AND id NOT IN (
                  SELECT source_id FROM message_links WHERE target_id = ?
                  UNION
                  SELECT target_id FROM message_links WHERE source_id = ?
              )
        """
        params = [conversation_id, message_id] + exclude_ids + [message_id, message_id]
        rows = conn.execute(query_str, params).fetchall()

        results = []
        for r in rows:
            blob = r["embedding"]
            dim = r["embedding_dim"]
            if not blob or not dim:
                continue
            vec = np.frombuffer(blob, dtype="float32")
            if len(vec) != dim or len(vec) != len(query_vec):
                continue

            v_norm = np.linalg.norm(vec)
            if v_norm > 0:
                vec = vec / v_norm
            sim = float(np.dot(query_vec, vec))

            if sim >= threshold:
                results.append(
                    {
                        "message_id": r["id"],
                        "speaker": r["speaker"],
                        "content": r["content"],
                        "similarity": sim,
                        "timestamp": r["timestamp"],
                    }
                )

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    @with_connection
    def search_text(self, query_str: str, conversation_id: str | None = None) -> list[Message]:
        conn = self._conn()
        # Broad keyword search: split into tokens and OR-match each across
        # both the content and thinking columns.
        tokens = [t.strip() for t in query_str.split() if len(t.strip()) >= 2]
        if not tokens:
            tokens = [query_str.strip()]

        # Build: (content LIKE %t1% OR thinking LIKE %t1% OR content LIKE %t2% ...)
        clauses = []
        params = []
        for token in tokens:
            clauses.append("(content LIKE ? OR thinking LIKE ?)")
            params.extend([f"%{token}%", f"%{token}%"])

        where_body = " OR ".join(clauses)
        sql = f"SELECT * FROM conversation_log WHERE ({where_body})"
        if conversation_id:
            sql += " AND conversation_id = ?"
            params.append(conversation_id)
        sql += " ORDER BY id DESC"
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_message(r) for r in rows]

    @with_connection
    def get_embeddings_and_signatures_for_search(
        self, conversation_id: str | None = None
    ) -> list[tuple[int, str, str, str, str, bytes, bytes | None]]:
        conn = self._conn()
        if conversation_id:
            rows = conn.execute(
                """SELECT id, speaker, content, conversation_id, timestamp, embedding, structural_signature
                   FROM conversation_log
                   WHERE conversation_id = ? AND embedding IS NOT NULL""",
                (conversation_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, speaker, content, conversation_id, timestamp, embedding, structural_signature
                   FROM conversation_log
                   WHERE conversation_id != '' AND embedding IS NOT NULL""",
            ).fetchall()
        return [
            (
                r["id"],
                r["speaker"],
                r["content"],
                r["conversation_id"],
                r["timestamp"],
                r["embedding"],
                r["structural_signature"],
            )
            for r in rows
        ]

    @with_connection
    def get_glitch_salience_messages(
        self, conversation_id: str | None = None, limit: int = 50
    ) -> list[tuple[int, str, str, str, str, float, float, float]]:
        conn = self._conn()
        query = """
            SELECT cl.id, cl.speaker, cl.content, cl.conversation_id, cl.timestamp,
                   cm.surprise_index, cm.novelty, cm.deficit
            FROM conversation_log cl
            JOIN conversation_metrics cm ON cl.id = cm.message_id
            WHERE cm.surprise_index > 0.6 OR cm.novelty > 0.6 OR cm.deficit > 0.6
        """
        params: list[Any] = []
        if conversation_id:
            query += " AND cl.conversation_id = ?"
            params.append(conversation_id)
        query += " ORDER BY cl.id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [
            (
                r["id"],
                r["speaker"],
                r["content"],
                r["conversation_id"],
                r["timestamp"],
                r["surprise_index"],
                r["novelty"],
                r["deficit"],
            )
            for r in rows
        ]
