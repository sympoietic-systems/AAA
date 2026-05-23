import json
import sqlite3
import threading
import traceback
from datetime import datetime
from typing import Optional

import numpy as np

from .database import get_connection
from .models import Conversation, ErrorLogEntry, Message, MetricsRecord, PerceptionSediment


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
    def list_all(self) -> list[Conversation]:
        conn = self._conn()
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
            "DELETE FROM conversations WHERE id = ?",
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
    ) -> Message:
        conn = self._conn()
        conn.execute(
            """INSERT INTO conversation_log
               (agent_id, speaker, content, thinking, embedding, embedding_model, embedding_dim, conversation_id, content_tokens, thinking_tokens, model_used, provider_used)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, speaker, content, thinking, embedding, embedding_model, embedding_dim, conversation_id, content_tokens, thinking_tokens, model_used, provider_used),
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
    def get_by_id(self, message_id: int) -> Optional[Message]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM conversation_log WHERE id = ?", (message_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_message(row)

    @with_connection
    def get_embeddings_by_speaker(
        self, speaker: str, limit: int = 5, conversation_id: str | None = None
    ) -> list[np.ndarray]:
        conn = self._conn()
        if conversation_id is not None:
            rows = conn.execute(
                "SELECT embedding, embedding_dim FROM conversation_log "
                "WHERE speaker = ? AND conversation_id = ? ORDER BY id DESC LIMIT ?",
                (speaker, conversation_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT embedding, embedding_dim FROM conversation_log "
                "WHERE speaker = ? ORDER BY id DESC LIMIT ?",
                (speaker, limit),
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
    def get_last_embedding_by_speaker(self, speaker: str, conversation_id: str | None = None) -> np.ndarray | None:
        conn = self._conn()
        if conversation_id is not None:
            row = conn.execute(
                "SELECT embedding, embedding_dim FROM conversation_log "
                "WHERE speaker = ? AND conversation_id = ? ORDER BY id DESC LIMIT 1",
                (speaker, conversation_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT embedding, embedding_dim FROM conversation_log "
                "WHERE speaker = ? ORDER BY id DESC LIMIT 1",
                (speaker,),
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
    def get_recent_embeddings(self, limit: int = 10, conversation_id: str | None = None) -> list[np.ndarray]:
        conn = self._conn()
        if conversation_id is not None:
            rows = conn.execute(
                "SELECT embedding, embedding_dim FROM conversation_log "
                "WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
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
    def get_recent_with_metrics(self, limit: int = 50, conversation_id: str | None = None) -> list[dict]:
        conn = self._conn()
        if conversation_id is not None:
            rows = conn.execute(
                """SELECT cl.id, cl.timestamp, cl.speaker, cl.content, cl.thinking,
                          cl.content_tokens, cl.thinking_tokens, cl.model_used, cl.provider_used,
                          cm.s_t, cm.novelty, cm.rolling_entropy, cm.coupling,
                          cm.agent_divergence, cm.deficit,
                          cm.reverse_perturbation, cm.surprise_index,
                          cm.mutual_perturbation, cm.vitality,
                          cm.boringness, cm.conceptual_velocity,
                          cm.divergence_resolution_ratio, cm.paskian_health
                    FROM conversation_log cl
                    LEFT JOIN conversation_metrics cm ON cl.id = cm.message_id
                    WHERE cl.conversation_id = ?
                    ORDER BY cl.id DESC LIMIT ?""",
                (conversation_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT cl.id, cl.timestamp, cl.speaker, cl.content, cl.thinking,
                          cl.content_tokens, cl.thinking_tokens, cl.model_used, cl.provider_used,
                          cm.s_t, cm.novelty, cm.rolling_entropy, cm.coupling,
                          cm.agent_divergence, cm.deficit,
                          cm.reverse_perturbation, cm.surprise_index,
                          cm.mutual_perturbation, cm.vitality,
                          cm.boringness, cm.conceptual_velocity,
                          cm.divergence_resolution_ratio, cm.paskian_health
                    FROM conversation_log cl
                    LEFT JOIN conversation_metrics cm ON cl.id = cm.message_id
                    ORDER BY cl.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    @with_connection
    def count_messages(self, conversation_id: str) -> int:
        conn = self._conn()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM conversation_log WHERE conversation_id = ?",
            (conversation_id,),
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
        embedding=row["embedding"],
        embedding_model=row["embedding_model"],
        embedding_dim=row["embedding_dim"],
        model_used=row["model_used"] if "model_used" in row.keys() else None,
        provider_used=row["provider_used"] if "provider_used" in row.keys() else None,
    )


def _row_to_conversation(row: sqlite3.Row) -> Conversation:
    return Conversation(
        id=row["id"],
        title=row["title"],
        agent_id=row["agent_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        message_count=row["message_count"] if "message_count" in row.keys() else 0,
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
    ) -> PerceptionSediment:
        conn = self._conn()
        conn.execute(
            """INSERT INTO perception_sediment
               (conversation_id, file_name, file_type, chunk_index, chunk_text,
                embedding, embedding_model, token_count, opacity, opacity_meta)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conversation_id, file_name, file_type, chunk_index, chunk_text,
             embedding, embedding_model, token_count, opacity, opacity_meta),
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
            "SELECT * FROM perception_sediment WHERE conversation_id = ? ORDER BY file_name, chunk_index",
            (conversation_id,),
        ).fetchall()
        return [_row_to_perception_sediment(r) for r in rows]

    @with_connection
    def get_embeddings_by_conversation(
        self, conversation_id: str
    ) -> list[tuple[int, np.ndarray]]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT id, embedding, embedding_model FROM perception_sediment WHERE conversation_id = ?",
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
        
        params.extend([conversation_id, file_name])
        query = f"UPDATE perception_files SET {', '.join(updates)} WHERE conversation_id = ? AND file_name = ?"
        conn.execute(query, params)
        conn.commit()

    @with_connection
    def get_files_by_conversation(self, conversation_id: str) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT file_name, file_type, status, summary, summary_model, token_count, chunk_count, created_at, updated_at
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
    )
