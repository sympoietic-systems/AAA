from backend.skills.metadata import SkillMeta
from backend.storage.repository import MessageRepository
from backend.utils.token_counter import caveman_compress

from .base import ProcessingModule


class ContextCollectorModule(ProcessingModule):
    def __init__(
        self,
        message_repo: MessageRepository,
        max_history: int = 20,
        floating_window: int = 8,
        caveman_enabled: bool = True,
    ):
        self._repo = message_repo
        self._max_history = max_history
        self._floating_window = floating_window
        self._caveman_enabled = caveman_enabled

    @property
    def name(self) -> str:
        return "context_collector"

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="context_collector",
            description="Gathers conversation history with tiered compression (raw floating window, caveman-compressed older messages)",
            category="memory",
            always_run=True,
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        conversation_id = payload.get("conversation_id", "")
        raw_msgs = self._repo.get_recent(
            limit=self._max_history,
            conversation_id=conversation_id if conversation_id else None,
        )

        messages: list[dict] = []

        total = len(raw_msgs)
        for i, row in enumerate(raw_msgs):
            position_from_end = total - 1 - i
            role = "assistant" if row.speaker == "apparatus" else "user"

            if position_from_end < self._floating_window:
                content = row.content
            elif self._caveman_enabled:
                content = f"[{role[0].upper()}]: {caveman_compress(row.content)}"
            else:
                content = row.content

            messages.append({"role": role, "content": content})

        current = payload.get("content", "")
        if current:
            messages.append({"role": "user", "content": current})

        payload["messages"] = messages
        payload["raw_msg_count"] = total

        return payload
