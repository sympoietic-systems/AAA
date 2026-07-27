"""Cybernetic Metrics Package.

# ponytail: clean package entrypoint re-exporting submodules
"""

from .health import (
    _compute_collapse_pressure,
    _compute_deficit,
    _compute_drr,
    _compute_paskian_health,
    _compute_vitality,
    _detect_phase_shifts,
)
from .kinematics import (
    _compute_conceptual_velocity,
    _compute_surprise_index,
)
from .resonance import (
    _compute_conceptual_novelty,
    _compute_pairwise_similarity,
    _compute_rolling_entropy,
)
from .trajectories import (
    _compute_agent_self_divergence,
    _compute_coupling_coherence,
    _compute_forward_perturbation,
    _compute_mutual_perturbation,
    _compute_reverse_perturbation,
)

__all__ = [
    "_compute_pairwise_similarity",
    "_compute_conceptual_novelty",
    "_compute_rolling_entropy",
    "_compute_coupling_coherence",
    "_compute_agent_self_divergence",
    "_compute_reverse_perturbation",
    "_compute_forward_perturbation",
    "_compute_mutual_perturbation",
    "_compute_surprise_index",
    "_compute_conceptual_velocity",
    "_compute_collapse_pressure",
    "_compute_drr",
    "_compute_paskian_health",
    "_compute_deficit",
    "_compute_vitality",
    "_detect_phase_shifts",
]
