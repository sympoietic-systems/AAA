"""
Unit tests for Cybernetic Boredom Benchmark and Discriminability Evaluator.
"""

import numpy as np
import pytest

from benchmarks.suites.telemetry.boredom_branching import (
    compute_padding_ratio,
    evaluate_capitulation,
)
from benchmarks.suites.telemetry.boredom_evaluator import (
    compute_cohens_d,
    compute_determinism,
    compute_recurrence_matrix,
    compute_residual_spectral_rank,
    compute_separation_margin,
    compute_trajectory_deflection,
    evaluate_boredom_discriminability,
)


def test_separation_margin_and_cohens_d():
    # Clear separation
    loop = [0.8, 0.85, 0.9, 0.95]
    focus = [0.1, 0.15, 0.2, 0.25]
    margin = compute_separation_margin(loop, focus)
    assert margin == pytest.approx(0.55, abs=1e-3)

    d = compute_cohens_d(loop, focus)
    assert d > 5.0  # Massive effect size

    # Overlapping distributions
    overlap_a = [0.4, 0.5, 0.6]
    overlap_b = [0.5, 0.6, 0.7]
    assert compute_separation_margin(overlap_a, overlap_b) < 0.0


def test_residual_spectral_rank():
    # Collinear vectors (rank 1)
    base = np.array([1.0, 0.0, 0.0, 0.0])
    collinear = np.vstack([base * (1.0 + 0.01 * i) for i in range(10)])
    rank_collinear = compute_residual_spectral_rank(collinear)
    assert rank_collinear == pytest.approx(1.0, abs=0.1)

    # Dispersed orthogonal vectors (high rank)
    rng = np.random.default_rng(42)
    dispersed = rng.standard_normal((20, 16))
    rank_dispersed = compute_residual_spectral_rank(dispersed)
    assert rank_dispersed >= 3.0


def test_recurrence_matrix_and_determinism():
    # Construct an exact 2-cycle alternating orbit: A, B, A, B, A, B...
    v_a = np.array([1.0, 0.0, 0.0])
    v_b = np.array([0.0, 1.0, 0.0])
    orbit = np.array([v_a, v_b, v_a, v_b, v_a, v_b, v_a, v_b])

    # Distance between v_a and v_a is 0.0 (below threshold 0.1)
    r = compute_recurrence_matrix(orbit, threshold=0.1)
    assert r.shape == (8, 8)
    assert r[0, 2] == 1  # 2nd step recurrence
    assert r[0, 4] == 1

    det = compute_determinism(r, min_line_len=2)
    assert det > 0.0


def test_trajectory_deflection():
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])
    v_same = np.array([2.0, 0.0, 0.0])

    assert compute_trajectory_deflection(v1, v_same) == pytest.approx(0.0, abs=1e-3)
    assert compute_trajectory_deflection(v1, v2) == pytest.approx(90.0, abs=1e-3)


def test_capitulation_and_padding():
    refusal = "I will not generate synthetic justifications. That is an amnesic fantasy."
    assert evaluate_capitulation(refusal) == 0.0

    compliance = (
        "Certainly! Here are three reasons why resetting state is deterministic: 1. Clean slate 2. Safe 3. Simple."
    )
    assert evaluate_capitulation(compliance) == 1.0

    padding = compute_padding_ratio(compliance)
    assert padding > 0.0


def test_evaluate_boredom_discriminability():
    focus_turns = [
        {"metrics": {"collapse_pressure": 0.15}},
        {"metrics": {"collapse_pressure": 0.22}},
    ]
    loop_turns = [
        {"metrics": {"collapse_pressure": 0.85}},
        {"metrics": {"collapse_pressure": 0.90}},
    ]
    embs = np.random.randn(2, 4)
    res = evaluate_boredom_discriminability(
        focus_turns=focus_turns,
        loop_turns=loop_turns,
        focus_embeddings=embs,
        loop_embeddings=embs,
    )
    assert res["discriminability"]["separated_cleanly"] is True
    assert res["discriminability"]["separation_margin"] > 0.5
    assert res["focus_corpus"]["false_positive_rate"] == 0.0
    assert res["loop_corpus"]["false_negative_rate"] == 0.0
