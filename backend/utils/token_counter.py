from dataclasses import dataclass, field


@dataclass
class TokenBudget:
    max_tokens: int
    used: dict[str, int] = field(default_factory=dict)
    _remaining: int | None = None

    def allocate(self, category: str, tokens: int) -> None:
        self.used[category] = tokens

    @property
    def total_used(self) -> int:
        return sum(self.used.values())

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.total_used)

    def can_fit(self, tokens: int) -> bool:
        return self.total_used + tokens <= self.max_tokens


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_message_tokens(message: dict) -> int:
    content = message.get("content", "")
    role = message.get("role", "")
    return estimate_tokens(role) + estimate_tokens(content) + 4


def estimate_messages_tokens(messages: list[dict]) -> int:
    return sum(estimate_message_tokens(m) for m in messages)
