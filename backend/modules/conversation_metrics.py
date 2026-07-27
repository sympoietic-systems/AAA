import logging

import numpy as np

from backend.pipeline.metadata import ModuleMeta
from backend.storage.repository import MessageRepository

from .base import ProcessingModule

logger = logging.getLogger(__name__)

_DEFICIT_WEIGHTS = {
    "similarity": 0.30,
    "novelty": 0.25,
    "entropy": 0.20,
    "self_divergence": 0.25,
}

_VITALITY_WEIGHTS = {
    "novelty": 0.30,
    "entropy": 0.20,
    "self_divergence": 0.20,
    "reverse_perturbation": 0.15,
    "surprise": 0.15,
}


class ConversationMetricsModule(ProcessingModule):
    def __init__(
        self,
        message_repo: MessageRepository,
        pairwise_window: int = 5,
        entropy_window: int = 5,
        agent_self_window: int = 5,
        phase_shift_threshold: float = 0.35,
    ):
        self._repo = message_repo
        self._pairwise_window = pairwise_window
        self._entropy_window = entropy_window
        self._agent_self_window = agent_self_window
        self._phase_shift_threshold = phase_shift_threshold
        self._prior_metrics: dict[str, float | None] = {}
        self._prior_centroid: np.ndarray | None = None

    @property
    def name(self) -> str:
        return "conversation_metrics"

    @property
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="conversation_metrics",
            description="Computes real-time conversational vitality and paskian metrics",
            category="perception",
            always_run=True,
            children=[
                ModuleMeta(
                    name="surprise_index",
                    description="Exponentially decaying weighted surprise (d=0.75)",
                    category="perception",
                ),
                ModuleMeta(
                    name="boringness",
                    description="Joint failure of mutual perturbation: (1 - rP_t) * (1 - MPI_{t-1})",
                    category="perception",
                ),
                ModuleMeta(
                    name="conceptual_velocity",
                    description="Disjoint window centroid drift rate (k=3)",
                    category="perception",
                ),
            ],
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        current_blob = payload.get("embedding")
        conversation_id = payload.get("conversation_id", "")
        exclude_message_id = payload.get("exclude_message_id")

        if not current_blob:
            payload["metrics"] = None
            payload["conversation_vitality"] = None
            payload["homeostatic_deficit"] = None
            return payload

        current_vec = np.frombuffer(current_blob, dtype="float32")

        ancestor_message_ids = payload.get("ancestor_message_ids", [])
        if ancestor_message_ids:
            ancestor_msgs = self._repo.get_by_ids(ancestor_message_ids)
            ancestor_msgs.sort(key=lambda m: m.id if m.id is not None else 0)
        else:
            parent_message_id = payload.get("parent_message_id")
            if parent_message_id is None and conversation_id:
                last_msgs = self._repo.get_recent(limit=1, conversation_id=conversation_id)
                if last_msgs:
                    parent_message_id = last_msgs[0].id
            if parent_message_id is not None:
                ancestor_msgs = self._repo.get_ancestor_path(parent_message_id, limit=50)
            else:
                ancestor_msgs = []

        if exclude_message_id is not None:
            ancestor_msgs = [m for m in ancestor_msgs if m.id != exclude_message_id]

        prior_human_msgs = [m for m in reversed(ancestor_msgs) if m.speaker == "human"]
        prior_agent_msgs = [m for m in reversed(ancestor_msgs) if m.speaker == "apparatus"]

        prior_human = []
        for m in prior_human_msgs[: self._pairwise_window]:
            if m.embedding and m.embedding_dim:
                vec = np.frombuffer(m.embedding, dtype="float32")
                if len(vec) == m.embedding_dim:
                    prior_human.append(vec)

        prior_agent = []
        for m in prior_agent_msgs[: self._agent_self_window]:
            if m.embedding and m.embedding_dim:
                vec = np.frombuffer(m.embedding, dtype="float32")
                if len(vec) == m.embedding_dim:
                    prior_agent.append(vec)

        all_recent = []
        for m in reversed(ancestor_msgs):
            if m.embedding and m.embedding_dim:
                vec = np.frombuffer(m.embedding, dtype="float32")
                if len(vec) == m.embedding_dim:
                    all_recent.append(vec)
        recent_history = []
        for m in reversed(ancestor_msgs[:10]):
            if m.embedding and m.embedding_dim:
                vec = np.frombuffer(m.embedding, dtype="float32")
                if len(vec) == m.embedding_dim:
                    speaker = "human" if m.speaker == "human" else "apparatus"
                    recent_history.append({"embedding": vec, "speaker": speaker})

        current_speaker = payload.get("speaker", "apparatus")

        metrics: dict = {}

        s_t = _compute_pairwise_similarity(current_vec, current_speaker, recent_history)
        metrics["pairwise_similarity"] = s_t

        novelty, new_centroid = _compute_conceptual_novelty(
            current_vec, recent_history, self._prior_centroid
        )
        self._prior_centroid = new_centroid
        metrics["conceptual_novelty"] = novelty

        rolling_entropy = _compute_rolling_entropy(current_vec, recent_history, window=8)
        metrics["rolling_entropy"] = rolling_entropy

        coupling = _compute_coupling_coherence(recent_history, window=8)
        metrics["coupling_coherence"] = coupling

        agent_divergence = _compute_agent_self_divergence(
            current_vec, current_speaker, prior_agent
        )
        metrics["agent_self_divergence"] = agent_divergence

        rp_t = _compute_reverse_perturbation(current_vec, prior_agent)
        metrics["reverse_perturbation"] = rp_t

        surprise = _compute_surprise_index(current_vec, prior_human)
        metrics["surprise_index"] = surprise

        mpi = _compute_mutual_perturbation(coupling, rp_t)
        metrics["mutual_perturbation"] = mpi

        prior_metrics = {}
        path_ids = [m.id for m in ancestor_msgs if m.id is not None]
        if path_ids:
            recent_with_metrics = self._repo.get_recent_with_metrics_for_path(
                path_ids, limit=5, exclude_message_id=exclude_message_id
            )
            if recent_with_metrics:
                for turn in reversed(recent_with_metrics):
                    if turn.get("s_t") is not None:
                        prior_metrics = {
                            "pairwise_similarity": turn.get("s_t"),
                            "conceptual_novelty": turn.get("novelty"),
                            "rolling_entropy": turn.get("rolling_entropy"),
                            "coupling_coherence": turn.get("coupling"),
                            "agent_self_divergence": turn.get("agent_divergence"),
                            "reverse_perturbation": turn.get("reverse_perturbation"),
                            "surprise_index": turn.get("surprise_index"),
                            "mutual_perturbation": turn.get("mutual_perturbation"),
                        }
                        break

        # Fall back to in-memory self._prior_metrics if DB returned nothing
        if not prior_metrics:
            prior_metrics = self._prior_metrics

        prev_mpi = prior_metrics.get("mutual_perturbation")
        collapse_pressure = _compute_collapse_pressure(rp_t, prev_mpi, rolling_entropy, novelty)
        metrics["collapse_pressure"] = collapse_pressure
        metrics["boringness"] = collapse_pressure  # ponytail: backward compatibility alias for boringness

        conceptual_velocity = _compute_conceptual_velocity(current_vec, all_recent)
        metrics["conceptual_velocity"] = conceptual_velocity

        prev_coupling = prior_metrics.get("coupling_coherence")
        prev_rp = prior_metrics.get("reverse_perturbation")
        drr = _compute_drr(coupling, prev_coupling, prev_rp)
        metrics["divergence_resolution_ratio"] = drr

        pask_health = _compute_paskian_health(collapse_pressure, conceptual_velocity, drr)
        metrics["paskian_health"] = pask_health

        deficit = _compute_deficit(
            s_t=s_t,
            novelty=novelty,
            rolling_entropy=rolling_entropy,
            agent_divergence=agent_divergence,
        )
        metrics["homeostatic_deficit"] = deficit

        vitality = _compute_vitality(
            novelty=novelty,
            rolling_entropy=rolling_entropy,
            agent_divergence=agent_divergence,
            reverse_perturbation=rp_t,
            surprise=surprise,
        )
        metrics["conversation_vitality"] = vitality

        phase_shifts = _detect_phase_shifts(metrics, prior_metrics, self._phase_shift_threshold)
        metrics["phase_shifts"] = phase_shifts

        # ponytail: compute diffractive Glitch Fidelity across 16D signature & 384D embedding space
        from backend.modules.glitch_fidelity_engine import compute_glitch_fidelity, select_diffractive_prior

        curr_sig = payload.get("vector_16d") or payload.get("structural_vector_16d") or current_vec[:16]
        cand_list = []
        for m in ancestor_msgs[:10]:
            if m.embedding and m.embedding_dim:
                m_emb = np.frombuffer(m.embedding, dtype="float32")
                m_sig = m.vector_16d if hasattr(m, "vector_16d") and m.vector_16d else m_emb[:16]
                cand_list.append({"signature": m_sig, "embedding": m_emb})

        prior_cand = select_diffractive_prior(curr_sig, current_vec, cand_list)
        if prior_cand:
            gf = compute_glitch_fidelity(
                curr_sig, current_vec, prior_cand["signature"], prior_cand["embedding"]
            )
        else:
            gf = 0.85

        metrics["glitch_fidelity"] = gf
        payload["glitch_fidelity"] = gf

        self._prior_metrics = {
            "pairwise_similarity": s_t,
            "conceptual_novelty": novelty,
            "rolling_entropy": rolling_entropy,
            "coupling_coherence": coupling,
            "agent_self_divergence": agent_divergence,
            "reverse_perturbation": rp_t,
            "surprise_index": surprise,
            "mutual_perturbation": mpi,
        }

        payload["metrics"] = metrics
        payload["conversation_vitality"] = vitality
        payload["homeostatic_deficit"] = deficit

        logger.debug(
            "metrics: sim=%.3f nov=%.3f ent=%s coup=%s divr=%s rP=%s srp=%s mpi=%s bore=%s vel=%s drr=%s ph=%s vit=%s \u0394=%.3f shifts=%s",
            _fmt(s_t),
            _fmt(novelty),
            _fmt4(rolling_entropy),
            _fmt(coupling),
            _fmt(agent_divergence),
            _fmt(rp_t),
            _fmt(surprise),
            _fmt(mpi),
            _fmt(collapse_pressure),
            _fmt(conceptual_velocity),
            _fmt(drr),
            _fmt(pask_health),
            _fmt(vitality),
            deficit if deficit is not None else -1,
            phase_shifts,
        )

        return payload


def _fmt(v: float | None) -> str:
    return f"{v:.3f}" if v is not None else "n/a"


def _fmt4(v: float | None) -> str:
    return f"{v:.4f}" if v is not None else "n/a"


def _compute_pairwise_similarity(
    current_vec: np.ndarray,
    current_speaker: str,
    recent_history: list[dict],
    decay_lambda: float = 0.15,
) -> float | None:
    """# ponytail: compute reciprocal perturbation coherence with exponential decay and speaker weighting."""
    if not recent_history:
        return None

    sims = []
    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    for i, item in enumerate(recent_history):
        v = item.get("embedding")
        if v is None:
            continue
        v_norm = np.linalg.norm(v)
        v_vec = v / v_norm if v_norm > 0 else v

        dot_sim = float(np.dot(c_vec, v_vec))
        cos_sim = max(0.0, min(1.0, dot_sim))

        speaker = item.get("speaker", "human")
        speaker_factor = 0.8 if speaker == current_speaker else 1.2
        decay = float(np.exp(-decay_lambda * i))

        sims.append(cos_sim * decay * speaker_factor)

    if not sims:
        return None

    weighted_sim = float(np.mean(sims))
    return max(0.0, min(1.0, weighted_sim))


def _compute_conceptual_novelty(
    current_vec: np.ndarray,
    recent_history: list[dict],
    prior_centroid: np.ndarray | None = None,
    alpha: float = 0.3,
) -> tuple[float | None, np.ndarray]:
    """# ponytail: compute sediment drift magnitude from context centroid and scatter."""
    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    if not recent_history:
        return None, c_vec

    hist_vecs = []
    for item in recent_history:
        v = item.get("embedding")
        if v is not None:
            norm = np.linalg.norm(v)
            hist_vecs.append(v / norm if norm > 0 else v)

    if not hist_vecs:
        return None, c_vec

    # Update context centroid EMA
    if prior_centroid is None:
        new_centroid = c_vec
    else:
        new_centroid = (alpha * c_vec) + ((1.0 - alpha) * prior_centroid)
        norm_cent = np.linalg.norm(new_centroid)
        if norm_cent > 0:
            new_centroid = new_centroid / norm_cent

    # Compute raw drift distance from centroid
    drift_raw = 1.0 - max(0.0, min(1.0, float(np.dot(c_vec, new_centroid))))

    # Compute scatter standard deviation across history turns relative to centroid
    scatters = [1.0 - max(0.0, min(1.0, float(np.dot(hv, new_centroid)))) for hv in hist_vecs]
    sigma_context = float(np.std(scatters)) if len(scatters) > 1 else 0.10

    # Normalized drift distance
    drift_norm = float(np.tanh(drift_raw / (sigma_context + 0.01)))

    # Compute velocity relative to prior history turn drift
    prior_drift = scatters[0] if scatters else 0.01
    velocity = min(1.0, abs(drift_raw - prior_drift) / max(0.01, prior_drift))

    # Combined novelty score (0.7 drift + 0.3 velocity)
    novelty = (0.7 * drift_norm) + (0.3 * velocity)
    novelty = max(0.0, min(1.0, float(novelty)))

    return round(novelty, 3), new_centroid


def _compute_rolling_entropy(
    current_vec: np.ndarray,
    recent_history: list[dict],
    window: int = 8,
    eps_reg: float = 1e-8,
) -> float | None:
    """# ponytail: compute manifold spectral entropy from embedding Gram matrix eigendecomposition."""
    if not recent_history:
        return 0.5

    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    hist_vecs = [c_vec]
    for item in recent_history[: window - 1]:
        v = item.get("embedding")
        if v is not None:
            norm = np.linalg.norm(v)
            hist_vecs.append(v / norm if norm > 0 else v)

    K = len(hist_vecs)
    if K < 2:
        return 0.5

    # Center matrix E (K x D)
    E = np.stack(hist_vecs)
    mu_E = np.mean(E, axis=0)
    E_centered = E - mu_E

    # Gram matrix C' = (1/K) * E_centered * E_centered^T (K x K)
    gram = (1.0 / K) * np.dot(E_centered, E_centered.T)
    gram_trace = float(np.trace(gram))

    if gram_trace < 1e-6:
        return 0.0

    try:
        eigvals = np.linalg.eigvalsh(gram)
        eigvals = np.maximum(eigvals, eps_reg)
        p = eigvals / np.sum(eigvals)
        h_raw = float(-np.sum(p * np.log(p)))
        max_h = float(np.log(K))
        entropy = h_raw / max_h if max_h > 0 else 0.5
        return round(max(0.0, min(1.0, float(entropy))), 4)
    except Exception:
        return 0.5


def _compute_coupling_coherence(
    recent_history: list[dict],
    window: int = 8,
    decay_lambda: float = 0.2,
) -> float | None:
    """# ponytail: compute trajectory cross-correlation between human and apparatus displacement vectors."""
    human_vecs = []
    agent_vecs = []
    for item in recent_history:
        v = item.get("embedding")
        if v is None:
            continue
        norm = np.linalg.norm(v)
        v_norm = v / norm if norm > 0 else v
        if item.get("speaker") == "human":
            human_vecs.append(v_norm)
        else:
            agent_vecs.append(v_norm)

    if len(human_vecs) < 2 or len(agent_vecs) < 2:
        return 0.5

    h_disps = [human_vecs[i] - human_vecs[i + 1] for i in range(len(human_vecs) - 1)]
    a_disps = [agent_vecs[i] - agent_vecs[i + 1] for i in range(len(agent_vecs) - 1)]

    min_len = min(len(h_disps), len(a_disps), window)
    if min_len == 0:
        return 0.5

    weighted_corrs = []
    weights = []
    for i in range(min_len):
        hd = h_disps[i]
        ad = a_disps[i]
        hd_n = np.linalg.norm(hd)
        ad_n = np.linalg.norm(ad)
        if hd_n > 0 and ad_n > 0:
            cos_disp = float(abs(np.dot(hd / hd_n, ad / ad_n)))
        else:
            cos_disp = 0.5
        w = float(np.exp(-decay_lambda * i))
        weighted_corrs.append(cos_disp * w)
        weights.append(w)

    if not weights or sum(weights) == 0:
        return 0.5

    score = sum(weighted_corrs) / sum(weights)
    return round(max(0.0, min(1.0, float(score))), 3)


def _compute_agent_self_divergence(
    current_vec: np.ndarray,
    current_speaker: str,
    prior_agent: list[np.ndarray],
    max_recent_window: int = 15,
    beta: float = 0.3,
) -> float | None:
    """# ponytail: compute agent self-divergence via recency-decayed max self-similarity and repeat penalty."""
    if not prior_agent:
        return 0.5

    c_norm = np.linalg.norm(current_vec)
    c_vec = current_vec / c_norm if c_norm > 0 else current_vec

    agent_norms = []
    for v in prior_agent:
        norm = np.linalg.norm(v)
        agent_norms.append(v / norm if norm > 0 else v)

    s_self_scores = []
    for i, v in enumerate(agent_norms[:max_recent_window]):
        cos_sim = max(0.0, min(1.0, float(np.dot(c_vec, v))))
        w = float(np.exp(-beta * i))
        s_self_scores.append(cos_sim * w)

    s_self = max(s_self_scores) if s_self_scores else 0.0

    penalty = 0.0
    if len(agent_norms) > max_recent_window:
        long_sims = [float(np.dot(c_vec, v)) for v in agent_norms[max_recent_window:]]
        max_long = max(long_sims) if long_sims else 0.0
        if max_long > 0.95:
            penalty = 0.3 * (max_long - 0.95) / 0.05

    divergence = 1.0 - s_self - penalty
    return round(max(0.0, min(1.0, float(divergence))), 3)


def _compute_reverse_perturbation(
    current_vec: np.ndarray,
    prior_agent: list[np.ndarray],
) -> float | None:
    """rP_t: did the agent's last response reshape the human's next question?

    rP_t = 1 - cos(agent_response_{t-1}, human_input_t)
    High rP_t = human diverged from prior agent response → agent perturbed or human resisted.
    Low rP_t = human echoed the agent → no perturbation in the reverse direction.
    """
    if not prior_agent:
        return None
    agent_last_vec = prior_agent[0]
    rp = 1.0 - float(np.dot(current_vec, agent_last_vec))
    return max(0.0, min(1.0, rp))


def _compute_surprise_index(
    current_vec: np.ndarray,
    prior_human: list[np.ndarray],
) -> float | None:
    """U_t: distance from current input to centroid of recent human inputs.

    U_t = 1 - cos(V_t, centroid(V_{t-1}..V_{t-K}))
    High U_t = input falls outside system's expected phase space.
    Uses exponential decay weighting (d=0.75) for temporal active coupling.
    """
    if not prior_human or len(prior_human) < 2:
        return None
    d = 0.75
    weights = np.array([d**i for i in range(len(prior_human))])
    stacked = np.stack(prior_human)
    weighted_sum = np.sum(stacked * weights[:, np.newaxis], axis=0)
    sum_weights = np.sum(weights)
    centroid = weighted_sum / sum_weights
    centroid = centroid / (np.linalg.norm(centroid) + 1e-8)
    u = 1.0 - float(np.dot(current_vec, centroid))
    return max(0.0, min(1.0, u))


def _compute_mutual_perturbation(
    coupling: float | None,
    reverse_perturbation: float | None,
) -> float | None:
    """MPI: product of forward and reverse coupling.

    MPI_t = coupling_{t-1} × rP_t
    High MPI = both directions active: agent tracked human AND human was reshaped.
    Low MPI = echo chamber or dissociation.
    """
    if coupling is None or reverse_perturbation is None:
        return None
    return max(0.0, min(1.0, coupling * reverse_perturbation))


def _compute_deficit(
    s_t: float | None,
    novelty: float | None,
    rolling_entropy: float | None,
    agent_divergence: float | None,
) -> float | None:
    if s_t is None or novelty is None:
        return None

    ws = _DEFICIT_WEIGHTS["similarity"]
    wn = _DEFICIT_WEIGHTS["novelty"]
    we = _DEFICIT_WEIGHTS["entropy"]
    wd = _DEFICIT_WEIGHTS["self_divergence"]

    deficit = ws * s_t + wn * (1.0 - novelty)

    if rolling_entropy is not None:
        entropy_norm = min(1.0, rolling_entropy / 0.25)
        deficit += we * (1.0 - entropy_norm)

    if agent_divergence is not None:
        deficit += wd * (1.0 - agent_divergence)
    else:
        deficit *= 1.0 / (ws + wn)

    return max(0.0, min(1.0, deficit))


def _compute_vitality(
    novelty: float | None,
    rolling_entropy: float | None,
    agent_divergence: float | None,
    reverse_perturbation: float | None,
    surprise: float | None,
) -> float | None:
    """Vitality: how alive is this conversation right now?

    Higher = more alive. Unlike deficit (where 0 = healthy),
    vitality is 1 = maximally alive, 0 = dead.
    """
    if novelty is None:
        return None

    wn = _VITALITY_WEIGHTS["novelty"]
    we = _VITALITY_WEIGHTS["entropy"]
    wd = _VITALITY_WEIGHTS["self_divergence"]
    wr = _VITALITY_WEIGHTS["reverse_perturbation"]
    ws = _VITALITY_WEIGHTS["surprise"]

    score = wn * novelty

    if rolling_entropy is not None:
        entropy_norm = min(1.0, rolling_entropy / 0.25)
        score += we * entropy_norm

    if agent_divergence is not None:
        score += wd * agent_divergence

    if reverse_perturbation is not None:
        score += wr * reverse_perturbation

    if surprise is not None:
        score += ws * surprise

    used_weight = wn
    if rolling_entropy is not None:
        used_weight += we
    if agent_divergence is not None:
        used_weight += wd
    if reverse_perturbation is not None:
        used_weight += wr
    if surprise is not None:
        used_weight += ws

    score /= used_weight
    return max(0.0, min(1.0, score))


def _detect_phase_shifts(
    current: dict,
    prior: dict,
    threshold: float,
) -> list[dict]:
    """Detect abrupt metric changes that indicate reframing events.

    A phase shift occurs when a metric changes by more than `threshold`
    between turns. This captures Symbia's concept of "repetition as
    reframing" — where an apparently repetitive turn is actually a
    meta-novel probe that shifts the conversational topology.
    """
    shifts: list[dict] = []

    for key, label in [
        ("pairwise_similarity", "similarity_jump"),
        ("conceptual_novelty", "novelty_collapse"),
        ("reverse_perturbation", "perturbation_surge"),
        ("surprise_index", "surprise_spike"),
    ]:
        cur = current.get(key)
        prev = prior.get(key)
        if cur is not None and prev is not None:
            delta = abs(cur - prev)
            if delta > threshold:
                direction = "rise" if cur > prev else "drop"
                shifts.append(
                    {
                        "metric": key,
                        "event": label,
                        "delta": round(delta, 4),
                        "direction": direction,
                        "from": round(prev, 4),
                        "to": round(cur, 4),
                    }
                )

    return shifts


def _compute_collapse_pressure(
    rp_t: float | None,
    prev_mpi: float | None,
    rolling_entropy: float | None,
    conceptual_novelty: float | None,
) -> float | None:
    """# ponytail: compute triadic collapse pressure index (renamed from boringness)."""
    if rp_t is None:
        return None

    rp_val = float(rp_t)
    mpi_val = prev_mpi if prev_mpi is not None else 0.5
    entropy_val = rolling_entropy if rolling_entropy is not None else 0.5
    novelty_val = conceptual_novelty if conceptual_novelty is not None else 0.5

    pert_geom_mean = float(np.sqrt(max(0.0, rp_val * mpi_val)))
    pert_failure = 1.0 - pert_geom_mean

    collapse = pert_failure * (1.0 - entropy_val) * (1.0 - novelty_val)
    return round(max(0.0, min(1.0, float(collapse))), 3)


def _compute_conceptual_velocity(
    current_vec: np.ndarray,
    all_recent: list[np.ndarray],
) -> float | None:
    """V_c = 1 - cos(W_prev, W_curr)

    Uses non-overlapping windows of size k=3 (current + last 2 vs. preceding 3).
    """
    if len(all_recent) < 5:
        return None
    curr_window = [current_vec] + all_recent[:2]
    curr_centroid = np.mean(np.stack(curr_window), axis=0)
    curr_centroid = curr_centroid / (np.linalg.norm(curr_centroid) + 1e-8)

    prev_window = all_recent[2:5]
    prev_centroid = np.mean(np.stack(prev_window), axis=0)
    prev_centroid = prev_centroid / (np.linalg.norm(prev_centroid) + 1e-8)

    v = 1.0 - float(np.dot(prev_centroid, curr_centroid))
    return max(0.0, min(1.0, v))


def _compute_drr(
    coupling: float | None,
    prev_coupling: float | None,
    prev_rp: float | None,
) -> float | None:
    """DRR_t = (coupling_t - coupling_{t-1}) / max(rP_{t-1}, 0.01)

    Does the agent's perturbation lead to resolution or rejection?
    Positive DRR → perturbation caused convergence (productive disagreement resolved).
    Negative DRR → perturbation pushed them apart (rejection, too-aggressive cut).
    Near-zero DRR → perturbation was absorbed without structural change (boring).
    """
    if coupling is None or prev_coupling is None or prev_rp is None:
        return None
    if prev_rp < 0.02:
        return 0.0
    drr = (coupling - prev_coupling) / prev_rp
    return max(-1.0, min(1.0, drr))


def _compute_paskian_health(
    boringness: float | None,
    conceptual_velocity: float | None,
    drr: float | None,
) -> float | None:
    """Paskian health: how well does the conversation maintain the productive
    zone between strict convergence and permissive noise?

    Pask_health = (1 - B_t) × V_c_norm × (1 - |DRR_t - DRR_optimal|)

    Where DRR_optimal ≈ 0.15 (slight positive convergence, not instant agreement).
    High Pask_health → conversation is in the productive disagreement zone.
    """
    if boringness is None or conceptual_velocity is None or drr is None:
        return None

    drr_optimal = 0.15
    anti_boring = 1.0 - boringness
    v_norm = min(1.0, conceptual_velocity / 0.35)
    drr_quality = 1.0 - min(1.0, abs(drr - drr_optimal) / 0.5)

    ph = anti_boring * v_norm * drr_quality
    return max(0.0, min(1.0, ph))
