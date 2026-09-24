"""Typing support for cooperative dream-daemon collaborators."""

from typing import Any

DreamResult = dict[str, Any]


class DreamDaemonCollaborator:
    """Declare attributes supplied by the composed lifecycle owner."""

    dream_counter: int
    dream_action_counts: dict[str, int]
    last_dream_time: float
    last_reset_day: int
    last_dream_action: str | None

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(name)
