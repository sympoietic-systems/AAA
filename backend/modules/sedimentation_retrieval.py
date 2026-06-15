import logging
from datetime import datetime
from typing import Optional

import numpy as np

from backend.pipeline.metadata import ModuleMeta
from backend.storage.repository import MessageRepository, SemanticKnotRepository
from backend.utils.token_counter import estimate_message_tokens

from .base import ProcessingModule

logger = logging.getLogger(__name__)


def _format_relative_time(dt: datetime) -> str:
    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{int(seconds)}s ago"
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)}h ago"
    days = hours / 24
    if days < 30:
        return f"{int(days)}d ago"
    months = days / 30.4
    if months < 12:
        return f"{int(months)}mo ago"
    years = days / 365.25
    return f"{int(years)}y ago"


class SedimentationRetrievalModule(ProcessingModule):
    def __init__(
        self,
        message_repo: MessageRepository,
        sediment_token_budget: int = 2000,
        sediment_count: int = 10,
        similarity_threshold: float = 0.3,
        semantic_knot_repo: Optional[SemanticKnotRepository] = None,
        knot_warping_enabled: bool = True,
        knot_warping_weight: float = 1.0,
    ):
        self._repo = message_repo
        self._sediment_token_budget = sediment_token_budget
        self._sediment_count = sediment_count
        self._similarity_threshold = similarity_threshold
        self._semantic_knot_repo = semantic_knot_repo
        self._knot_warping_enabled = knot_warping_enabled
        self._knot_warping_weight = knot_warping_weight

    @property
    def name(self) -> str:
        return "sedimentation_retrieval"

    @property
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="sedimentation_retrieval",
            description="Retrieves semantically relevant messages from other conversations via embedding similarity",
            category="memory",
            always_run=True,
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        current_blob = payload.get("embedding")
        conversation_id = payload.get("conversation_id", "")

        if not current_blob or not conversation_id:
            payload["sediment_messages"] = []
            return payload

        current_vec = np.frombuffer(current_blob, dtype="float32")

        embeddings = self._repo.get_all_embeddings_except(
            exclude_conversation_id=conversation_id,
            limit=500,
        )

        if not embeddings:
            payload["sediment_messages"] = []
            return payload

        # S2: Load active semantic knots for gravitational warping
        knot_embeddings: list[tuple[float, np.ndarray]] = []
        if self._knot_warping_enabled and self._semantic_knot_repo:
            try:
                raw_knots = self._semantic_knot_repo.get_embeddings_and_signatures_except(
                    exclude_conversation_id=conversation_id, limit=100
                )
                for _knot_id, emb_vec, _sig_vec, _payload in raw_knots:
                    if emb_vec is not None and len(emb_vec) == len(current_vec):
                        # Fetch weight from repo (default to 0.5 if unavailable)
                        knot_embeddings.append((0.5, emb_vec))
            except Exception:
                pass

        scored: list[tuple[float, int]] = []
        for msg_id, _speaker, vec in embeddings:
            if len(vec) != len(current_vec):
                continue
            sim = float(np.dot(current_vec, vec))

            # S2: Add knot gravitational pull to the base similarity score
            if knot_embeddings:
                gravity_sum = 0.0
                for knot_weight, knot_vec in knot_embeddings:
                    dist_sq = float(np.sum((vec - knot_vec) ** 2))
                    gravity_sum += knot_weight * np.exp(-dist_sq)
                sim += self._knot_warping_weight * gravity_sum

            if sim >= self._similarity_threshold:
                scored.append((sim, msg_id))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_ids = [msg_id for _, msg_id in scored[:self._sediment_count]]

        if not top_ids:
            payload["sediment_messages"] = []
            return payload

        messages = self._repo.get_sediment_messages_with_metadata(top_ids)
        id_to_msg = {m["id"]: m for m in messages}

        sediment: list[dict] = []
        tokens_used = 0
        for _, msg_id in scored[:self._sediment_count]:
            msg = id_to_msg.get(msg_id)
            if msg is None:
                continue
            original_speaker = "apparatus" if msg["speaker"] == "apparatus" else "human"
            rel_time = _format_relative_time(msg["timestamp"])
            title = msg["conversation_title"]
            
            content_formatted = f'[Memory from "{title}" | {rel_time} | Speaker: {original_speaker} | msg: {msg["id"]} | conv: {msg["conversation_id"]}]:\n"{msg["content"]}"'
            
            entry = {"role": "system", "content": content_formatted}
            entry_tokens = estimate_message_tokens(entry)
            if tokens_used + entry_tokens > self._sediment_token_budget:
                break
            sediment.append(entry)
            tokens_used += entry_tokens

        payload["sediment_messages"] = sediment
        if sediment:
            logger.debug(
                "sediment: %d messages from other conversations, %d tokens",
                len(sediment),
                tokens_used,
            )

        return payload
