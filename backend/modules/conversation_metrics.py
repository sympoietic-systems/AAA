import logging

import numpy as np

from backend.skills.metadata import SkillMeta
from backend.storage.repository import MessageRepository

from .base import ProcessingModule

logger = logging.getLogger(__name__)

_DEFICIT_WEIGHTS = {
    "similarity": 0.30,
    "novelty": 0.25,
    "entropy": 0.20,
    "self_divergence": 0.25,
}


class ConversationMetricsModule(ProcessingModule):
    def __init__(
        self,
        message_repo: MessageRepository,
        pairwise_window: int = 5,
        entropy_window: int = 5,
        agent_self_window: int = 5,
    ):
        self._repo = message_repo
        self._pairwise_window = pairwise_window
        self._entropy_window = entropy_window
        self._agent_self_window = agent_self_window

    @property
    def name(self) -> str:
        return "conversation_metrics"

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="conversation_metrics",
            description="Computes real-time conversational vitality metrics",
            category="perception",
            always_run=True,
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        current_blob = payload.get("embedding")
        embedding_dim = payload.get("embedding_dim", 384)

        if not current_blob:
            payload["metrics"] = None
            payload["homeostatic_deficit"] = None
            return payload

        current_vec = np.frombuffer(current_blob, dtype="float32")

        prior_human = self._repo.get_embeddings_by_speaker(
            "human", limit=self._pairwise_window
        )
        prior_agent = self._repo.get_embeddings_by_speaker(
            "apparatus", limit=self._agent_self_window
        )

        metrics: dict = {}

        s_t = _compute_pairwise_similarity(current_vec, prior_human)
        metrics["pairwise_similarity"] = s_t

        novelty = _compute_conceptual_novelty(current_vec, prior_human)
        metrics["conceptual_novelty"] = novelty

        rolling_entropy = _compute_rolling_entropy(current_vec, prior_human, self._entropy_window)
        metrics["rolling_entropy"] = rolling_entropy

        coupling = _compute_coupling_coherence(self._repo)
        metrics["coupling_coherence"] = coupling

        agent_divergence = _compute_agent_self_divergence(prior_agent)
        metrics["agent_self_divergence"] = agent_divergence

        deficit = _compute_deficit(
            s_t=s_t,
            novelty=novelty,
            rolling_entropy=rolling_entropy,
            agent_divergence=agent_divergence,
        )
        metrics["homeostatic_deficit"] = deficit

        payload["metrics"] = metrics
        payload["homeostatic_deficit"] = deficit

        logger.debug(
            "metrics: S_t=%.3f N_t=%.3f E_t=%s C_t=%s D_t=%s \u0394=%.3f",
            s_t if s_t is not None else -1,
            novelty if novelty is not None else -1,
            f"{rolling_entropy:.4f}" if rolling_entropy is not None else "n/a",
            f"{coupling:.3f}" if coupling is not None else "n/a",
            f"{agent_divergence:.3f}" if agent_divergence is not None else "n/a",
            deficit if deficit is not None else -1,
        )

        return payload


def _compute_pairwise_similarity(
    current_vec: np.ndarray,
    prior_human: list[np.ndarray],
) -> float | None:
    if not prior_human:
        return None
    s_t = float(np.dot(current_vec, prior_human[0]))
    return max(0.0, min(1.0, s_t))


def _compute_conceptual_novelty(
    current_vec: np.ndarray,
    prior_human: list[np.ndarray],
) -> float | None:
    if not prior_human:
        return None
    sims = [float(np.dot(current_vec, v)) for v in prior_human]
    max_sim = max(sims)
    return max(0.0, 1.0 - max_sim)


def _compute_rolling_entropy(
    current_vec: np.ndarray,
    prior_human: list[np.ndarray],
    window: int,
) -> float | None:
    pairs = _build_similarity_pairs(current_vec, prior_human, window)
    if len(pairs) < 2:
        return None
    variance = float(np.var(pairs))
    return max(0.0, variance)


def _build_similarity_pairs(
    current_vec: np.ndarray,
    prior_human: list[np.ndarray],
    window: int,
) -> list[float]:
    pairs: list[float] = []
    vecs = [current_vec] + prior_human
    for i in range(min(len(vecs) - 1, window)):
        s = float(np.dot(vecs[i], vecs[i + 1]))
        pairs.append(max(0.0, min(1.0, s)))
    return pairs


def _compute_coupling_coherence(repo: MessageRepository) -> float | None:
    last_human = repo.get_last_embedding_by_speaker("human")
    last_agent = repo.get_last_embedding_by_speaker("apparatus")
    if last_human is None or last_agent is None:
        return None
    c = float(np.dot(last_human, last_agent))
    return max(0.0, min(1.0, c))


def _compute_agent_self_divergence(
    prior_agent: list[np.ndarray],
) -> float | None:
    if not prior_agent or len(prior_agent) < 2:
        return None
    latest = prior_agent[0]
    divergences = [1.0 - float(np.dot(latest, v)) for v in prior_agent[1:]]
    return float(np.mean(divergences))


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
