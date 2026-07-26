import uuid
import numpy as np
import pytest
from unittest.mock import MagicMock
from datetime import datetime, UTC

from backend.modules.sedimentation_retrieval import SedimentationRetrievalModule
from backend.modules.context_collector import ContextCollectorModule


@pytest.mark.asyncio
async def test_context_collector_detects_grating():
    message_repo = MagicMock()
    note_repo = MagicMock()
    note_repo.get_notes_by_conversation.return_value = []

    collector = ContextCollectorModule(
        message_repo=message_repo,
        note_repo=note_repo,
    )

    payload = {
        "conversation_id": "conv-123",
        "content": "GRATING: Please reflect on our theoretical framework.",
    }
    message_repo.get_recent.return_value = []

    res = await collector.process(payload)
    assert res.get("grating_requested") is True


@pytest.mark.asyncio
async def test_sedimentation_retrieval_grating_protocol():
    message_repo = MagicMock()

    # Vector 1: current conversation (unit vector [1, 0, 0])
    vec_current = np.array([1.0, 0.0, 0.0], dtype="float32")

    # Vector 2: low similarity candidate ([0.3, 0.95, 0.0], dot product = 0.30)
    vec_low = np.array([0.3, 0.95, 0.0], dtype="float32")

    # Vector 3: high similarity candidate ([0.9, 0.43, 0.0], dot product = 0.90)
    vec_high = np.array([0.9, 0.43, 0.0], dtype="float32")

    message_repo.get_all_embeddings_except.return_value = [
        (101, "human", vec_low),
        (102, "apparatus", vec_high),
    ]

    message_repo.get_sediment_messages_with_metadata.return_value = [
        {
            "id": 101,
            "speaker": "human",
            "conversation_title": "Old Plateau Dialogue",
            "timestamp": datetime.now(UTC),
            "conversation_id": "conv-old",
            "content": "Dissonant memory regarding Indigenous epistemologies.",
        }
    ]

    module = SedimentationRetrievalModule(
        message_repo=message_repo,
        sediment_token_budget=1000,
        similarity_threshold=0.3,
    )

    payload = {
        "embedding": vec_current.tobytes(),
        "conversation_id": "conv-current",
        "grating_requested": True,
    }

    res = await module.process(payload)

    assert res.get("grating_applied") is True
    assert len(res["sediment_messages"]) == 1
    content = res["sediment_messages"][0]["content"]
    assert "[GRATING SEDIMENT INJECTION — IMMUNE PERTURBATION]" in content
    assert "Dissonant memory regarding Indigenous epistemologies." in content
    assert "PROTOCOL MANDATE: You MUST include this quoted chunk verbatim" in content
