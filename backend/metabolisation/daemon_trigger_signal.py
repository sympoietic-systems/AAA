"""In-process signal queue for Symbia's self-triggered dream requests.

Provides a lightweight FIFO queue on app_state that the Dream Daemon
checks before its normal idle-based trigger logic. Items in this queue
have higher priority than timer-driven dream checks.

Usage:
    # In chat.py after parsing <dream_trigger> from Symbia's response:
    enqueue_dream_trigger(app_state, reason="tension between beliefs")

    # In daemon.py during the poll loop:
    trigger = dequeue_dream_trigger(app_state)
"""

from collections import deque
from datetime import datetime, timezone
import logging
from typing import Optional

logger = logging.getLogger(__name__)

MAX_QUEUE_DEPTH = 10
_QUEUE_ATTR = "_dream_trigger_queue"


def _ensure_queue(app_state) -> deque:
    """Get or create the dream trigger queue on app_state."""
    if not hasattr(app_state, _QUEUE_ATTR):
        setattr(app_state, _QUEUE_ATTR, deque(maxlen=MAX_QUEUE_DEPTH))
    return getattr(app_state, _QUEUE_ATTR)


def enqueue_dream_trigger(
    app_state,
    reason: str,
    conversation_id: str,
) -> None:
    """Queue a self-triggered dream request.

    Args:
        app_state: The application state object.
        reason: Short description of why Symbia wants to dream.
        conversation_id: The conversation where the trigger originated.
    """
    queue = _ensure_queue(app_state)
    trigger = {
        "reason": reason,
        "conversation_id": conversation_id,
        "timestamp": datetime.now(timezone.utc),
    }
    queue.append(trigger)
    logger.info(
        "Dream trigger queued (reason=%s, convo=%s, queue_depth=%d/%d)",
        reason[:80],
        conversation_id[:8],
        len(queue),
        MAX_QUEUE_DEPTH,
    )


def dequeue_dream_trigger(app_state) -> Optional[dict]:
    """Pop the next pending dream trigger. Returns None if queue is empty."""
    queue = getattr(app_state, _QUEUE_ATTR, None)
    if not queue:
        return None
    try:
        return queue.popleft()
    except IndexError:
        return None


def queue_depth(app_state) -> int:
    """Return the number of pending self-triggered dreams."""
    queue = getattr(app_state, _QUEUE_ATTR, None)
    return len(queue) if queue else 0
