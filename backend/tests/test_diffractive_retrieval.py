import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock
import numpy as np
import pytest

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.modules.diffractive_retrieval import DiffractiveRetrievalModule
from backend.storage.repository import MessageRepository, PerceptionSedimentRepository


@pytest.fixture
def mock_repos():
    msg_repo = MagicMock(spec=MessageRepository)
    perception_repo = MagicMock(spec=PerceptionSedimentRepository)
    return msg_repo, perception_repo


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_diffractive_retrieval_disabled(mock_repos):
    msg_repo, perception_repo = mock_repos
    module = DiffractiveRetrievalModule(
        message_repo=msg_repo,
        perception_repo=perception_repo,
        enabled=False,
    )

    payload = {"conversation_id": "test_conv", "embedding": b"dummy_vec", "conversation_vitality": 0.5}
    res = await module.process(payload)

    assert res["diffractive_state"] == "FLOWING"
    assert len(res["diffractive_messages"]) == 0


@pytest.mark.anyio
async def test_hysteresis_state_machine(mock_repos, monkeypatch):
    monkeypatch.setattr(np.random, "uniform", lambda a, b: 0.0)
    msg_repo, perception_repo = mock_repos
    module = DiffractiveRetrievalModule(
        message_repo=msg_repo,
        perception_repo=perception_repo,
        enabled=True,
        cohesion_length=3,
    )

    # Initial state is FLOWING. Let's trigger STAGNANT.
    # We want boringness high (1.0), rolling_entropy low (0.0), vitality low (0.0) -> high P_diffract
    payload = {
        "conversation_id": "test_conv",
        "embedding": np.zeros(384, dtype="float32").tobytes(),
        "conversation_vitality": 0.0,
        "metrics": {"boringness": 1.0, "rolling_entropy": 0.0},
    }

    # First turn: transitions to STAGNANT, cohesion timer set to 3
    res1 = await module.process(payload)
    assert res1["diffractive_state"] == "STAGNANT"
    assert module._timers["test_conv"] == 3

    # Second turn: cohesion countdown decreases to 2, state remains STAGNANT even if P_diffract drops
    low_stagnation_payload = {
        "conversation_id": "test_conv",
        "embedding": np.zeros(384, dtype="float32").tobytes(),
        "conversation_vitality": 1.0,
        "metrics": {"boringness": 0.0, "rolling_entropy": 1.0},
    }
    res2 = await module.process(low_stagnation_payload)
    assert res2["diffractive_state"] == "STAGNANT"
    assert module._timers["test_conv"] == 2

    # Third turn: cohesion countdown decreases to 1, state remains STAGNANT
    res3 = await module.process(low_stagnation_payload)
    assert res3["diffractive_state"] == "STAGNANT"
    assert module._timers["test_conv"] == 1

    # Fourth turn: cohesion countdown decreases to 0, state remains STAGNANT because it decreases at the start of process
    res4 = await module.process(low_stagnation_payload)
    assert res4["diffractive_state"] == "STAGNANT"
    assert module._timers["test_conv"] == 0

    # Fifth turn: timer is 0. Since low_stagnation_payload has low P_diffract, state should return to FLOWING
    res5 = await module.process(low_stagnation_payload)
    assert res5["diffractive_state"] == "FLOWING"


@pytest.mark.anyio
async def test_dynamic_bounds_and_budget(mock_repos, monkeypatch):
    monkeypatch.setattr(np.random, "randint", lambda a, b=None: 2)
    monkeypatch.setattr(np.random, "uniform", lambda a, b: 0.0)
    msg_repo, perception_repo = mock_repos
    module = DiffractiveRetrievalModule(
        message_repo=msg_repo,
        perception_repo=perception_repo,
        enabled=True,
        max_diffractive_count=3,
        token_budget=1000,
    )

    # Setup mocks
    # We want to return some candidates for similarity matching
    from backend.modules.structural_engine import CompositeStructuralScorer
    monkeypatch.setattr(CompositeStructuralScorer, "score_async", AsyncMock(return_value=np.ones(16, dtype="float32")))

    msg_repo.get_embeddings_and_signatures_except.return_value = [
        (101, np.ones(384, dtype="float32"), np.ones(16, dtype="float32")),
        (102, np.ones(384, dtype="float32"), np.ones(16, dtype="float32")),
        (103, np.ones(384, dtype="float32"), np.ones(16, dtype="float32")),
    ]
    msg_repo.get_embeddings_in_similarity_range.return_value = [
        (0.65, 101),
        (0.60, 102),
        (0.55, 103),
    ]
    msg_repo.get_sediment_messages_with_metadata.return_value = [
        {"id": 101, "content": "Nomadic message one content details", "conversation_title": "Conv A", "timestamp": "2026-05-23", "conversation_id": "conv_a"},
        {"id": 102, "content": "Nomadic message two content details", "conversation_title": "Conv B", "timestamp": "2026-05-23", "conversation_id": "conv_b"},
        {"id": 103, "content": "Nomadic message three content details", "conversation_title": "Conv C", "timestamp": "2026-05-23", "conversation_id": "conv_c"},
    ]

    perception_repo.get_chunks_in_similarity_range.return_value = [
        (0.50, "chunk_1"),
        (0.48, "chunk_2"),
    ]
    mock_chunk_1 = MagicMock(id="chunk_1", chunk_text="Dormant file chunk one text", file_name="file_a.txt")
    mock_chunk_2 = MagicMock(id="chunk_2", chunk_text="Dormant file chunk two text", file_name="file_b.txt")
    perception_repo.get_by_ids.return_value = [mock_chunk_1, mock_chunk_2]

    # Force stagnant state transition on clean module state
    module._states["test_conv_2"] = "STAGNANT"
    module._timers["test_conv_2"] = 0

    payload = {
        "conversation_id": "test_conv_2",
        "embedding": np.zeros(384, dtype="float32").tobytes(),
        "conversation_vitality": 0.01,
        "metrics": {"boringness": 0.9, "rolling_entropy": 0.1},
    }

    res = await module.process(payload)
    assert res["diffractive_state"] == "STAGNANT"
    assert len(res["diffractive_messages"]) > 0

    # Verify interleaving order of nomadic and file chunks
    types = [item["type"] for item in res["diffractive_messages"]]
    # Should alternate nomadic, dormant_file, nomadic, dormant_file, etc.
    assert types[0] == "nomadic"
    if len(types) > 1:
        assert types[1] == "dormant_file"

    # Verify diffractive_meta is populated and structured
    assert "diffractive_meta" in res
    meta = res["diffractive_meta"]
    assert meta["state"] == "STAGNANT"
    assert meta["p_diffract"] >= 0.0
    assert meta["token_budget"] == int(1000 * meta["r_context"])
    assert meta["items_injected"] == len(res["diffractive_messages"])
    assert len(meta["sources"]) == len(res["diffractive_messages"])
    assert meta["sources"][0]["type"] == "nomadic"
    assert meta["sources"][0]["source_title"] == "Conv A"

