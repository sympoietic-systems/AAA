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


STOP_WORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "that", "which",
    "who", "whom", "this", "these", "those", "it", "its", "to", "of",
    "in", "for", "on", "with", "at", "by", "from", "as", "or", "and",
    "but", "if", "so", "no", "not", "just", "very", "really", "quite",
    "then", "now", "here", "there", "also", "some", "any", "all", "each",
    "what", "when", "where", "how", "why",
})


def caveman_compress(text: str, max_chars: int = 250) -> str:
    if not text:
        return ""
    words = text.split()
    if len(words) <= 8:
        return text
    compressed = [w for w in words if w.lower() not in STOP_WORDS]
    result = " ".join(compressed)
    # Character truncation removed (R1): stop-word filtering alone provides
    # ~50% token reduction. Downstream token budgets at the sedimentation
    # (4000 tokens) and diffractive (6000 tokens) layers handle capping.
    return result
