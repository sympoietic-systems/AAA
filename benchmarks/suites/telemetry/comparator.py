"""
Differential analysis for cybernetic telemetry benchmarking runs.
Isolates, ranks, and categorizes 'metrics that changed' between two evaluations.
"""

from dataclasses import dataclass
from typing import Any, Dict, List
import numpy as np

from .evaluator import METRIC_KEYS


@dataclass
class MetricDelta:
    key: str
    label: str
    mean_a: float
    mean_b: float
    delta: float
    abs_delta: float
    pct_change: float
    std_a: float
    std_b: float
    category: str  # 'significant', 'moderate', 'stable'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "mean_a": self.mean_a,
            "mean_b": self.mean_b,
            "delta": self.delta,
            "abs_delta": self.abs_delta,
            "pct_change": self.pct_change,
            "std_a": self.std_a,
            "std_b": self.std_b,
            "category": self.category,
        }


METRIC_PRETTY_LABELS = {
    "pairwise_similarity": "Pairwise Similarity (s_t)",
    "conceptual_novelty": "Conceptual Novelty (N_t)",
    "rolling_entropy": "Rolling Spectral Entropy (H_ent)",
    "coupling_coherence": "Coupling Coherence (C_t)",
    "agent_self_divergence": "Agent Self-Divergence (D_self)",
    "reverse_perturbation": "Reverse Perturbation (rP_t)",
    "forward_perturbation": "Forward Perturbation (fP_t)",
    "mutual_perturbation": "Mutual Perturbation (MPI)",
    "surprise_index": "Predictive Surprise (S_t)",
    "collapse_pressure": "Collapse Pressure (CP_t)",
    "conceptual_velocity": "Conceptual Velocity (v_t)",
    "phase_transition_magnitude": "Phase Transition Mag (M_pt)",
    "divergence_resolution_ratio": "Divergence Resolution Ratio (DRR)",
    "paskian_health": "Gordon Pask Health (H_pask)",
    "deficit": "Conversational Deficit (D_t)",
    "vitality": "Conversational Vitality (V_t)",
}


def compare_runs(
    turns_a: List[Dict[str, Any]],
    turns_b: List[Dict[str, Any]],
    delta_threshold: float = 0.05,
) -> Dict[str, Any]:
    """
    Compare two evaluated runs turn-by-turn and summarize metric deltas.
    Returns:
      - 'deltas': list[MetricDelta] sorted by abs_delta descending
      - 'changed_metrics': list[MetricDelta] exceeding delta_threshold
      - 'stable_metrics': list[MetricDelta] below threshold
    """
    deltas: List[MetricDelta] = []

    for key in METRIC_KEYS:
        vals_a = [t["metrics"].get(key) for t in turns_a if t["metrics"].get(key) is not None]
        vals_b = [t["metrics"].get(key) for t in turns_b if t["metrics"].get(key) is not None]

        if not vals_a and not vals_b:
            continue

        mean_a = float(np.mean(vals_a)) if vals_a else 0.0
        mean_b = float(np.mean(vals_b)) if vals_b else 0.0
        std_a = float(np.std(vals_a)) if vals_a else 0.0
        std_b = float(np.std(vals_b)) if vals_b else 0.0

        d = mean_b - mean_a
        abs_d = abs(d)
        pct = (d / (mean_a + 1e-6)) * 100.0

        if abs_d >= delta_threshold:
            cat = "significant"
        elif abs_d >= 0.02:
            cat = "moderate"
        else:
            cat = "stable"

        deltas.append(
            MetricDelta(
                key=key,
                label=METRIC_PRETTY_LABELS.get(key, key),
                mean_a=round(mean_a, 4),
                mean_b=round(mean_b, 4),
                delta=round(d, 4),
                abs_delta=round(abs_d, 4),
                pct_change=round(pct, 2),
                std_a=round(std_a, 4),
                std_b=round(std_b, 4),
                category=cat,
            )
        )

    # Sort primarily by abs_delta descending
    deltas.sort(key=lambda item: item.abs_delta, reverse=True)

    changed = [d for d in deltas if d.category == "significant"]
    moderate = [d for d in deltas if d.category == "moderate"]
    stable = [d for d in deltas if d.category == "stable"]

    return {
        "all_deltas": deltas,
        "changed_metrics": changed,
        "moderate_metrics": moderate,
        "stable_metrics": stable,
        "top_changed_keys": [d.key for d in changed] if changed else [d.key for d in deltas[:4]],
    }
