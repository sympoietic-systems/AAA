import numpy as np
import pytest
from backend.modules.glitch_fidelity_engine import (
    compute_glitch_fidelity,
    compute_interference_variance,
    select_diffractive_prior,
)


def test_compute_interference_variance_boundaries():
    # 1. Identical flat signatures -> flat elementwise product -> zero variance
    sig_flat = [0.25] * 16
    var_flat = compute_interference_variance(sig_flat, sig_flat)
    assert var_flat == 0.0

    # 2. Rich diffractive signature pair -> half aligned, half zero
    sig1 = [0.25] * 8 + [0.0] * 8
    sig2 = [0.25] * 8 + [0.0] * 8
    var_rich = compute_interference_variance(sig1, sig2)
    assert var_rich > 0.5, f"Expected high normalized variance, got {var_rich}"

    # 3. Embedding relevance scaling
    emb1 = np.ones(384, dtype=np.float32)
    emb2 = np.ones(384, dtype=np.float32)
    var_with_emb = compute_interference_variance(sig1, sig2, emb1, emb2)
    assert var_with_emb > 0.5


def test_select_diffractive_prior_goldilocks_zone():
    current_sig = [0.25] * 16

    # Candidate A: Too similar (affinity > 0.7) -> 1.0 structural similarity
    cand_similar = {"id": 1, "signature": [0.25] * 16}

    # Candidate B: Goldilocks zone (affinity = 0.5) -> 4 entries non-zero
    cand_goldilocks = {"id": 2, "signature": [0.25] * 4 + [0.0] * 12}

    # Candidate C: Disjoint (affinity < 0.3) -> orthogonal
    cand_disjoint = {"id": 3, "signature": [0.0] * 8 + [0.25] * 8}

    selected = select_diffractive_prior(
        current_sig, None, [cand_similar, cand_goldilocks, cand_disjoint]
    )
    assert selected is not None
    assert selected["id"] == 2, f"Expected Goldilocks candidate ID 2, got {selected['id']}"


def test_compute_glitch_fidelity_combined():
    sig1 = [0.25] * 8 + [0.0] * 8
    sig2 = [0.25] * 8 + [0.0] * 8

    fidelity = compute_glitch_fidelity(
        current_signature=sig1,
        current_embedding=None,
        prior_signature=sig2,
        prior_embedding=None,
        contradiction_density=0.4,
    )
    assert 0.0 <= fidelity <= 1.0
    assert fidelity > 0.5, f"Expected high combined glitch fidelity, got {fidelity}"
