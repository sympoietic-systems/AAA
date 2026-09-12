"""
Cybernetic telemetry evaluator: computes all 14 calibrated metric dimensions,
homeostatic regimes, phase shift events, and long-horizon quartile progressions.
"""

from typing import Any, Dict, List, Optional
import numpy as np

from backend.modules.conversation_metrics import (
    _compute_agent_self_divergence,
    _compute_collapse_pressure,
    _compute_conceptual_novelty,
    _compute_conceptual_velocity,
    _compute_coupling_coherence,
    _compute_deficit,
    _compute_drr,
    _compute_forward_perturbation,
    _compute_mutual_perturbation,
    _compute_paskian_health,
    _compute_pairwise_similarity,
    _compute_reverse_perturbation,
    _compute_rolling_entropy,
    _compute_surprise_index,
    _compute_vitality,
    _detect_phase_shifts,
)

METRIC_KEYS = [
    "pairwise_similarity",
    "conceptual_novelty",
    "rolling_entropy",
    "coupling_coherence",
    "agent_self_divergence",
    "reverse_perturbation",
    "forward_perturbation",
    "mutual_perturbation",
    "surprise_index",
    "collapse_pressure",
    "conceptual_velocity",
    "phase_transition_magnitude",
    "divergence_resolution_ratio",
    "paskian_health",
    "deficit",
    "vitality",
]


def evaluate_sequence(messages: List[Dict[str, Any]], embeddings: np.ndarray, phase_threshold: float = 0.35) -> List[Dict[str, Any]]:
    """
    Evaluate all 14 cybernetic metrics turn-by-turn across a chronological message sequence.
    """
    results: List[Dict[str, Any]] = []
    recent_history: List[Dict[str, Any]] = []  # sliding window up to 20 turns
    prior_centroid: Optional[np.ndarray] = None
    prior_metrics: Dict[str, Any] = {}

    for i, msg in enumerate(messages):
        msg_id = msg.get("id", i + 1)
        speaker = msg.get("speaker", "human")
        current_speaker = "apparatus" if speaker in ("apparatus", "agent") else "human"
        current_vec = embeddings[i]

        prior_human = [h["embedding"] for h in recent_history if h["speaker"] == "human"]
        prior_agent = [h["embedding"] for h in recent_history if h["speaker"] != "human"]
        all_recent = [h["embedding"] for h in recent_history]

        turn_metrics: Dict[str, Any] = {}

        # 1. Pairwise Similarity
        s_t = _compute_pairwise_similarity(current_vec, current_speaker, recent_history)
        turn_metrics["pairwise_similarity"] = s_t
        turn_metrics["s_t"] = s_t

        # 2. Conceptual Novelty
        novelty, new_centroid = _compute_conceptual_novelty(
            current_vec, recent_history, prior_centroid=prior_centroid
        )
        turn_metrics["conceptual_novelty"] = novelty
        prior_centroid = new_centroid

        # 3. Rolling Spectral Entropy
        rolling_entropy = _compute_rolling_entropy(current_vec, recent_history)
        turn_metrics["rolling_entropy"] = rolling_entropy

        # 4. Trajectory Coupling Coherence
        coupling = _compute_coupling_coherence(recent_history)
        turn_metrics["coupling_coherence"] = coupling

        # 5. Agent Self-Divergence
        if current_speaker == "apparatus":
            agent_divergence = _compute_agent_self_divergence(
                current_vec, current_speaker, prior_agent
            )
        else:
            agent_divergence = prior_metrics.get("agent_self_divergence")
        turn_metrics["agent_self_divergence"] = agent_divergence

        # 6. Directional Perturbation (rP / fP)
        rp_t = None
        fp_t = None
        if current_speaker == "human":
            rp_t = _compute_reverse_perturbation(current_vec, prior_human, prior_agent)
            turn_metrics["reverse_perturbation"] = rp_t
            turn_metrics["forward_perturbation"] = prior_metrics.get("forward_perturbation")
        else:
            fp_t = _compute_forward_perturbation(current_vec, prior_human, prior_agent)
            turn_metrics["forward_perturbation"] = fp_t
            turn_metrics["reverse_perturbation"] = prior_metrics.get("reverse_perturbation")

        # 7. Mutual Perturbation Index
        mpi = _compute_mutual_perturbation(
            rp_t or turn_metrics.get("reverse_perturbation"),
            fp_t or turn_metrics.get("forward_perturbation"),
        )
        turn_metrics["mutual_perturbation"] = mpi

        # 8. Predictive Residual Trend Surprise
        surprise = _compute_surprise_index(current_vec, all_recent)
        turn_metrics["surprise_index"] = surprise

        # 9. Collapse Pressure / Boringness
        prev_mpi = prior_metrics.get("mutual_perturbation")
        collapse_pressure = _compute_collapse_pressure(rp_t, prev_mpi, rolling_entropy, novelty)
        turn_metrics["collapse_pressure"] = collapse_pressure
        turn_metrics["boringness"] = collapse_pressure

        # 10. Conceptual Velocity & Phase Transition Magnitude
        conceptual_velocity, phase_trans = _compute_conceptual_velocity(current_vec, all_recent)
        turn_metrics["conceptual_velocity"] = conceptual_velocity
        turn_metrics["phase_transition_magnitude"] = phase_trans

        # 11. Divergence Resolution Ratio
        drr = _compute_drr(recent_history, window=10)
        turn_metrics["divergence_resolution_ratio"] = drr

        # 12. Paskian Cybernetic Health
        pask_health = _compute_paskian_health(
            agent_self_divergence=agent_divergence,
            conceptual_velocity=conceptual_velocity,
            phase_transition_magnitude=phase_trans,
            coupling_coherence=coupling,
            mutual_perturbation=mpi,
            collapse_pressure=collapse_pressure,
            rolling_entropy=rolling_entropy,
            drr=drr,
        )
        turn_metrics["paskian_health"] = pask_health

        # 13. Conversational Deficit
        deficit = _compute_deficit(
            s_t=s_t,
            novelty=novelty,
            rolling_entropy=rolling_entropy,
            agent_divergence=agent_divergence,
        )
        turn_metrics["deficit"] = deficit

        # 14. Conversational Vitality
        vitality = _compute_vitality(
            novelty=novelty,
            rolling_entropy=rolling_entropy,
            agent_divergence=agent_divergence,
            reverse_perturbation=turn_metrics.get("reverse_perturbation"),
            surprise=surprise,
        )
        turn_metrics["vitality"] = vitality

        # 15. Homeostatic State Regime
        homeostatic_state = "flowing"
        if collapse_pressure is not None and collapse_pressure > 0.65:
            homeostatic_state = "stagnant"
        elif phase_trans is not None and phase_trans > 0.75:
            homeostatic_state = "disrupted"
        turn_metrics["homeostatic_state"] = homeostatic_state

        phase_shifts = _detect_phase_shifts(
            current=turn_metrics, prior=prior_metrics, threshold=phase_threshold
        )

        record = {
            "turn_index": i + 1,
            "id": msg_id,
            "parent_message_id": msg.get("parent_message_id"),
            "speaker": speaker,
            "timestamp": msg.get("timestamp"),
            "content_snippet": msg.get("content", "")[:120],
            "metrics": turn_metrics,
            "phase_shifts": phase_shifts,
        }
        results.append(record)

        # Update sliding history
        recent_history.append({
            "id": msg_id,
            "speaker": current_speaker,
            "embedding": current_vec,
        })
        if len(recent_history) > 20:
            recent_history.pop(0)

        prior_metrics = turn_metrics

    return results


def compute_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute distribution statistics across all turn metrics."""
    stats: Dict[str, Any] = {}
    for key in METRIC_KEYS:
        vals = [r["metrics"][key] for r in results if r["metrics"].get(key) is not None]
        if vals:
            stats[key] = {
                "count": len(vals),
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "min": float(np.min(vals)),
                "p25": float(np.percentile(vals, 25)),
                "median": float(np.median(vals)),
                "p75": float(np.percentile(vals, 75)),
                "max": float(np.max(vals)),
            }
        else:
            stats[key] = None

    regimes = [r["metrics"].get("homeostatic_state", "flowing") for r in results]
    tot = max(1, len(regimes))
    stats["regimes"] = {
        "flowing": regimes.count("flowing"),
        "flowing_pct": round(regimes.count("flowing") / tot * 100, 2),
        "stagnant": regimes.count("stagnant"),
        "stagnant_pct": round(regimes.count("stagnant") / tot * 100, 2),
        "disrupted": regimes.count("disrupted"),
        "disrupted_pct": round(regimes.count("disrupted") / tot * 100, 2),
    }

    shifts = [s for r in results for s in r.get("phase_shifts", [])]
    stats["total_phase_shifts"] = len(shifts)
    return stats
