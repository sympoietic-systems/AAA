import json
import sqlite3
import traceback
from datetime import datetime
from typing import Optional

import numpy as np

from .database import get_connection
from .models import ErrorLogEntry, Message, MetricsRecord


class MessageRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def insert(
        self,
        speaker: str,
        content: str,
        embedding: bytes,
        embedding_model: str,
        embedding_dim: int,
        thinking: Optional[str] = None,
        agent_id: str = "",
    ) -> Message:
        conn = self._conn()
        conn.execute(
            """INSERT INTO conversation_log
               (agent_id, speaker, content, thinking, embedding, embedding_model, embedding_dim)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, speaker, content, thinking, embedding, embedding_model, embedding_dim),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversation_log WHERE id = last_insert_rowid()"
        ).fetchone()
        return _row_to_message(row)

    def get_recent(self, limit: int = 50) -> list[Message]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM conversation_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_message(r) for r in reversed(rows)]

    def get_by_id(self, message_id: int) -> Optional[Message]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM conversation_log WHERE id = ?", (message_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_message(row)

    def get_embeddings_by_speaker(
        self, speaker: str, limit: int = 5
    ) -> list[np.ndarray]:
        conn = self._conn()
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

    def get_last_embedding_by_speaker(self, speaker: str) -> np.ndarray | None:
        conn = self._conn()
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

    def get_recent_embeddings(self, limit: int = 10) -> list[np.ndarray]:
        conn = self._conn()
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

    def get_recent_with_metrics(self, limit: int = 50) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            """SELECT cl.id, cl.timestamp, cl.speaker, cl.content, cl.thinking,
                      cm.s_t, cm.novelty, cm.rolling_entropy, cm.coupling,
                      cm.agent_divergence, cm.deficit,
                      cm.reverse_perturbation, cm.surprise_index,
                      cm.mutual_perturbation, cm.vitality,
                      cm.boringness, cm.conceptual_velocity,
                      cm.divergence_resolution_ratio, cm.paskian_health
               FROM conversation_log cl
               LEFT JOIN conversation_metrics cm ON cl.id = cm.message_id
               ORDER BY cl.timestamp DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def _row_to_message(row: sqlite3.Row) -> Message:
    return Message(
        id=row["id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        agent_id=row["agent_id"] if "agent_id" in row.keys() else "",
        speaker=row["speaker"],
        content=row["content"],
        thinking=row["thinking"] if "thinking" in row.keys() else None,
        embedding=row["embedding"],
        embedding_model=row["embedding_model"],
        embedding_dim=row["embedding_dim"],
    )


class ErrorLogRepository:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

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
        return get_connection(self._db_path)

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

    def get_recent(self, limit: int = 50) -> list[MetricsRecord]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM conversation_metrics ORDER BY message_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_metrics(r) for r in reversed(rows)]

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

    def get_latest(self) -> MetricsRecord | None:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM conversation_metrics ORDER BY message_id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return _row_to_metrics(row)


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
