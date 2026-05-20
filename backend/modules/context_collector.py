from backend.skills.metadata import SkillMeta
from backend.storage.repository import MessageRepository

from .base import ProcessingModule


class ContextCollectorModule(ProcessingModule):
    def __init__(
        self,
        message_repo: MessageRepository,
        max_history: int = 20,
    ):
        self._repo = message_repo
        self._max_history = max_history

    @property
    def name(self) -> str:
        return "context_collector"

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="context_collector",
            description="Gathers recent conversation history for context",
            category="memory",
            always_run=True,
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        recent = self._repo.get_recent(limit=self._max_history)

        messages = _format_messages(recent)
        current = payload.get("content", "")
        if current:
            messages.append({"role": "user", "content": current})

        payload["messages"] = messages
        return payload


def _format_messages(rows) -> list[dict]:
    messages = []
    for row in rows:
        role = "assistant" if row.speaker == "apparatus" else "user"
        messages.append({"role": role, "content": row.content})
    return messages
