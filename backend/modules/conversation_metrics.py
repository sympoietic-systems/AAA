import logging

import numpy as np

from backend.modules.metrics import (
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
from backend.pipeline.metadata import ModuleMeta
from backend.storage.repository import MessageRepository

from .base import ProcessingModule

logger = logging.getLogger(__name__)

# Re-export metric functions for backward compatibility with existing tests and imports
__all__ = [
    "ConversationMetricsModule",
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


class ConversationMetricsModule(ProcessingModule):
    """# ponytail: pipeline facade delegating to backend.modules.metrics submodules."""

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
            name=self.name,
            description="Computes cybernetic metrics (Glitch Fidelity, Spectral Entropy, Perturbation, Paskian Health) over embedding trajectories.",
        )

    def validate(self, payload: dict | None = None) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        current_msg = payload.get("current_message", {})
        msg_id = current_msg.get("id")
        conversation_id = current_msg.get("conversation_id") or payload.get("conversation_id")
        current_speaker = current_msg.get("speaker", "human")
        current_vec = payload.get("embeddings", {}).get("dense")

        if current_vec is None and "embedding" in payload:
            raw_emb = payload["embedding"]
            if isinstance(raw_emb, bytes):
                current_vec = np.frombuffer(raw_emb, dtype=np.float32)
            elif raw_emb is not None:
                current_vec = np.asarray(raw_emb, dtype=np.float32)

        if current_vec is None:
            logger.warning(
                "No dense embedding found in payload for message %s; skipping metrics",
                msg_id,
            )
            return payload

        if hasattr(self._repo, "get_history"):
            history_rows = self._repo.get_history(conversation_id, limit=20)
        elif hasattr(self._repo, "get_recent"):
            history_rows = self._repo.get_recent(limit=20, conversation_id=conversation_id)
        else:
            history_rows = []

        recent_history = []
        for row in history_rows:
            row_id = getattr(row, "id", None)
            if row_id == msg_id:
                continue
            emb = None
            if hasattr(self._repo, "get_dense_embedding") and row_id is not None:
                emb = self._repo.get_dense_embedding(row_id)
            elif hasattr(row, "embedding") and row.embedding is not None:
                raw_e = row.embedding
                if isinstance(raw_e, bytes):
                    emb = np.frombuffer(raw_e, dtype=np.float32)
                else:
                    emb = np.asarray(raw_e, dtype=np.float32)

            if emb is not None:
                recent_history.append(
                    {
                        "id": row_id,
                        "speaker": getattr(row, "speaker", "human"),
                        "embedding": emb,
                    }
                )

        prior_metrics = {}
        if hasattr(self._repo, "get_metrics"):
            prior_metrics = self._repo.get_metrics(conversation_id, limit=1) or {}

        prior_human = [
            h["embedding"] for h in recent_history if h["speaker"] == "human"
        ]
        prior_agent = [
            h["embedding"] for h in recent_history if h["speaker"] != "human"
        ]
        all_recent = [h["embedding"] for h in recent_history]

        metrics: dict[str, float | None] = {}

        s_t = _compute_pairwise_similarity(
            current_vec, current_speaker, recent_history
        )
        metrics["s_t"] = s_t
        metrics["pairwise_similarity"] = s_t

        novelty, new_centroid = _compute_conceptual_novelty(
            current_vec, recent_history, prior_centroid=self._prior_centroid
        )
        metrics["conceptual_novelty"] = novelty
        self._prior_centroid = new_centroid

        rolling_entropy = _compute_rolling_entropy(current_vec, recent_history)
        metrics["rolling_entropy"] = rolling_entropy

        coupling = _compute_coupling_coherence(recent_history)
        metrics["coupling_coherence"] = coupling

        agent_divergence = _compute_agent_self_divergence(
            current_vec, current_speaker, prior_agent
        )
        metrics["agent_self_divergence"] = agent_divergence

        rp_t = None
        fp_t = None
        if current_speaker == "human":
            rp_t = _compute_reverse_perturbation(
                current_vec, prior_human, prior_agent
            )
            metrics["reverse_perturbation"] = rp_t
            metrics["forward_perturbation"] = prior_metrics.get(
                "forward_perturbation"
            )
        else:
            fp_t = _compute_forward_perturbation(
                current_vec, prior_human, prior_agent
            )
            metrics["forward_perturbation"] = fp_t
            metrics["reverse_perturbation"] = prior_metrics.get(
                "reverse_perturbation"
            )

        mpi = _compute_mutual_perturbation(
            rp_t or metrics.get("reverse_perturbation"),
            fp_t or metrics.get("forward_perturbation"),
        )
        metrics["mutual_perturbation"] = mpi

        surprise = _compute_surprise_index(current_vec, all_recent)
        metrics["surprise_index"] = surprise

        prev_mpi = prior_metrics.get("mutual_perturbation")
        collapse_pressure = _compute_collapse_pressure(
            rp_t, prev_mpi, rolling_entropy, novelty
        )
        metrics["collapse_pressure"] = collapse_pressure
        metrics["boringness"] = (
            collapse_pressure  # ponytail: backward compatibility alias
        )

        conceptual_velocity, phase_trans = _compute_conceptual_velocity(
            current_vec, all_recent
        )
        metrics["conceptual_velocity"] = conceptual_velocity
        metrics["phase_transition_magnitude"] = phase_trans

        drr = _compute_drr(recent_history, window=10)
        metrics["divergence_resolution_ratio"] = drr

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
        metrics["paskian_health"] = pask_health

        deficit = _compute_deficit(
            s_t=s_t,
            novelty=novelty,
            rolling_entropy=rolling_entropy,
            agent_divergence=agent_divergence,
        )
        metrics["deficit"] = deficit

        vitality = _compute_vitality(
            novelty=novelty,
            rolling_entropy=rolling_entropy,
            agent_divergence=agent_divergence,
            reverse_perturbation=metrics.get("reverse_perturbation"),
            surprise=surprise,
        )
        metrics["vitality"] = vitality

        homeostatic_state = "flowing"
        if collapse_pressure is not None and collapse_pressure > 0.65:
            homeostatic_state = "stagnant"
        elif phase_trans is not None and phase_trans > 0.75:
            homeostatic_state = "disrupted"
        metrics["homeostatic_state"] = homeostatic_state

        phase_shifts = _detect_phase_shifts(
            current=metrics,
            prior=prior_metrics,
            threshold=self._phase_shift_threshold,
        )

        if msg_id is not None:
            self._repo.save_metrics(msg_id, metrics)

        self._prior_metrics = metrics

        payload["metrics"] = metrics
        payload["phase_shifts"] = phase_shifts

        logger.info(
            "Metrics for msg %s [%s]: s_t=%s, novelty=%s, entropy=%s, coupling=%s, div=%s, rP=%s, fP=%s, MPI=%s, surprise=%s, V_c=%s, collapse=%s, DRR=%s, Pask=%s, vitality=%s, deficit=%s | %d phase shift(s)",
            msg_id,
            homeostatic_state,
            _fmt(s_t),
            _fmt(novelty),
            _fmt4(rolling_entropy),
            _fmt(coupling),
            _fmt(agent_divergence),
            _fmt(metrics.get("reverse_perturbation")),
            _fmt(metrics.get("forward_perturbation")),
            _fmt(mpi),
            _fmt(surprise),
            _fmt(conceptual_velocity),
            _fmt(collapse_pressure),
            _fmt(drr),
            _fmt(pask_health),
            _fmt(vitality),
            deficit if deficit is not None else -1,
            len(phase_shifts),
        )

        return payload


def _fmt(v: float | None) -> str:
    return f"{v:.3f}" if v is not None else "n/a"


def _fmt4(v: float | None) -> str:
    return f"{v:.4f}" if v is not None else "n/a"
