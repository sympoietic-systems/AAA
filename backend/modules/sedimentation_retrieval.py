import logging
from datetime import datetime

import numpy as np

from backend.skills.metadata import SkillMeta
from backend.storage.repository import MessageRepository
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
    ):
        self._repo = message_repo
        self._sediment_token_budget = sediment_token_budget
        self._sediment_count = sediment_count
        self._similarity_threshold = similarity_threshold

    @property
    def name(self) -> str:
        return "sedimentation_retrieval"

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
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

        scored: list[tuple[float, int]] = []
        for msg_id, _speaker, vec in embeddings:
            sim = float(np.dot(current_vec, vec))
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
