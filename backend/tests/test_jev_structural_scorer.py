"""Unit tests for JevStructuralScorer and confidence metrics."""

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from backend.modules.structural_engine import (
    CYBERNETIC_DIMENSIONS,
    CompositeStructuralScorer,
    JevStructuralScorer,
)


@pytest.mark.asyncio
async def test_jev_structural_scorer_questions_builder():
    """Verify all 16 cybernetic dimensions are populated with Score questions."""
    scorer = JevStructuralScorer()
    questions = scorer._build_questions()

    assert len(questions) == 16
    for i, (dim_slug, dim_title, _) in enumerate(CYBERNETIC_DIMENSIONS):
        q_id = f"dim_{i:02d}_{dim_slug}"
        assert q_id in questions
        q = questions[q_id]
        assert q["type"] == "score"
        assert len(q["criteria"]) == 4
        assert dim_title in q["instructions"]


@pytest.mark.asyncio
async def test_jev_structural_scorer_evaluation_success():
    """Verify evaluation parses 16 scores and confidences into np.ndarrays."""
    mock_client = MagicMock()
    mock_client.is_configured = True

    # Construct mock answers
    answers = {}
    for i, (dim_slug, _, _) in enumerate(CYBERNETIC_DIMENSIONS):
        q_id = f"dim_{i:02d}_{dim_slug}"
        answers[q_id] = {
            "score": round((i % 4) / 3.0, 2),
            "confidence": 0.85 + (i * 0.005),
        }

    mock_client.evaluate = AsyncMock(
        return_value={
            "success": True,
            "answers": answers,
        }
    )

    scorer = JevStructuralScorer(client=mock_client)
    power, conf = await scorer.score_with_confidence_async("Autopoietic recursive closed membrane feedback.")

    assert isinstance(power, np.ndarray)
    assert isinstance(conf, np.ndarray)
    assert len(power) == 16
    assert len(conf) == 16

    # Verify normalization bounds
    assert np.all(power >= 0.0) and np.all(power <= 1.0)
    assert np.all(conf >= 0.0) and np.all(conf <= 1.0)

    # Verify score_async returns just power
    power_only = await scorer.score_async("Autopoietic recursive closed membrane feedback.")
    np.testing.assert_array_almost_equal(power, power_only)


@pytest.mark.asyncio
async def test_jev_structural_scorer_unconfigured_fallback():
    """Verify unconfigured client falls back to 0.25 power and 0.50 confidence."""
    scorer = JevStructuralScorer(client=None)
    power, conf = await scorer.score_with_confidence_async("Test text")

    assert len(power) == 16
    assert np.all(power == 0.25)
    assert len(conf) == 16
    assert np.all(conf == 0.50)


@pytest.mark.asyncio
async def test_composite_scorer_with_jev():
    """Verify CompositeStructuralScorer incorporates Jev when configured."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    answers = {
        f"dim_{i:02d}_{dim_slug}": {"score": 0.8, "confidence": 0.9}
        for i, (dim_slug, _, _) in enumerate(CYBERNETIC_DIMENSIONS)
    }
    mock_client.evaluate = AsyncMock(
        return_value={
            "success": True,
            "answers": answers,
        }
    )

    composite = CompositeStructuralScorer(
        jev_client=mock_client,
        w_ling=0.25,
        w_topo=0.25,
        w_llm=0.0,
        w_jev=0.50,
    )

    sig = await composite.score_async("Decentralized peer-to-peer meshwork feedback loops.")
    assert isinstance(sig, np.ndarray)
    assert len(sig) == 16
    assert np.all(sig >= 0.0) and np.all(sig <= 1.0)
