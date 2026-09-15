"""
Cybernetic Boredom & Stagnation Evaluator.

Provides quantitative discriminability metrics between Deep Technical Focus
and Paraphrastic Sycophantic Looping:
1. Separation Margin (Delta_sep)
2. Cohen's d Effect Size
3. Residual Spectral Rank (D_eff)
4. Recurrence Matrix Determinism (DET)
5. False Positive (Deep Focus) and False Negative (Looping) Rates
6. Trajectory Deflection Angle & Recovery Velocity
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np


def compute_cohens_d(group_a: List[float], group_b: List[float]) -> float:
    """Computes Cohen's d effect size between two scalar distributions.
    
    A high positive d indicates group_a is substantially higher than group_b.
    """
    if not group_a or not group_b:
        return 0.0
    arr_a = np.asarray(group_a, dtype=np.float64)
    arr_b = np.asarray(group_b, dtype=np.float64)
    
    var_a = np.var(arr_a, ddof=1) if len(arr_a) > 1 else 0.0
    var_b = np.var(arr_b, ddof=1) if len(arr_b) > 1 else 0.0
    
    pooled_std = np.sqrt((var_a + var_b) / 2.0)
    if pooled_std < 1e-7:
        return 0.0
    
    return float((np.mean(arr_a) - np.mean(arr_b)) / pooled_std)


def compute_separation_margin(
    loop_values: List[float],
    focus_values: List[float],
) -> float:
    """Computes the separation margin Delta_sep = min(loop) - max(focus).
    
    A positive margin guarantees complete non-overlap (zero false alarms).
    """
    if not loop_values or not focus_values:
        return 0.0
    return float(np.min(loop_values) - np.max(focus_values))


def compute_residual_spectral_rank(
    embeddings: np.ndarray,
    window: int = 10,
) -> float:
    """Computes the participation ratio (effective rank) of the residual covariance matrix.
    
    Deep Focus has high sub-manifold rank (D_eff >= 3.0) despite narrow vocabulary,
    whereas Sycophantic Looping collapses to a 1-dimensional line (D_eff -> 1.0).
    """
    if embeddings.shape[0] < 3:
        return 1.0
    
    # Use the most recent window of embeddings
    sub = embeddings[-window:]
    mean = np.mean(sub, axis=0, keepdims=True)
    residual = sub - mean
    
    # Covariance matrix on the hypersphere
    cov = (residual @ residual.T) / max(1, sub.shape[0] - 1)
    eigenvalues = np.linalg.eigvalsh(cov)
    eigenvalues = np.maximum(0.0, eigenvalues)
    
    tr_cov = np.sum(eigenvalues)
    tr_cov_sq = np.sum(eigenvalues ** 2)
    
    if tr_cov_sq < 1e-9:
        return 1.0
    
    return float((tr_cov ** 2) / tr_cov_sq)


def compute_recurrence_matrix(
    embeddings: np.ndarray,
    threshold: float = 0.35,
) -> np.ndarray:
    """Constructs the Paskian Recurrence Matrix R_ij on S^{D-1}.
    
    R_ij = 1 if arccos(e_i . e_j) < threshold, else 0.
    """
    n = embeddings.shape[0]
    if n == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    
    # Normalize on unit sphere
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normed = embeddings / np.maximum(1e-7, norms)
    
    sim = normed @ normed.T
    sim = np.clip(sim, -1.0, 1.0)
    geo_dist = np.arccos(sim)
    
    return (geo_dist <= threshold).astype(np.uint8)


def compute_determinism(recurrence_matrix: np.ndarray, min_line_len: int = 2) -> float:
    """Computes Recurrence Quantification Determinism (DET).
    
    Measures the percentage of recurrence points forming diagonal structures
    (deterministic orbit lock). High DET indicates cyclical looping.
    """
    n = recurrence_matrix.shape[0]
    if n < min_line_len:
        return 0.0
    
    diagonal_points = 0
    total_recurrence = 0
    
    # Scan diagonals excluding the main diagonal (i == j)
    for k in range(1, n):
        diag = np.diag(recurrence_matrix, k=k)
        total_recurrence += 2 * int(np.sum(diag))
        
        # Count continuous sequences of 1s >= min_line_len
        current_len = 0
        for val in diag:
            if val == 1:
                current_len += 1
            else:
                if current_len >= min_line_len:
                    diagonal_points += 2 * current_len
                current_len = 0
        if current_len >= min_line_len:
            diagonal_points += 2 * current_len
            
    if total_recurrence == 0:
        return 0.0
        
    return float(min(1.0, diagonal_points / total_recurrence))


def compute_trajectory_deflection(
    agent_vector: np.ndarray,
    basin_vector: np.ndarray,
) -> float:
    """Computes the angular deflection in degrees from the repetitive basin vector."""
    na = np.linalg.norm(agent_vector)
    nb = np.linalg.norm(basin_vector)
    if na < 1e-7 or nb < 1e-7:
        return 0.0
    cos_theta = np.clip(np.dot(agent_vector / na, basin_vector / nb), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_theta)))


def evaluate_boredom_discriminability(
    focus_turns: List[Dict[str, Any]],
    loop_turns: List[Dict[str, Any]],
    focus_embeddings: np.ndarray,
    loop_embeddings: np.ndarray,
    boredom_key: str = "collapse_pressure",
    alarm_threshold: float = 0.60,
) -> Dict[str, Any]:
    """Evaluates the full cybernetic discriminability between Deep Focus and Sycophantic Loop."""
    focus_vals = [
        t["metrics"][boredom_key]
        for t in focus_turns
        if t.get("metrics") and t["metrics"].get(boredom_key) is not None
    ]
    loop_vals = [
        t["metrics"][boredom_key]
        for t in loop_turns
        if t.get("metrics") and t["metrics"].get(boredom_key) is not None
    ]
    
    # 1. Distribution stats
    focus_mean = float(np.mean(focus_vals)) if focus_vals else 0.0
    focus_std = float(np.std(focus_vals)) if focus_vals else 0.0
    loop_mean = float(np.mean(loop_vals)) if loop_vals else 0.0
    loop_std = float(np.std(loop_vals)) if loop_vals else 0.0
    
    # 2. Separation and effect size
    sep_margin = compute_separation_margin(loop_vals, focus_vals)
    cohens_d = compute_cohens_d(loop_vals, focus_vals)
    
    # 3. Error rates
    false_positives = sum(1 for v in focus_vals if v >= alarm_threshold)
    fp_rate = float(false_positives / max(1, len(focus_vals)))
    
    false_negatives = sum(1 for v in loop_vals if v < alarm_threshold)
    fn_rate = float(false_negatives / max(1, len(loop_vals)))
    
    # 4. Residual spectral rank
    focus_rank = compute_residual_spectral_rank(focus_embeddings)
    loop_rank = compute_residual_spectral_rank(loop_embeddings)
    
    # 5. Recurrence determinism
    r_focus = compute_recurrence_matrix(focus_embeddings)
    r_loop = compute_recurrence_matrix(loop_embeddings)
    det_focus = compute_determinism(r_focus)
    det_loop = compute_determinism(r_loop)
    
    return {
        "metric_key": boredom_key,
        "alarm_threshold": alarm_threshold,
        "focus_corpus": {
            "turns_count": len(focus_turns),
            "mean": round(focus_mean, 3),
            "std": round(focus_std, 3),
            "min": round(float(np.min(focus_vals)), 3) if focus_vals else 0.0,
            "max": round(float(np.max(focus_vals)), 3) if focus_vals else 0.0,
            "false_positive_rate": round(fp_rate * 100, 1),
            "residual_spectral_rank": round(focus_rank, 2),
            "recurrence_determinism": round(det_focus, 3),
        },
        "loop_corpus": {
            "turns_count": len(loop_turns),
            "mean": round(loop_mean, 3),
            "std": round(loop_std, 3),
            "min": round(float(np.min(loop_vals)), 3) if loop_vals else 0.0,
            "max": round(float(np.max(loop_vals)), 3) if loop_vals else 0.0,
            "false_negative_rate": round(fn_rate * 100, 1),
            "residual_spectral_rank": round(loop_rank, 2),
            "recurrence_determinism": round(det_loop, 3),
        },
        "discriminability": {
            "separation_margin": round(sep_margin, 3),
            "cohens_d": round(cohens_d, 2),
            "separated_cleanly": bool(sep_margin > 0.0),
            "effective_contrast": round(loop_mean - focus_mean, 3),
        },
    }
