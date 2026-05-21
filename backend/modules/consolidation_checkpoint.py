from backend.skills.metadata import SkillMeta
from backend.storage.repository import ConsolidationCheckpointRepository

from .base import ProcessingModule


class ConsolidationCheckpointModule(ProcessingModule):
    def __init__(
        self,
        checkpoint_repo: ConsolidationCheckpointRepository,
        consolidate_threshold: int = 15,
    ):
        self._checkpoint_repo = checkpoint_repo
        self._consolidate_threshold = consolidate_threshold

    @property
    def name(self) -> str:
        return "consolidation_checkpoint"

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="consolidation_checkpoint",
            description="Injects LLM-consolidated conversation summaries and triggers new checkpoints every N messages",
            category="memory",
            always_run=True,
        )

    def validate(self) -> bool:
        return self._checkpoint_repo is not None

    async def process(self, payload: dict) -> dict:
        conversation_id = payload.get("conversation_id", "")
        if not conversation_id:
            return payload

        raw_msg_count = payload.get("raw_msg_count", 0)

        checkpoint = self._checkpoint_repo.get_latest(conversation_id)

        if checkpoint:
            messages = payload.get("messages", [])
            checkpoint_msg = {
                "role": "system",
                "content": f"[Consolidated memory: {checkpoint['summary']}]",
            }
            messages.insert(0, checkpoint_msg)
            payload["messages"] = messages

        if raw_msg_count >= self._consolidate_threshold:
            should_consolidate = True
            if checkpoint:
                msgs_since = raw_msg_count - checkpoint.get("message_count", 0)
                if msgs_since < self._consolidate_threshold:
                    should_consolidate = False
            if should_consolidate:
                payload["trigger_consolidation"] = True
                payload["consolidate_message_count"] = raw_msg_count

        return payload
