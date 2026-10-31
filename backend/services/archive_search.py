"""Archive search's synchronous read/rank boundary; no HTTP objects or model calls."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel

from backend.utils.vector import cosine_similarity

logger = logging.getLogger(__name__)


class SearchBusy(Exception):
    """The bounded ranking admission queue is full or its wait expired."""


class SearchCapacity:
    def __init__(self, active_limit: int = 2, waiting_limit: int = 8, wait_seconds: float = 2) -> None:
        self.loop = asyncio.get_running_loop()
        self.active = 0
        self.waiting = 0
        self._active_limit = active_limit
        self._waiting_limit = waiting_limit
        self._wait_seconds = wait_seconds
        self._condition = asyncio.Condition()
        self._jobs: set[asyncio.Task[list[SearchMatch]]] = set()

    async def _release(self, job: asyncio.Task[list[SearchMatch]]) -> None:
        self._jobs.discard(job)
        if not job.cancelled():
            job.exception()  # Observe a failure even if its requesting client disconnected.
        async with self._condition:
            self.active -= 1
            self._condition.notify_all()

    async def run(self, work: Callable[[], list[SearchMatch]]) -> list[SearchMatch]:
        async with self._condition:
            if self.active >= self._active_limit:
                if self.waiting >= self._waiting_limit:
                    raise SearchBusy()
                self.waiting += 1
                try:
                    await asyncio.wait_for(
                        self._condition.wait_for(lambda: self.active < self._active_limit), self._wait_seconds
                    )
                except TimeoutError as exc:
                    raise SearchBusy() from exc
                finally:
                    self.waiting -= 1
            self.active += 1
        job = asyncio.create_task(asyncio.to_thread(work))
        self._jobs.add(job)
        job.add_done_callback(lambda finished: self.loop.create_task(self._release(finished)))
        return await asyncio.shield(job)


class SearchMatch(BaseModel):
    id: str
    type: str  # "message" | "note" | "memory_node"
    conversation_id: str
    title: str
    snippet: str
    relevance_score: float
    timestamp: str


def strip_xml_tags(text: str) -> str:
    if not text:
        return ""
    # Strip any XML/HTML-like tags, keeping the inner text
    return re.sub(r"<[^>]+>", "", text)


def get_snippet(text: str, query: str, length: int = 150) -> str:
    cleaned = strip_xml_tags(text)
    if not query:
        return cleaned[:length] + "..." if len(cleaned) > length else cleaned

    idx = cleaned.lower().find(query.lower())
    if idx == -1:
        return cleaned[:length] + "..." if len(cleaned) > length else cleaned

    start = max(0, idx - 50)
    end = min(len(cleaned), idx + length - 50)
    snippet = cleaned[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(cleaned):
        snippet = snippet + "..."
    return snippet


def _scalar_cosine(query: NDArray[np.float32] | None, blob: bytes | None) -> float:
    if query is None or not blob:
        return 0.0
    try:
        return float(cosine_similarity(query, np.frombuffer(blob, dtype="float32")))
    except (ValueError, TypeError):
        logger.debug("Skipping malformed archive vector")
        return 0.0


def _batch_cosines(query: NDArray[np.float32] | None, blobs: list[bytes | None]) -> list[float]:
    scores = [0.0] * len(blobs)
    if query is None:
        return scores
    norm = float(np.linalg.norm(query))
    if norm == 0:
        return scores
    for start in range(0, len(blobs), 256):
        vectors, indices = [], []
        for index in range(start, min(start + 256, len(blobs))):
            blob = blobs[index]
            if not blob or len(blob) != query.size * 4:
                continue
            vectors.append(np.frombuffer(blob, dtype="float32"))
            indices.append(index)
        if not vectors:
            continue
        matrix = np.stack(vectors)
        norms = np.linalg.norm(matrix, axis=1).astype(np.float64) * norm
        dots = np.einsum("ij,j->i", matrix, query)
        values = np.divide(dots, norms, out=np.zeros(len(indices)), where=norms != 0)
        for index, value in zip(indices, values, strict=True):
            scores[index] = float(value)
    return scores


def search_sync(
    state: Any,
    q: str,
    conversation_id: str | None,
    mode: str,
    w_text: float,
    w_semantic: float,
    w_structural: float,
    w_glitch: float,
    query_emb: NDArray[np.float32] | None,
    query_sig: NDArray[np.float32] | None,
) -> list[SearchMatch]:
    # Compatibility membrane around the existing repository container.
    message_repo, note_repo, memory_node_repo = state.message_repo, state.note_repo, state.memory_node_repo
    matches: list[SearchMatch] = []

    # 1. Fetch text matches
    text_message_ids = set()
    if w_text > 0.0 and q:
        # Dialogue messages text match
        text_msgs = message_repo.search_text(q, conversation_id)
        for msg in text_msgs:
            text_message_ids.add(msg.id)
            snippet = get_snippet(msg.content, q)
            matches.append(
                SearchMatch(
                    id=str(msg.id),
                    type="message",
                    conversation_id=msg.conversation_id,
                    title=f"Dialogue: {msg.speaker.capitalize()}",
                    snippet=snippet,
                    relevance_score=w_text * 1.0,
                    timestamp=msg.timestamp.isoformat() if hasattr(msg.timestamp, "isoformat") else str(msg.timestamp),
                )
            )

        # Notes text match
        notes = note_repo.search_notes_text(q)
        for note in notes:
            if conversation_id and note.get("conversation_id") != conversation_id:
                continue
            snippet = get_snippet(note.get("selected_text", "") + " - " + note.get("comment", ""), q)
            matches.append(
                SearchMatch(
                    id=note.get("id"),
                    type="note",
                    conversation_id=note.get("conversation_id") or "",
                    title=f"Note: {note.get('asset_type', '').replace('_', ' ').capitalize()}",
                    snippet=snippet,
                    relevance_score=w_text * 1.0,
                    timestamp=note.get("created_at").isoformat()
                    if hasattr(note.get("created_at"), "isoformat")
                    else str(note.get("created_at") or ""),
                )
            )

        # Memory Nodes text match
        mem_nodes = memory_node_repo.search_memory_nodes_text(q)
        for node in mem_nodes:
            if conversation_id and node.get("conversation_id") != conversation_id:
                continue
            snippet = get_snippet(node.get("intra_active_text", "") or node.get("scar", ""), q)
            matches.append(
                SearchMatch(
                    id=node.get("id"),
                    type="memory_node",
                    conversation_id=node.get("conversation_id") or "",
                    title=f"Memory: {node.get('node_type', 'concept').capitalize()} ({node.get('agential_symmetry', '')})",
                    snippet=snippet,
                    relevance_score=w_text * 1.0,
                    timestamp=node.get("created_at").isoformat()
                    if hasattr(node.get("created_at"), "isoformat")
                    else str(node.get("created_at") or ""),
                )
            )

    # 2. Vector-based scoring (Semantic & Diffractive) and Glitch Salience
    # Primarily queries and ranks dialogue messages
    if w_semantic > 0.0 or w_structural > 0.0 or w_glitch > 0.0:
        # Load all messages candidates with embeddings and signatures
        candidates = message_repo.get_embeddings_and_signatures_for_search(conversation_id)

        # Load glitch salience metrics mappings if weight active
        glitch_map = {}
        if w_glitch > 0.0:
            glitch_msgs = message_repo.get_glitch_salience_messages(conversation_id, limit=200)
            for m_id, _, _, _, _, surprise, novelty, deficit in glitch_msgs:
                glitch_map[m_id] = max(surprise or 0.0, novelty or 0.0, deficit or 0.0)

        by_id = {match.id: match for match in matches if match.type == "message"}
        base_scores = {key: match.relevance_score for key, match in by_id.items()}
        candidate_by_id = {str(row[0]): row for row in candidates}
        sem_scores = _batch_cosines(query_emb, [row[5] for row in candidates])
        str_scores = _batch_cosines(query_sig, [row[6] for row in candidates])
        for index, (m_id, speaker, content, conv_id, timestamp, emb_blob, sig_blob) in enumerate(candidates):
            # Small NumPy/Pydantic calls can retain the GIL across a ranking burst.
            # Yield the worker periodically so lightweight event-loop work can run.
            if index % 128 == 0:
                time.sleep(0)
            existing_match = by_id.get(str(m_id))
            s_sem, s_str = sem_scores[index], str_scores[index]
            # Scalar parity at score/gate boundaries avoids batch-rounding membership changes.
            if abs(s_sem) < 1e-5 or abs(s_sem - 0.45) < 1e-5:
                s_sem = _scalar_cosine(query_emb, emb_blob)
            if abs(s_str) < 1e-5 or abs(s_str - 0.8) < 1e-5:
                s_str = _scalar_cosine(query_sig, sig_blob)

            g_score = glitch_map.get(m_id, 0.0)

            # Diffractive Goldilocks gate (pure diffractive mode only):
            # Structural isomorphism = high s_str (≥0.80) AND low s_sem (≤0.45).
            # This mirrors the convention in diffractive_retrieval.py.
            # In composite/weighted mode we fall back to continuous scoring.
            if mode == "diffractive" and w_semantic == 0.0:
                # Hard gate: skip unless structurally isomorphic
                if s_str < 0.80 or s_sem > 0.45:
                    continue
                diff_score = s_str
            else:
                # Continuous weighted scoring: structural minus semantic overlap
                diff_score = s_str * (1.0 - s_sem) if (w_structural > 0.0 and query_emb is not None) else s_str

            comp_score = (w_semantic * max(0.0, s_sem)) + (w_structural * max(0.0, diff_score)) + (w_glitch * g_score)

            if comp_score <= 0.0:
                continue

            if existing_match:
                existing_match.relevance_score += comp_score
            else:
                snippet = get_snippet(content, q)
                matches.append(
                    SearchMatch(
                        id=str(m_id),
                        type="message",
                        conversation_id=conv_id,
                        title=f"Dialogue: {speaker.capitalize()}",
                        snippet=snippet,
                        relevance_score=comp_score,
                        timestamp=timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                    )
                )

    # Preserve the existing timestamp-ascending tie break.
    matches.sort(key=lambda x: (-x.relevance_score, x.timestamp), reverse=False)

    if w_semantic > 0 or w_structural > 0 or w_glitch > 0:
        near: set[int] = set()
        for index in range(1, len(matches)):
            if abs(matches[index].relevance_score - matches[index - 1].relevance_score) <= 1e-5:
                near.update((index - 1, index))
        for ordinal, index in enumerate(near):
            if ordinal % 128 == 0:
                time.sleep(0)
            match = matches[index]
            if match.type != "message" or match.id not in candidate_by_id:
                continue
            row = candidate_by_id[match.id]
            sem, structural = _scalar_cosine(query_emb, row[5]), _scalar_cosine(query_sig, row[6])
            diff = structural * (1 - sem) if w_structural > 0 and query_emb is not None else structural
            value = w_semantic * max(0.0, sem) + w_structural * max(0.0, diff) + w_glitch * glitch_map.get(row[0], 0.0)
            match.relevance_score = base_scores.get(match.id, 0.0) + value
        matches.sort(key=lambda match: (-match.relevance_score, match.timestamp))
    return matches[:100]
