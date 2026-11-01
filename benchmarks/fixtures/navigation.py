"""Seeded, non-secret archive fixtures; no model or network dependencies."""

from datetime import UTC, datetime
from types import SimpleNamespace

import numpy as np


def archive(size=4000):
    rng = np.random.default_rng(20261031)
    query = np.zeros(384, dtype=np.float32)
    query[0] = 1
    signature = query[:16].copy()
    candidates = []
    for i in range(size):
        vector = rng.normal(size=384).astype(np.float32)
        vector[0] = abs(vector[0]) + 1
        structural = rng.normal(size=16).astype(np.float32)
        if i % 17 == 0:
            vector = query.copy()
            structural = signature.copy()
        blob = vector.tobytes()
        if i % 101 == 1:
            blob = b"x"
        elif i % 101 == 2:
            blob = np.zeros(384, dtype=np.float32).tobytes()
        elif i % 101 == 3:
            blob = vector[:16].tobytes()
        candidates.append(
            (
                i,
                "human",
                f"Memory <tag>fixture {i}</tag>",
                f"conv-{i % 2}",
                f"2026-10-{i % 28 + 1:02d}",
                blob,
                structural.tobytes(),
            )
        )

    class Messages:
        def get_embeddings_and_signatures_for_search(self, conversation_id=None):
            return [r for r in candidates if conversation_id is None or r[3] == conversation_id]

        def search_text(self, q, conversation_id=None):
            return [
                SimpleNamespace(
                    id=r[0],
                    speaker=r[1],
                    content=r[2],
                    conversation_id=r[3],
                    timestamp=datetime(2026, 10, 1, tzinfo=UTC),
                )
                for r in candidates[:20]
                if conversation_id is None or r[3] == conversation_id
            ]

        def get_glitch_salience_messages(self, conversation_id=None, limit=200):
            return [
                (r[0], None, None, None, None, 0.8, 0.5, 0.1)
                for r in candidates[:limit]
                if conversation_id is None or r[3] == conversation_id
            ]

    class Notes:
        def search_notes_text(self, q):
            return [
                {
                    "id": "note",
                    "conversation_id": "conv-0",
                    "selected_text": "Memory",
                    "comment": "fixture",
                    "asset_type": "conversation_message",
                }
            ]

    class Memories:
        def search_memory_nodes_text(self, q):
            return [{"id": "node", "conversation_id": "conv-0", "intra_active_text": "Memory fixture"}]

    class Embedder:
        async def encode_async(self, q):
            return query

    class Scorer:
        async def score_async(self, q, **kwargs):
            return signature

    state = SimpleNamespace(
        message_repo=Messages(),
        note_repo=Notes(),
        memory_node_repo=Memories(),
        embedder=SimpleNamespace(service=Embedder()),
        structural_scorer=SimpleNamespace(_scorer=Scorer()),
    )
    return SimpleNamespace(app=SimpleNamespace(state=state)), candidates
