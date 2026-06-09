from datetime import datetime
from typing import Optional

import numpy as np

from backend.storage.connection import with_connection
from backend.storage.models import Message
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_message


class MessageRepository(BaseRepository):
    @with_connection
    def insert(
        self,
        speaker: str,
        content: str,
        embedding: bytes,
        embedding_model: str,
        embedding_dim: int,
        thinking: Optional[str] = None,
        agent_id: str = "",
        conversation_id: str = "",
        content_tokens: int = 0,
        thinking_tokens: int | None = None,
        model_used: Optional[str] = None,
        provider_used: Optional[str] = None,
        context_sent: Optional[str] = None,
        structural_signature: bytes = b"",
        structural_justification: Optional[str] = None,
    ) -> Message:
        conn = self._conn()
        conn.execute(
            """INSERT INTO conversation_log
               (agent_id, speaker, content, thinking, context_sent, embedding, embedding_model, embedding_dim, conversation_id, content_tokens, thinking_tokens, model_used, provider_used, structural_signature, structural_justification)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, speaker, content, thinking, context_sent, embedding, embedding_model, embedding_dim, conversation_id, content_tokens, thinking_tokens, model_used, provider_used, structural_signature, structural_justification),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversation_log WHERE id = last_insert_rowid()"
        ).fetchone()
        return _row_to_message(row)

    @with_connection
    def get_recent(self, limit: int = 50, conversation_id: str | None = None) -> list[Message]:
        conn = self._conn()
        if conversation_id is not None:
            rows = conn.execute(
                "SELECT * FROM conversation_log WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversation_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_message(r) for r in reversed(rows)]

    @with_connection
    def get_messages_since(self, conversation_id: str, last_message_count: int) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM conversation_log WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        messages = [_row_to_message(r) for r in rows]
        return messages[last_message_count:]

    @with_connection
    def get_last_message_timestamp(self, conversation_id: Optional[str] = None) -> Optional[datetime]:
        conn = self._conn()
        if conversation_id:
            row = conn.execute(
                "SELECT timestamp FROM conversation_log WHERE conversation_id = ? ORDER BY id DESC LIMIT 1",
                (conversation_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT timestamp FROM conversation_log ORDER BY id DESC LIMIT 1",
            ).fetchone()
        if row is None or not row["timestamp"]:
            return None
        try:
            return datetime.fromisoformat(row["timestamp"])
        except Exception:
            return None

    @with_connection
    def get_by_id(self, message_id: int) -> Optional[Message]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM conversation_log WHERE id = ?", (message_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_message(row)

    @with_connection
    def update_signature(self, message_id: int, structural_signature: bytes) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET structural_signature = ? WHERE id = ?",
            (structural_signature, message_id),
        )
        conn.commit()

    @with_connection
    def update_embedding(self, message_id: int, embedding: bytes, embedding_model: str, embedding_dim: int) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET embedding = ?, embedding_model = ?, embedding_dim = ? WHERE id = ?",
            (embedding, embedding_model, embedding_dim, message_id),
        )
        conn.commit()

    @with_connection
    def get_messages_by_conversation(self, conversation_id: str) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM conversation_log WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    @with_connection
    def get_messages_without_signatures(self) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM conversation_log WHERE structural_signature IS NULL ORDER BY id ASC"
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    @with_connection
    def get_messages_without_metrics(self) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT cl.* FROM conversation_log cl
               WHERE cl.id NOT IN (SELECT message_id FROM conversation_metrics)
               ORDER BY cl.conversation_id, cl.id ASC"""
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    @with_connection
    def get_surprise_index(self, message_id: int) -> float:
        conn = self._conn()
        row = conn.execute(
            "SELECT surprise_index FROM conversation_metrics WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        if row and row["surprise_index"] is not None:
            return float(row["surprise_index"])
        return 0.0

    @with_connection
    def get_recent_assistant_signatures(self, conversation_id: str, limit: int = 5) -> list[bytes]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT structural_signature FROM conversation_log
               WHERE conversation_id = ? AND speaker = 'apparatus' AND structural_signature IS NOT NULL
               ORDER BY id DESC LIMIT ?""",
            (conversation_id, limit),
        ).fetchall()
        signatures = []
        for r in rows:
            blob = r["structural_signature"]
            if blob:
                signatures.append(blob)
        return signatures

    @with_connection
    def count_dreams_since(self, since_date_str: str) -> int:
        conn = self._conn()
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM conversation_log
               WHERE conversation_id IN (
                   SELECT conversation_id FROM conversation_tags
                   WHERE tag_type = 'structural' AND tag = 'dreams'
               )
               AND speaker = 'apparatus'
               AND timestamp >= ?""",
            (since_date_str,),
        ).fetchone()
        return row["cnt"] if row else 0

    @with_connection
    def mark_message_metabolized(self, message_id: int) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET metabolized = 1 WHERE id = ?",
            (message_id,),
        )
        conn.commit()

    @with_connection
    def get_embeddings_by_speaker(
        self, speaker: str, limit: int = 5, conversation_id: str | None = None,
        exclude_message_id: int | None = None,
    ) -> list[np.ndarray]:
        conn = self._conn()
        exclude_clause = "AND id != ?" if exclude_message_id is not None else ""
        if conversation_id is not None:
            params = (speaker, conversation_id) + ((exclude_message_id,) if exclude_message_id is not None else ()) + (limit,)
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
    def get_last_embedding_by_speaker(self, speaker: str, conversation_id: str | None = None, exclude_message_id: int | None = None) -> np.ndarray | None:
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
    def get_recent_embeddings(self, limit: int = 10, conversation_id: str | None = None, exclude_message_id: int | None = None) -> list[np.ndarray]:
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
                "SELECT embedding, embedding_dim FROM conversation_log "
                "ORDER BY id DESC LIMIT ?",
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
    def get_recent_with_metrics(self, limit: int = 50, offset: int = 0, conversation_id: str | None = None, exclude_message_id: int | None = None) -> list[dict]:
        conn = self._conn()
        exclude_clause = "AND cl.id != ?" if exclude_message_id is not None else ""
        if conversation_id is not None:
            params = (conversation_id,) + ((exclude_message_id,) if exclude_message_id is not None else ()) + (limit, offset)
            rows = conn.execute(
                f"""SELECT cl.id, cl.timestamp, cl.speaker, cl.content, cl.thinking,
                          cl.content_tokens, cl.thinking_tokens, cl.model_used, cl.provider_used,
                          cl.structural_signature, cl.structural_justification,
                          (cl.context_sent IS NOT NULL AND cl.context_sent != '') AS has_context,
                          cm.s_t, cm.novelty, cm.rolling_entropy, cm.coupling,
                          cm.agent_divergence, cm.deficit,
                          cm.reverse_perturbation, cm.surprise_index,
                          cm.mutual_perturbation, cm.vitality,
                          cm.boringness, cm.conceptual_velocity,
                          cm.divergence_resolution_ratio, cm.paskian_health
                    FROM conversation_log cl
                    LEFT JOIN conversation_metrics cm ON cl.id = cm.message_id
                    WHERE cl.conversation_id = ? {exclude_clause}
                    ORDER BY cl.id DESC LIMIT ? OFFSET ?""",
                params,
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT cl.id, cl.timestamp, cl.speaker, cl.content, cl.thinking,
                          cl.content_tokens, cl.thinking_tokens, cl.model_used, cl.provider_used,
                          cl.structural_signature, cl.structural_justification,
                          (cl.context_sent IS NOT NULL AND cl.context_sent != '') AS has_context,
                          cm.s_t, cm.novelty, cm.rolling_entropy, cm.coupling,
                          cm.agent_divergence, cm.deficit,
                          cm.reverse_perturbation, cm.surprise_index,
                          cm.mutual_perturbation, cm.vitality,
                          cm.boringness, cm.conceptual_velocity,
                          cm.divergence_resolution_ratio, cm.paskian_health
                    FROM conversation_log cl
                    LEFT JOIN conversation_metrics cm ON cl.id = cm.message_id
                    ORDER BY cl.id DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    @with_connection
    def count_messages(self, conversation_id: str | None = None) -> int:
        conn = self._conn()
        if conversation_id:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM conversation_log WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM conversation_log"
            ).fetchone()
        return row["cnt"] if row else 0

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
        for msg_id, speaker, vec in candidates:
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
    ) -> list[tuple[int, np.ndarray, Optional[np.ndarray]]]:
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
    def get_by_ids(self, message_ids: list[int]) -> list[Message]:
        if not message_ids:
            return []
        conn = self._conn()
        placeholders = ",".join("?" * len(message_ids))
        rows = conn.execute(
            f"SELECT * FROM conversation_log WHERE id IN ({placeholders})",
            message_ids,
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    @with_connection
    def get_sediment_messages_with_metadata(self, message_ids: list[int]) -> list[dict]:
        if not message_ids:
            return []
        conn = self._conn()
        placeholders = ",".join("?" * len(message_ids))
        rows = conn.execute(
            f"""SELECT cl.*, c.title as conversation_title
               FROM conversation_log cl
               LEFT JOIN conversations c ON cl.conversation_id = c.id
               WHERE cl.id IN ({placeholders})""",
            message_ids,
        ).fetchall()
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "timestamp": datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else datetime.now(),
                "conversation_id": row["conversation_id"],
                "speaker": row["speaker"],
                "content": row["content"],
                "conversation_title": row["conversation_title"] or "Untitled Conversation",
            })
        return results

    @with_connection
    def get_token_totals(self, conversation_id: str | None = None) -> list[dict]:
        conn = self._conn()
        if conversation_id is not None:
            rows = conn.execute(
                """SELECT conversation_id,
                          SUM(CASE WHEN speaker = 'human' THEN content_tokens ELSE 0 END) as user_tokens,
                          SUM(CASE WHEN speaker = 'apparatus' THEN content_tokens ELSE 0 END) as agent_tokens,
                          COALESCE(SUM(thinking_tokens), 0) as thinking_tokens
                   FROM conversation_log
                   WHERE conversation_id = ? AND conversation_id != ''
                   GROUP BY conversation_id""",
                (conversation_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT conversation_id,
                          SUM(CASE WHEN speaker = 'human' THEN content_tokens ELSE 0 END) as user_tokens,
                          SUM(CASE WHEN speaker = 'apparatus' THEN content_tokens ELSE 0 END) as agent_tokens,
                          COALESCE(SUM(thinking_tokens), 0) as thinking_tokens
                   FROM conversation_log
                   WHERE conversation_id != ''
                   GROUP BY conversation_id
                   ORDER BY conversation_id""",
            ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def reassign_messages(self, from_conversation_id: str, to_conversation_id: str) -> int:
        conn = self._conn()
        cursor = conn.execute(
            "UPDATE conversation_log SET conversation_id = ? WHERE conversation_id = ?",
            (to_conversation_id, from_conversation_id),
        )
        conn.commit()
        return cursor.rowcount

    @with_connection
    def increment_message_note_count(self, message_id: int, amount: int = 1) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET note_count = COALESCE(note_count, 0) + ? WHERE id = ?",
            (amount, message_id),
        )
        conn.commit()

    @with_connection
    def update_content(self, message_id: int, content: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET content = ? WHERE id = ?",
            (content, message_id),
        )
        conn.commit()
