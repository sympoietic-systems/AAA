import threading
from typing import Optional

import numpy as np

from backend.storage.connection import with_connection, _get_tracked_connection
from backend.storage.models import SemanticKnot
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_semantic_knot


class SemanticKnotRepository(BaseRepository):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        self._local = threading.local()

    def _conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            from backend.storage.database import get_connection
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
