from typing import Optional

import numpy as np

from backend.storage.connection import with_connection
from backend.storage.models import PerceptionSediment
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_perception_sediment


class PerceptionSedimentRepository(BaseRepository):
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
    def ensure_conversation_exists(self, conversation_id: str, title: str, agent_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT OR IGNORE INTO conversations (id, title, agent_id) VALUES (?, ?, ?)",
            (conversation_id, title, agent_id),
        )
        conn.commit()

    @with_connection
    def check_file_exists(self, conversation_id: str, file_name: str) -> bool:
        conn = self._conn()
        row = conn.execute(
            "SELECT 1 FROM perception_files WHERE conversation_id = ? AND file_name = ?",
            (conversation_id, file_name),
        ).fetchone()
        return row is not None

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
        conn = self._conn()
        conn.execute("DELETE FROM sediment_injections WHERE id = ?", (injection_id,))
        conn.commit()

    @with_connection
    def get_injected_file_chunks(self, target_conversation_id: str) -> list["PerceptionSediment"]:
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
