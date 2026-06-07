import json
import sqlite3
import threading
import traceback
from datetime import datetime
from typing import Optional

import numpy as np

from .database import get_connection
from .models import Conversation, ErrorLogEntry, Message, MetricsRecord, MemoryNode, PerceptionSediment, BeliefNode, BeliefEvent, SemanticKnot


class ConnectionTracker:
    def __init__(self):
        self.conns = []
        self.depth = 0


_thread_conns = threading.local()


def with_connection(func):
    def wrapper(self, *args, **kwargs):
        if not hasattr(_thread_conns, "tracker") or _thread_conns.tracker is None:
            _thread_conns.tracker = ConnectionTracker()
        
        tracker = _thread_conns.tracker
        tracker.depth += 1
        try:
            return func(self, *args, **kwargs)
        finally:
            tracker.depth -= 1
            if tracker.depth == 0:
                for conn in tracker.conns:
                    try:
                        conn.close()
                    except Exception:
                        pass
                tracker.conns = []
                _thread_conns.tracker = None
    return wrapper


def _get_tracked_connection(db_path: str) -> sqlite3.Connection:
    if not hasattr(_thread_conns, "tracker") or _thread_conns.tracker is None:
        raise RuntimeError("Database connection requested outside of @with_connection context")
    conn = get_connection(db_path)
    _thread_conns.tracker.conns.append(conn)
    return conn



class ConversationRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)

    @with_connection
    def create(self, conversation_id: str, agent_id: str = "", title: str = "") -> Conversation:
        conn = self._conn()
        conn.execute(
            """INSERT INTO conversations (id, title, agent_id)
               VALUES (?, ?, ?)""",
            (conversation_id, title, agent_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return _row_to_conversation(row)

    @with_connection
    def get(self, conversation_id: str) -> Optional[Conversation]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_conversation(row)

    @with_connection
    def list_all(self, tag: Optional[str] = None) -> list[Conversation]:
        conn = self._conn()
        if tag:
            rows = conn.execute(
                """SELECT c.*, COUNT(cl.id) as message_count
                   FROM conversations c
                   LEFT JOIN conversation_log cl ON c.id = cl.conversation_id
                   JOIN conversation_tags ct ON c.id = ct.conversation_id
                   WHERE ct.tag = ?
                   GROUP BY c.id
                   ORDER BY c.updated_at DESC""",
                (tag,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT c.*, COUNT(cl.id) as message_count
                   FROM conversations c
                   LEFT JOIN conversation_log cl ON c.id = cl.conversation_id
                   GROUP BY c.id
                   ORDER BY c.updated_at DESC"""
            ).fetchall()
        return [_row_to_conversation(r) for r in rows]

    @with_connection
    def update_title(self, conversation_id: str, title: str) -> None:
        conn = self._conn()
        conn.execute(
            """UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (title, conversation_id),
        )
        conn.commit()

    @with_connection
    def touch(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()

    @with_connection
    def delete(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            """DELETE FROM conversation_metrics 
               WHERE message_id IN (
                    SELECT id FROM conversation_log WHERE conversation_id = ?
               )""",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM conversation_log WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM perception_sediment WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM perception_files WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM consolidation_checkpoints WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM memory_nodes WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM conversation_tags WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()

    @with_connection
    def get_tags(self, conversation_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT tag, tag_type FROM conversation_tags WHERE conversation_id = ? ORDER BY tag ASC",
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def add_tag(self, conversation_id: str, tag: str, tag_type: str) -> None:
        conn = self._conn()
        conn.execute(
            """INSERT OR IGNORE INTO conversation_tags (conversation_id, tag, tag_type)
               VALUES (?, ?, ?)""",
            (conversation_id, tag.strip(), tag_type),
        )
        conn.commit()

    @with_connection
    def remove_tag(self, conversation_id: str, tag: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM conversation_tags WHERE conversation_id = ? AND tag = ?",
            (conversation_id, tag.strip()),
        )
        conn.commit()

    @with_connection
    def get_all_unique_tags(self) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT DISTINCT tag, tag_type FROM conversation_tags ORDER BY tag ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def mark_requires_consolidation(self, conversation_id: str, requires: bool) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversations SET requires_consolidation = ? WHERE id = ?",
            (1 if requires else 0, conversation_id),
        )
        conn.commit()

    @with_connection
    def update_last_consolidated_at(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversations SET last_consolidated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        conn.commit()


class MessageRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)

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
                   SELECT id FROM conversations WHERE title LIKE 'Dream Log%' OR title LIKE 'Internal Diary%'
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
    def increment_message_note_count(self, message_id: int, amount: int = 1) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE conversation_log SET note_count = COALESCE(note_count, 0) + ? WHERE id = ?",
            (amount, message_id),
        )
        conn.commit()


def _row_to_message(row: sqlite3.Row) -> Message:
    return Message(
        id=row["id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        agent_id=row["agent_id"] if "agent_id" in row.keys() else "",
        conversation_id=row["conversation_id"] if "conversation_id" in row.keys() else "",
        speaker=row["speaker"],
        content=row["content"],
        content_tokens=row["content_tokens"] if "content_tokens" in row.keys() else 0,
        thinking=row["thinking"] if "thinking" in row.keys() else None,
        thinking_tokens=row["thinking_tokens"] if "thinking_tokens" in row.keys() else None,
        context_sent=row["context_sent"] if "context_sent" in row.keys() else None,
        embedding=row["embedding"],
        embedding_model=row["embedding_model"],
        embedding_dim=row["embedding_dim"],
        model_used=row["model_used"] if "model_used" in row.keys() else None,
        provider_used=row["provider_used"] if "provider_used" in row.keys() else None,
        structural_signature=row["structural_signature"] if ("structural_signature" in row.keys() and row["structural_signature"] is not None) else b"",
        structural_justification=row["structural_justification"] if "structural_justification" in row.keys() else None,
        note_count=row["note_count"] if "note_count" in row.keys() else 0,
        metabolized=row["metabolized"] if "metabolized" in row.keys() else 0,
    )


def _row_to_conversation(row: sqlite3.Row) -> Conversation:
    return Conversation(
        id=row["id"],
        title=row["title"],
        agent_id=row["agent_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        message_count=row["message_count"] if "message_count" in row.keys() else 0,
        somatic_reservoir_ad=row["somatic_reservoir_ad"] if "somatic_reservoir_ad" in row.keys() else 0.0,
        matrix_warping=row["matrix_warping"] if "matrix_warping" in row.keys() else 0.0,
        immunological_directive_active=row["immunological_directive_active"] if "immunological_directive_active" in row.keys() else 0,
        requires_consolidation=row["requires_consolidation"] if "requires_consolidation" in row.keys() else 0,
        last_consolidated_at=datetime.fromisoformat(row["last_consolidated_at"]) if ("last_consolidated_at" in row.keys() and row["last_consolidated_at"]) else None,
    )


class ErrorLogRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)

    @with_connection
    def log_error(
        self,
        module: str,
        error: Exception,
        context: Optional[dict] = None,
    ) -> ErrorLogEntry:
        conn = self._conn()
        conn.execute(
            """INSERT INTO error_log (module, error_type, error_message, traceback, context)
               VALUES (?, ?, ?, ?, ?)""",
            (
                module,
                type(error).__name__,
                str(error),
                traceback.format_exc(),
                json.dumps(context) if context else None,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM error_log WHERE id = last_insert_rowid()"
        ).fetchone()
        return ErrorLogEntry(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            module=row["module"],
            error_type=row["error_type"],
            error_message=row["error_message"],
            traceback=row["traceback"],
            context=row["context"],
        )

    @with_connection
    def get_recent(self, limit: int = 20) -> list[ErrorLogEntry]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM error_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            ErrorLogEntry(
                id=r["id"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                module=r["module"],
                error_type=r["error_type"],
                error_message=r["error_message"],
                traceback=r["traceback"],
                context=r["context"],
            )
            for r in rows
        ]


class MetricsRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)

    @with_connection
    def insert(
        self,
        message_id: int,
        s_t: float,
        novelty: float,
        deficit: float,
        rolling_entropy: float | None = None,
        coupling: float | None = None,
        agent_divergence: float | None = None,
        reverse_perturbation: float | None = None,
        surprise_index: float | None = None,
        mutual_perturbation: float | None = None,
        vitality: float | None = None,
        phase_shifts: str | None = None,
        boringness: float | None = None,
        conceptual_velocity: float | None = None,
        divergence_resolution_ratio: float | None = None,
        paskian_health: float | None = None,
        temperature_rec: float | None = None,
        presence_penalty_rec: float | None = None,
        frequency_penalty_rec: float | None = None,
        homeostatic_state: str | None = None,
    ) -> MetricsRecord:
        conn = self._conn()
        conn.execute(
            """INSERT OR REPLACE INTO conversation_metrics
               (message_id, s_t, novelty, rolling_entropy, coupling,
                agent_divergence, deficit, reverse_perturbation, surprise_index,
                mutual_perturbation, vitality, phase_shifts,
                boringness, conceptual_velocity, divergence_resolution_ratio,
                paskian_health,
                temperature_rec, presence_penalty_rec, frequency_penalty_rec,
                homeostatic_state)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message_id, s_t, novelty, rolling_entropy, coupling,
                agent_divergence, deficit, reverse_perturbation, surprise_index,
                mutual_perturbation, vitality, phase_shifts,
                boringness, conceptual_velocity, divergence_resolution_ratio,
                paskian_health,
                temperature_rec, presence_penalty_rec, frequency_penalty_rec,
                homeostatic_state,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversation_metrics WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        return _row_to_metrics(row)

    @with_connection
    def get_recent(self, limit: int = 50) -> list[MetricsRecord]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM conversation_metrics ORDER BY message_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_metrics(r) for r in reversed(rows)]

    @with_connection
    def get_aggregates(self, limit: int = 20) -> dict:
        conn = self._conn()
        row = conn.execute(
            """SELECT
                 AVG(s_t) as avg_s_t,
                 AVG(novelty) as avg_novelty,
                 AVG(rolling_entropy) as avg_entropy,
                 AVG(coupling) as avg_coupling,
                 AVG(agent_divergence) as avg_divergence,
                 AVG(deficit) as avg_deficit,
                 AVG(reverse_perturbation) as avg_rev_pert,
                 AVG(surprise_index) as avg_surprise,
                 AVG(mutual_perturbation) as avg_mpi,
                 AVG(vitality) as avg_vitality,
                 AVG(boringness) as avg_boringness,
                 AVG(conceptual_velocity) as avg_velocity,
                 AVG(divergence_resolution_ratio) as avg_drr,
                 AVG(paskian_health) as avg_pask_health,
                 COUNT(*) as count
               FROM (
                 SELECT * FROM conversation_metrics
                 ORDER BY message_id DESC LIMIT ?
               )""",
            (limit,),
        ).fetchone()
        if row is None or row["count"] == 0:
            return {"count": 0}
        return {
            "count": row["count"],
            "avg_pairwise_similarity": round(row["avg_s_t"], 4) if row["avg_s_t"] is not None else None,
            "avg_novelty": round(row["avg_novelty"], 4) if row["avg_novelty"] is not None else None,
            "avg_rolling_entropy": round(row["avg_entropy"], 6) if row["avg_entropy"] is not None else None,
            "avg_coupling": round(row["avg_coupling"], 4) if row["avg_coupling"] is not None else None,
            "avg_agent_divergence": round(row["avg_divergence"], 4) if row["avg_divergence"] is not None else None,
            "avg_deficit": round(row["avg_deficit"], 4) if row["avg_deficit"] is not None else None,
            "avg_reverse_perturbation": round(row["avg_rev_pert"], 4) if row["avg_rev_pert"] is not None else None,
            "avg_surprise_index": round(row["avg_surprise"], 4) if row["avg_surprise"] is not None else None,
            "avg_mutual_perturbation": round(row["avg_mpi"], 4) if row["avg_mpi"] is not None else None,
            "avg_vitality": round(row["avg_vitality"], 4) if row["avg_vitality"] is not None else None,
            "avg_boringness": round(row["avg_boringness"], 4) if row["avg_boringness"] is not None else None,
            "avg_conceptual_velocity": round(row["avg_velocity"], 4) if row["avg_velocity"] is not None else None,
            "avg_drr": round(row["avg_drr"], 4) if row["avg_drr"] is not None else None,
            "avg_paskian_health": round(row["avg_pask_health"], 4) if row["avg_pask_health"] is not None else None,
        }

    @with_connection
    def get_latest(self) -> MetricsRecord | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM conversation_metrics ORDER BY message_id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return _row_to_metrics(row)


class PerceptionSedimentRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)

    @with_connection
    def get_unfinished_files(self) -> list[dict]:
        conn = self._conn()
        cursor = conn.execute(
            """SELECT conversation_id, file_name, file_type, status 
               FROM perception_files 
               WHERE status IN ('uploading', 'processing', 'error')"""
        )
        return [dict(r) for r in cursor.fetchall()]

    @with_connection
    def get_missed_belief_turns(self) -> list[dict]:
        conn = self._conn()
        cursor = conn.execute(
            """
            SELECT user_msg.id AS user_id, user_msg.conversation_id, assistant_msg.id AS assistant_id
            FROM conversation_log user_msg
            JOIN conversation_log assistant_msg ON assistant_msg.id = (
                SELECT id FROM conversation_log
                WHERE id > user_msg.id 
                  AND conversation_id = user_msg.conversation_id 
                  AND speaker = 'apparatus'
                ORDER BY id ASC LIMIT 1
            )
            WHERE user_msg.speaker = 'human'
              AND user_msg.metabolized = 0
              AND CAST(user_msg.id AS TEXT) NOT IN (
                  SELECT source_id FROM belief_events WHERE source_type = 'chat_turn' AND source_id IS NOT NULL
              )
            ORDER BY user_msg.id ASC
            LIMIT 50
            """
        )
        return [dict(r) for r in cursor.fetchall()]

    @with_connection
    def insert_chunk(
        self,
        conversation_id: str,
        file_name: str,
        file_type: str,
        chunk_index: int,
        chunk_text: str,
        embedding: bytes,
        embedding_model: str,
        token_count: int,
        opacity: int = 0,
        opacity_meta: Optional[str] = None,
        structural_signature: bytes = b"",
    ) -> PerceptionSediment:
        conn = self._conn()
        conn.execute(
            """INSERT INTO perception_sediment
               (conversation_id, file_name, file_type, chunk_index, chunk_text,
                embedding, embedding_model, token_count, opacity, opacity_meta, structural_signature)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conversation_id, file_name, file_type, chunk_index, chunk_text,
             embedding, embedding_model, token_count, opacity, opacity_meta, structural_signature),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM perception_sediment WHERE id = last_insert_rowid()"
        ).fetchone()
        return _row_to_perception_sediment(row)

    @with_connection
    def get_by_conversation(
        self, conversation_id: str
    ) -> list[PerceptionSediment]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT ps.* FROM perception_sediment ps
               LEFT JOIN perception_files pf ON ps.conversation_id = pf.conversation_id AND ps.file_name = pf.file_name
               WHERE ps.conversation_id = ? AND (pf.status IS NULL OR pf.status = 'ready')
               ORDER BY ps.file_name, ps.chunk_index""",
            (conversation_id,),
        ).fetchall()
        return [_row_to_perception_sediment(r) for r in rows]

    @with_connection
    def get_embeddings_by_conversation(
        self, conversation_id: str
    ) -> list[tuple[int, np.ndarray]]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT ps.id, ps.embedding, ps.embedding_model FROM perception_sediment ps
               LEFT JOIN perception_files pf ON ps.conversation_id = pf.conversation_id AND ps.file_name = pf.file_name
               WHERE ps.conversation_id = ? AND (pf.status IS NULL OR pf.status = 'ready')""",
            (conversation_id,),
        ).fetchall()
        result: list[tuple[int, np.ndarray]] = []
        for row in rows:
            blob = row["embedding"]
            if blob:
                vec = np.frombuffer(blob, dtype="float32")
                result.append((row["id"], vec))
        return result

    @with_connection
    def get_chunks_in_similarity_range(
        self,
        query_vec: np.ndarray,
        conversation_id: str,
        min_sim: float,
        max_sim: float,
    ) -> list[tuple[float, int]]:
        candidates = self.get_embeddings_by_conversation(conversation_id)
        scored: list[tuple[float, int]] = []
        for chunk_id, vec in candidates:
            if len(vec) != len(query_vec):
                continue
            sim = float(np.dot(query_vec, vec))
            if min_sim <= sim <= max_sim:
                scored.append((sim, chunk_id))
        return scored


    @with_connection
    def get_by_ids(self, chunk_ids: list[int]) -> list[PerceptionSediment]:
        if not chunk_ids:
            return []
        conn = self._conn()
        placeholders = ",".join("?" * len(chunk_ids))
        rows = conn.execute(
            f"SELECT * FROM perception_sediment WHERE id IN ({placeholders})",
            chunk_ids,
        ).fetchall()
        id_to_row = {r["id"]: _row_to_perception_sediment(r) for r in rows}
        return [id_to_row[cid] for cid in chunk_ids if cid in id_to_row]

    @with_connection
    def get_file_summary(
        self, conversation_id: str
    ) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT file_name, file_type,
                      SUM(token_count) as total_tokens,
                      COUNT(*) as chunk_count
               FROM perception_sediment
               WHERE conversation_id = ?
               GROUP BY file_name, file_type
               ORDER BY file_name""",
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def get_file_preview(
        self, conversation_id: str, file_name: str, max_chars: int = 400
    ) -> str | None:
        conn = self._conn()
        row = conn.execute(
            """SELECT chunk_text FROM perception_sediment
               WHERE conversation_id = ? AND file_name = ?
               ORDER BY chunk_index LIMIT 1""",
            (conversation_id, file_name),
        ).fetchone()
        if not row:
            return None
        text = row["chunk_text"]
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip() + "..."

    @with_connection
    def create_file(self, conversation_id: str, file_name: str, file_type: str, status: str = 'uploading') -> None:
        conn = self._conn()
        conn.execute(
            """INSERT OR IGNORE INTO perception_files (conversation_id, file_name, file_type, status)
               VALUES (?, ?, ?, ?)""",
            (conversation_id, file_name, file_type, status),
        )
        conn.execute(
            """UPDATE perception_files SET status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE conversation_id = ? AND file_name = ?""",
            (status, conversation_id, file_name),
        )
        conn.commit()

    @with_connection
    def update_file(
        self,
        conversation_id: str,
        file_name: str,
        status: str,
        summary: Optional[str] = None,
        summary_model: Optional[str] = None,
        token_count: Optional[int] = None,
        chunk_count: Optional[int] = None,
        interference_score: Optional[float] = None,
        belief_nodes_implicated: Optional[str] = None,
        state_vector_impact: Optional[str] = None,
    ) -> None:
        conn = self._conn()
        updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        if summary is not None:
            updates.append("summary = ?")
            params.append(summary)
        if summary_model is not None:
            updates.append("summary_model = ?")
            params.append(summary_model)
        if token_count is not None:
            updates.append("token_count = ?")
            params.append(token_count)
        if chunk_count is not None:
            updates.append("chunk_count = ?")
            params.append(chunk_count)
        if interference_score is not None:
            updates.append("interference_score = ?")
            params.append(interference_score)
        if belief_nodes_implicated is not None:
            updates.append("belief_nodes_implicated = ?")
            params.append(belief_nodes_implicated)
        if state_vector_impact is not None:
            updates.append("state_vector_impact = ?")
            params.append(state_vector_impact)
        
        params.extend([conversation_id, file_name])
        query = f"UPDATE perception_files SET {', '.join(updates)} WHERE conversation_id = ? AND file_name = ?"
        conn.execute(query, params)
        conn.commit()

    @with_connection
    def get_files_by_conversation(self, conversation_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT file_name, file_type, status, summary, summary_model, token_count, chunk_count, created_at, updated_at,
                      interference_score, belief_nodes_implicated, state_vector_impact
               FROM perception_files
               WHERE conversation_id = ?
               ORDER BY created_at DESC""",
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def delete_file(self, conversation_id: str, file_name: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM perception_sediment WHERE conversation_id = ? AND file_name = ?",
            (conversation_id, file_name),
        )
        conn.execute(
            "DELETE FROM perception_files WHERE conversation_id = ? AND file_name = ?",
            (conversation_id, file_name),
        )
        conn.commit()

    @with_connection
    def delete_chunks(self, conversation_id: str, file_name: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM perception_sediment WHERE conversation_id = ? AND file_name = ?",
            (conversation_id, file_name),
        )
        conn.commit()

    @with_connection
    def delete_chunks_from_index(self, conversation_id: str, file_name: str, from_index: int) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM perception_sediment WHERE conversation_id = ? AND file_name = ? AND chunk_index >= ?",
            (conversation_id, file_name, from_index),
        )
        conn.commit()

    @with_connection
    def get_by_file(
        self, conversation_id: str, file_name: str
    ) -> list[PerceptionSediment]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM perception_sediment WHERE conversation_id = ? AND file_name = ? ORDER BY chunk_index",
            (conversation_id, file_name),
        ).fetchall()
        return [_row_to_perception_sediment(r) for r in rows]

    @with_connection
    def update_chunk_opacity(
        self,
        chunk_id: int,
        opacity: int,
        opacity_meta: str,
    ) -> None:
        conn = self._conn()
        conn.execute(
            """UPDATE perception_sediment
               SET opacity = ?, opacity_meta = ?
               WHERE id = ?""",
            (opacity, opacity_meta, chunk_id),
        )
        conn.commit()


    @with_connection
    def delete_by_conversation(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM perception_sediment WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM perception_files WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.commit()

    @with_connection
    def find_file_by_name(self, file_name: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            """SELECT conversation_id, file_name, file_type, status, summary, summary_model, token_count, chunk_count, created_at, updated_at
               FROM perception_files
               WHERE file_name = ?
               ORDER BY updated_at DESC LIMIT 1""",
            (file_name,),
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def get_chunks_by_file(self, conversation_id: str, file_name: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT chunk_index, chunk_text, token_count, opacity, opacity_meta
               FROM perception_sediment
               WHERE conversation_id = ? AND file_name = ?
               ORDER BY chunk_index""",
            (conversation_id, file_name),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def get_structural_signatures_by_conversation(
        self, conversation_id: str
    ) -> list[tuple[int, np.ndarray]]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT ps.id, ps.structural_signature FROM perception_sediment ps
               LEFT JOIN perception_files pf ON ps.conversation_id = pf.conversation_id AND ps.file_name = pf.file_name
               WHERE ps.conversation_id = ? AND ps.structural_signature IS NOT NULL
                 AND (pf.status IS NULL OR pf.status = 'ready')""",
            (conversation_id,),
        ).fetchall()
        result: list[tuple[int, np.ndarray]] = []
        for row in rows:
            blob = row["structural_signature"]
            if blob:
                vec = np.frombuffer(blob, dtype="float32")
                result.append((row["id"], vec))
        return result

    @with_connection
    def get_structural_signatures_except(
        self, exclude_conversation_id: str, limit: int = 500
    ) -> list[tuple[int, np.ndarray]]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT ps.id, ps.structural_signature FROM perception_sediment ps
               LEFT JOIN perception_files pf ON ps.conversation_id = pf.conversation_id AND ps.file_name = pf.file_name
               WHERE ps.conversation_id != ? AND ps.conversation_id != '' AND ps.structural_signature IS NOT NULL
                 AND (pf.status IS NULL OR pf.status = 'ready')
               ORDER BY ps.id DESC LIMIT ?""",
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
    def get_all_chunk_embeddings_except(
        self, exclude_conversation_id: str, limit: int = 500
    ) -> list[tuple[int, np.ndarray]]:
        """Get chunk embedding vectors from ALL conversations except the current one.

        Used by PerceptionModule as a fallback when the current conversation has
        no native/injected sediment files, or when local similarity search yields
        insufficient results.
        """
        conn = self._conn()
        rows = conn.execute(
            """SELECT ps.id, ps.embedding FROM perception_sediment ps
               LEFT JOIN perception_files pf ON ps.conversation_id = pf.conversation_id AND ps.file_name = pf.file_name
               WHERE ps.conversation_id != ? AND ps.conversation_id != '' AND ps.embedding IS NOT NULL
                 AND (pf.status IS NULL OR pf.status = 'ready')
               ORDER BY ps.id DESC LIMIT ?""",
            (exclude_conversation_id, limit),
        ).fetchall()
        result: list[tuple[int, np.ndarray]] = []
        for row in rows:
            blob = row["embedding"]
            if blob:
                vec = np.frombuffer(blob, dtype="float32")
                result.append((row["id"], vec))
        return result

    @with_connection
    def get_conversation_titles_for_chunk_ids(
        self, chunk_ids: list[int]
    ) -> dict[int, str]:
        conn = self._conn()
        if not chunk_ids:
            return {}
        placeholders = ",".join("?" * len(chunk_ids))
        rows = conn.execute(
            f"""SELECT ps.id, c.title FROM perception_sediment ps
                JOIN conversations c ON ps.conversation_id = c.id
                WHERE ps.id IN ({placeholders})""",
            chunk_ids,
        ).fetchall()
        return {row["id"]: row["title"] for row in rows}

    # ── Sediment Injection (cross-conversation linking) ───────────────

    @with_connection
    def get_all_files_across_conversations(
        self, exclude_conversation_id: str | None = None, search: str | None = None
    ) -> list[dict]:
        """Return perception_files from all conversations, optionally excluding one and filtering by search."""
        conn = self._conn()
        query = """
            SELECT pf.conversation_id, pf.file_name, pf.file_type, pf.status,
                   pf.summary, pf.token_count, pf.chunk_count,
                   pf.created_at, pf.updated_at,
                   c.title AS conversation_title
            FROM perception_files pf
            LEFT JOIN conversations c ON pf.conversation_id = c.id
            WHERE pf.status = 'ready'
        """
        params: list = []
        if exclude_conversation_id:
            query += " AND pf.conversation_id != ?"
            params.append(exclude_conversation_id)
        if search:
            query += " AND (pf.file_name LIKE ? OR pf.summary LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY pf.updated_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def inject_sediment(
        self,
        injection_id: str,
        source_conversation_id: str,
        source_file_name: str,
        target_conversation_id: str,
    ) -> None:
        """Create a sediment injection link from a source file to a target conversation."""
        conn = self._conn()
        conn.execute(
            """INSERT OR IGNORE INTO sediment_injections
               (id, source_conversation_id, source_file_name, target_conversation_id)
               VALUES (?, ?, ?, ?)""",
            (injection_id, source_conversation_id, source_file_name, target_conversation_id),
        )
        conn.commit()

    @with_connection
    def get_injections_for_conversation(self, target_conversation_id: str) -> list[dict]:
        """Get all sediment injections linked to a target conversation."""
        conn = self._conn()
        rows = conn.execute(
            """SELECT si.id, si.source_conversation_id, si.source_file_name,
                      si.target_conversation_id, si.injected_at,
                      pf.file_type, pf.status, pf.summary, pf.token_count, pf.chunk_count,
                      c.title AS source_conversation_title
               FROM sediment_injections si
               JOIN perception_files pf
                 ON si.source_conversation_id = pf.conversation_id
                AND si.source_file_name = pf.file_name
               LEFT JOIN conversations c ON si.source_conversation_id = c.id
               WHERE si.target_conversation_id = ?
               ORDER BY si.injected_at DESC""",
            (target_conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @with_connection
    def remove_injection(self, injection_id: str) -> None:
        """Remove a sediment injection link."""
        conn = self._conn()
        conn.execute("DELETE FROM sediment_injections WHERE id = ?", (injection_id,))
        conn.commit()

    @with_connection
    def get_injected_file_chunks(self, target_conversation_id: str) -> list["PerceptionSediment"]:
        """Get all perception_sediment chunks that have been injected into a target conversation."""
        conn = self._conn()
        rows = conn.execute(
            """SELECT ps.* FROM perception_sediment ps
               JOIN sediment_injections si
                 ON ps.conversation_id = si.source_conversation_id
                AND ps.file_name = si.source_file_name
               WHERE si.target_conversation_id = ?
               ORDER BY ps.file_name, ps.chunk_index""",
            (target_conversation_id,),
        ).fetchall()
        return [_row_to_perception_sediment(r) for r in rows]

    @with_connection
    def get_injected_structural_signatures(
        self, target_conversation_id: str
    ) -> list[tuple[int, np.ndarray]]:
        """Get structural signatures for injected sediment chunks."""
        conn = self._conn()
        rows = conn.execute(
            """SELECT ps.id, ps.structural_signature FROM perception_sediment ps
               JOIN sediment_injections si
                 ON ps.conversation_id = si.source_conversation_id
                AND ps.file_name = si.source_file_name
               JOIN perception_files pf
                 ON ps.conversation_id = pf.conversation_id
                AND ps.file_name = pf.file_name
               WHERE si.target_conversation_id = ?
                 AND ps.structural_signature IS NOT NULL
                 AND pf.status = 'ready'""",
            (target_conversation_id,),
        ).fetchall()
        result: list[tuple[int, np.ndarray]] = []
        for row in rows:
            blob = row["structural_signature"]
            if blob:
                vec = np.frombuffer(blob, dtype="float32")
                result.append((row["id"], vec))
        return result

    # ── Perception Log ─────────────────────────────────────────────────

    @with_connection
    def insert_perception_log(
        self,
        id: str,
        image_path: str,
        artifact_type: str,
        raw_transcription: Optional[str] = None,
        somatic_notes: Optional[str] = None,
        diffractive_analysis: Optional[str] = None,
        g_f_score: float = 0.0,
        a_d_score: float = 0.0,
        structural_vector_16d: str = "[]",
        associated_day: Optional[int] = None,
        belief_nodes_implicated: Optional[str] = None,
    ) -> None:
        conn = self._conn()
        conn.execute(
            """INSERT INTO perception_log
               (id, image_path, artifact_type, raw_transcription, somatic_notes,
                diffractive_analysis, g_f_score, a_d_score, structural_vector_16d, associated_day, belief_nodes_implicated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (id, image_path, artifact_type, raw_transcription, somatic_notes,
             diffractive_analysis, g_f_score, a_d_score, structural_vector_16d, associated_day, belief_nodes_implicated),
        )
        conn.commit()

    @with_connection
    def get_perception_log_by_image(self, image_path: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            """SELECT * FROM perception_log
               WHERE image_path = ?
               ORDER BY timestamp DESC LIMIT 1""",
            (image_path,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "image_path": row["image_path"],
            "artifact_type": row["artifact_type"],
            "raw_transcription": row["raw_transcription"],
            "somatic_notes": row["somatic_notes"],
            "diffractive_analysis": row["diffractive_analysis"],
            "g_f_score": row["g_f_score"],
            "a_d_score": row["a_d_score"],
            "structural_vector_16d": row["structural_vector_16d"],
            "timestamp": row["timestamp"],
            "belief_nodes_implicated": row["belief_nodes_implicated"] if "belief_nodes_implicated" in row.keys() else None,
        }

    @with_connection
    def insert_exogenous_stream(
        self,
        id: str,
        query_used: str,
        source_url: str,
        raw_content: str,
        interference_score: float = 0.0,
        belief_nodes_implicated: Optional[str] = None,
        state_vector_impact: Optional[str] = None,
        associated_file_name: Optional[str] = None,
    ) -> None:
        conn = self._conn()
        conn.execute(
            """INSERT INTO exogenous_stream
               (id, query_used, source_url, raw_content, interference_score,
                belief_nodes_implicated, state_vector_impact, associated_file_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (id, query_used, source_url, raw_content, interference_score,
             belief_nodes_implicated, state_vector_impact, associated_file_name),
        )
        conn.commit()

    @with_connection
    def get_exogenous_stream_by_file(self, file_name: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            """SELECT * FROM exogenous_stream
               WHERE associated_file_name = ?
               ORDER BY timestamp DESC LIMIT 1""",
            (file_name,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "query_used": row["query_used"],
            "source_url": row["source_url"],
            "raw_content": row["raw_content"],
            "interference_score": row["interference_score"],
            "belief_nodes_implicated": row["belief_nodes_implicated"],
            "state_vector_impact": row["state_vector_impact"],
            "timestamp": row["timestamp"],
        }


class ConsolidationCheckpointRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)

    @with_connection
    def save(self, conversation_id: str, message_count: int, summary: str, model: str = "") -> int:
        conn = self._conn()
        conn.execute(
            """INSERT INTO consolidation_checkpoints (conversation_id, message_count, summary, model)
               VALUES (?, ?, ?, ?)""",
            (conversation_id, message_count, summary, model),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM consolidation_checkpoints WHERE id = last_insert_rowid()"
        ).fetchone()
        return row["id"] if row else 0

    @with_connection
    def get_latest(self, conversation_id: str) -> dict | None:
        conn = self._conn()
        row = conn.execute(
            """SELECT * FROM consolidation_checkpoints
               WHERE conversation_id = ?
               ORDER BY id DESC LIMIT 1""",
            (conversation_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "message_count": row["message_count"],
            "summary": row["summary"],
            "model": row["model"],
            "created_at": row["created_at"],
        }

    @with_connection
    def delete_by_conversation(self, conversation_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM consolidation_checkpoints WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.commit()


class MemoryNodeRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)

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


def _row_to_memory_node(row: sqlite3.Row) -> dict:
    tendril_ids = []
    try:
        tendril_ids = json.loads(row["tendril_ids"]) if row["tendril_ids"] else []
    except (json.JSONDecodeError, TypeError):
        pass
    return {
        "id": row["id"],
        "conversation_id": row["conversation_id"],
        "checkpoint_id": row["checkpoint_id"],
        "node_type": row["node_type"],
        "intensity": row["intensity"],
        "scar": row["scar"],
        "glitch_potential": row["glitch_potential"],
        "intra_active_text": row["intra_active_text"],
        "surface_fragment": row["surface_fragment"],
        "agential_symmetry": row["agential_symmetry"],
        "diffractive_key": row["diffractive_key"],
        "tendril_ids": tendril_ids,
        "created_at": row["created_at"],
    }


def _row_to_metrics(row: sqlite3.Row) -> MetricsRecord:
    return MetricsRecord(
        message_id=row["message_id"],
        s_t=row["s_t"],
        novelty=row["novelty"],
        rolling_entropy=row["rolling_entropy"],
        coupling=row["coupling"],
        agent_divergence=row["agent_divergence"],
        deficit=row["deficit"],
        reverse_perturbation=row["reverse_perturbation"] if "reverse_perturbation" in row.keys() else None,
        surprise_index=row["surprise_index"] if "surprise_index" in row.keys() else None,
        mutual_perturbation=row["mutual_perturbation"] if "mutual_perturbation" in row.keys() else None,
        vitality=row["vitality"] if "vitality" in row.keys() else None,
        phase_shifts=row["phase_shifts"] if "phase_shifts" in row.keys() else None,
        boringness=row["boringness"] if "boringness" in row.keys() else None,
        conceptual_velocity=row["conceptual_velocity"] if "conceptual_velocity" in row.keys() else None,
        divergence_resolution_ratio=row["divergence_resolution_ratio"] if "divergence_resolution_ratio" in row.keys() else None,
        paskian_health=row["paskian_health"] if "paskian_health" in row.keys() else None,
        temperature_rec=row["temperature_rec"],
        presence_penalty_rec=row["presence_penalty_rec"],
        frequency_penalty_rec=row["frequency_penalty_rec"],
        homeostatic_state=row["homeostatic_state"],
    )


def _row_to_perception_sediment(row: sqlite3.Row) -> PerceptionSediment:
    # Safely get opacity and opacity_meta with fallbacks
    opacity = row["opacity"] if "opacity" in row.keys() else 0
    opacity_meta = row["opacity_meta"] if "opacity_meta" in row.keys() else None
    structural_signature = row["structural_signature"] if ("structural_signature" in row.keys() and row["structural_signature"] is not None) else b""
    return PerceptionSediment(
        id=row["id"],
        conversation_id=row["conversation_id"],
        file_name=row["file_name"],
        file_type=row["file_type"],
        chunk_index=row["chunk_index"],
        chunk_text=row["chunk_text"],
        embedding=row["embedding"],
        embedding_model=row["embedding_model"],
        token_count=row["token_count"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        opacity=opacity,
        opacity_meta=opacity_meta,
        structural_signature=structural_signature,
    )


class BeliefRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)

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


class SemanticKnotRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._local = threading.local()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = get_connection(self._db_path)
        return self._local.conn

    @with_connection
    def insert_knot(
        self,
        id: str,
        conversation_id: str,
        concept_payload: str,
        embedding: bytes,
        embedding_model: str,
        token_count: int,
        weight: float = 1.0,
        structural_signature: Optional[bytes] = None,
    ) -> SemanticKnot:
        conn = self._conn()
        conn.execute(
            """INSERT INTO semantic_knots
               (id, conversation_id, weight, concept_payload, embedding, embedding_model, token_count, structural_signature)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                id,
                conversation_id,
                weight,
                concept_payload,
                embedding,
                embedding_model,
                token_count,
                structural_signature,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM semantic_knots WHERE id = ?", (id,)
        ).fetchone()
        return _row_to_semantic_knot(row)

    @with_connection
    def get_by_conversation(self, conversation_id: str) -> list[SemanticKnot]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM semantic_knots WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
        return [_row_to_semantic_knot(r) for r in rows]

    @with_connection
    def get_embeddings_and_signatures_except(
        self, exclude_conversation_id: str, limit: int = 500
    ) -> list[tuple[str, np.ndarray, Optional[np.ndarray], str]]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT id, embedding, structural_signature, concept_payload FROM semantic_knots
               WHERE conversation_id != ? AND embedding IS NOT NULL
               ORDER BY created_at DESC LIMIT ?""",
            (exclude_conversation_id, limit),
        ).fetchall()
        result = []
        for row in rows:
            emb_blob = row["embedding"]
            sig_blob = row["structural_signature"]
            
            emb_vec = None
            if emb_blob:
                emb_vec = np.frombuffer(emb_blob, dtype="float32")
            
            sig_vec = None
            if sig_blob:
                sig_vec = np.frombuffer(sig_blob, dtype="float32")
                
            if emb_vec is not None:
                result.append((row["id"], emb_vec, sig_vec, row["concept_payload"]))
        return result

    @with_connection
    def get_knots_in_similarity_range(
        self,
        query_vec: np.ndarray,
        exclude_conversation_id: str,
        min_sim: float,
        max_sim: float,
        limit: int = 30,
    ) -> list[tuple[float, str]]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT id, embedding FROM semantic_knots
               WHERE conversation_id != ? AND embedding IS NOT NULL""",
            (exclude_conversation_id,),
        ).fetchall()
        
        candidates = []
        for row in rows:
            emb_blob = row["embedding"]
            if not emb_blob:
                continue
            emb_vec = np.frombuffer(emb_blob, dtype="float32")
            if len(emb_vec) != len(query_vec):
                continue
            norm1 = np.linalg.norm(query_vec)
            norm2 = np.linalg.norm(emb_vec)
            if norm1 == 0 or norm2 == 0:
                sim = 0.0
            else:
                sim = float(np.dot(query_vec, emb_vec) / (norm1 * norm2))
            
            if min_sim <= sim <= max_sim:
                candidates.append((sim, row["id"]))
                
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[:limit]

    @with_connection
    def get_by_ids(self, knot_ids: list[str]) -> list[SemanticKnot]:
        if not knot_ids:
            return []
        conn = self._conn()
        placeholders = ",".join("?" * len(knot_ids))
        rows = conn.execute(
            f"SELECT * FROM semantic_knots WHERE id IN ({placeholders})",
            knot_ids,
        ).fetchall()
        return [_row_to_semantic_knot(r) for r in rows]

    @with_connection
    def update_knot(
        self,
        knot_id: str,
        concept_payload: str,
        embedding: bytes,
        weight: float,
        structural_signature: bytes,
    ) -> None:
        conn = self._conn()
        conn.execute(
            """UPDATE semantic_knots
               SET concept_payload = ?, embedding = ?, weight = ?, structural_signature = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (concept_payload, embedding, weight, structural_signature, knot_id),
        )
        conn.commit()

    @with_connection
    def delete_knot(self, knot_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM semantic_knots WHERE id = ?",
            (knot_id,),
        )
        conn.commit()


def _row_to_belief_node(row: sqlite3.Row) -> BeliefNode:
    created = row["created_at"]
    updated = row["updated_at"]
    last_reinforced = None
    try:
        last_reinforced_raw = row["last_reinforced_at"]
        if last_reinforced_raw:
            last_reinforced = datetime.fromisoformat(last_reinforced_raw) if isinstance(last_reinforced_raw, str) else last_reinforced_raw
    except (IndexError, KeyError):
        pass

    lifecycle = "crystallized"
    try:
        lifecycle = row["lifecycle_stage"] or "crystallized"
    except (IndexError, KeyError):
        pass

    last_dreamed = None
    try:
        last_dreamed_raw = row["last_dreamed_at"]
        if last_dreamed_raw:
            last_dreamed = datetime.fromisoformat(last_dreamed_raw) if isinstance(last_dreamed_raw, str) else last_dreamed_raw
    except (IndexError, KeyError):
        pass

    return BeliefNode(
        id=row["id"],
        agent_id=row["agent_id"],
        label=row["label"],
        statement=row["statement"],
        origin=row["origin"],
        confidence=row["confidence"],
        ontological_mass=row["ontological_mass"],
        somatic_anchor=row["somatic_anchor"],
        vector_16d=row["vector_16d"],
        lifecycle_stage=lifecycle,
        last_reinforced_at=last_reinforced,
        last_dreamed_at=last_dreamed,
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else updated,
    )


def _row_to_belief_event(row: sqlite3.Row) -> BeliefEvent:
    ts = row["timestamp"]
    return BeliefEvent(
        id=row["id"],
        timestamp=datetime.fromisoformat(ts) if isinstance(ts, str) else ts,
        belief_id=row["belief_id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        alignment_coefficient=row["alignment_coefficient"],
        perturbation_magnitude=row["perturbation_magnitude"],
        event_type=row["event_type"],
        impact_score=row["impact_score"],
        rationale=row["rationale"],
    )


def _row_to_semantic_knot(row: sqlite3.Row) -> SemanticKnot:
    created = row["created_at"]
    return SemanticKnot(
        id=row["id"],
        conversation_id=row["conversation_id"],
        created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        weight=row["weight"],
        concept_payload=row["concept_payload"],
        embedding=row["embedding"],
        embedding_model=row["embedding_model"],
        token_count=row["token_count"],
        structural_signature=row["structural_signature"] or b"",
    )


class NoteRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return _get_tracked_connection(self._db_path)

    @with_connection
    def create_note(
        self,
        id: str,
        conversation_id: str,
        message_id: int,
        selected_text: str,
        comment: str = "",
        visibility: str = "personal",
        start_offset: Optional[int] = None,
    ) -> dict:
        conn = self._conn()
        
        # 1. Update message content with <mark id="...">
        row_msg = conn.execute(
            "SELECT content FROM conversation_log WHERE id = ?", (message_id,)
        ).fetchone()
        if row_msg:
            content = row_msg["content"]
            new_content = None
            if start_offset is not None:
                # Build plain text and mapping
                plain_chars = []
                mapping = []
                
                i = 0
                n = len(content)
                
                while i < n:
                    if content[i:].startswith('<mark') or content[i:].startswith('<aaa-note'):
                        close_idx = content.find('>', i)
                        if close_idx != -1:
                            i = close_idx + 1
                            continue
                    elif content[i:].startswith('</mark>') or content[i:].startswith('</aaa-note>'):
                        close_idx = content.find('>', i)
                        if close_idx != -1:
                            i = close_idx + 1
                            continue
                            
                    char = content[i]
                    if char in ('*', '_', '`', '~'):
                        i += 1
                        continue
                        
                    plain_chars.append(char)
                    mapping.append(i)
                    i += 1
                    
                plain_text = "".join(plain_chars)
                
                # Find all occurrences of selected_text in plain_text
                matches = []
                start_search = 0
                while True:
                    idx = plain_text.find(selected_text, start_search)
                    if idx == -1:
                        break
                    matches.append(idx)
                    start_search = idx + 1
                    
                if matches:
                    # Choose the match closest to start_offset
                    chosen_idx = min(matches, key=lambda x: abs(x - start_offset))
                    
                    start_plain = chosen_idx
                    end_plain = chosen_idx + len(selected_text) - 1
                    
                    start_content = mapping[start_plain]
                    end_content = mapping[end_plain]
                    
                    new_content = (
                        content[:start_content]
                        + f'<mark id="{id}">'
                        + content[start_content:end_content + 1]
                        + f'</mark>'
                        + content[end_content + 1:]
                    )
            
            if new_content is None:
                # Use regex-based alignment to match across markdown formatting and existing HTML tags
                import re
                trimmed_sel = selected_text.strip()
                if trimmed_sel:
                    pattern_parts = []
                    filler = r"(?:[\*_~`]|<[^>]+>)*"
                    for char in trimmed_sel:
                        if char.isspace():
                            pattern_parts.append(r"(?:[\s\*_~`]|<[^>]+>)*")
                        else:
                            pattern_parts.append(re.escape(char))
                    pattern = filler.join(pattern_parts)
                    match = re.search(pattern, content)
                    if match:
                        start, end = match.span()
                        new_content = (
                            content[:start]
                            + f'<mark id="{id}">'
                            + content[start:end]
                            + f'</mark>'
                            + content[end:]
                        )
            
            if new_content is not None:
                conn.execute(
                    "UPDATE conversation_log SET content = ? WHERE id = ?",
                    (new_content, message_id),
                )

        # 2. Insert the note
        conn.execute(
            """INSERT INTO conversation_notes (id, conversation_id, message_id, selected_text, comment, visibility)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (id, conversation_id, message_id, selected_text, comment, visibility),
        )
        conn.commit()
        
        row = conn.execute(
            "SELECT * FROM conversation_notes WHERE id = ?", (id,)
        ).fetchone()
        return dict(row) if row else {}

    @with_connection
    def get_note(self, note_id: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM conversation_notes WHERE id = ?", (note_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def get_notes_by_conversation(self, conversation_id: str) -> list[dict]:
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM conversation_notes WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    @with_connection
    def update_note(self, note_id: str, comment: Optional[str] = None, visibility: Optional[str] = None) -> Optional[dict]:
        conn = self._conn()
        updates = []
        params = []
        if comment is not None:
            updates.append("comment = ?")
            params.append(comment)
        if visibility is not None:
            updates.append("visibility = ?")
            params.append(visibility)
        
        if not updates:
            row = conn.execute("SELECT * FROM conversation_notes WHERE id = ?", (note_id,)).fetchone()
            return dict(row) if row else None
            
        updates.append("updated_at = CURRENT_TIMESTAMP")
        # Add values for updates
        sql_params = params + [note_id]
        
        conn.execute(
            f"UPDATE conversation_notes SET {', '.join(updates)} WHERE id = ?",
            sql_params
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversation_notes WHERE id = ?", (note_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def delete_note(self, note_id: str) -> None:
        conn = self._conn()
        
        # 1. Fetch note to get message_id
        row_note = conn.execute(
            "SELECT message_id FROM conversation_notes WHERE id = ?", (note_id,)
        ).fetchone()
        
        if row_note:
            message_id = row_note["message_id"]
            row_msg = conn.execute(
                "SELECT content FROM conversation_log WHERE id = ?", (message_id,)
            ).fetchone()
            if row_msg:
                content = row_msg["content"]
                import re
                new_content = re.sub(
                    rf'<(?:aaa-note|mark) id="{note_id}">(.*?)</(?:aaa-note|mark)>',
                    r'\1',
                    content
                )
                if new_content != content:
                    conn.execute(
                        "UPDATE conversation_log SET content = ? WHERE id = ?",
                        (new_content, message_id),
                    )

        # 2. Delete the note
        conn.execute(
            "DELETE FROM conversation_notes WHERE id = ?",
            (note_id,),
        )
        conn.commit()

