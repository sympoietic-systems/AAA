"""Parse <dream_trigger reason="..."/> tags from Symbia's responses.

Symbia can emit these to request an immediate dream cycle when she detects
unresolved tension or diffractive patterns that need metabolic processing.
The tag is stripped from the visible response and routed to the daemon's
dream trigger queue.

Tag format:
    <dream_trigger reason="tension between beliefs X and Y needs resolution"/>
"""

import logging
import re

logger = logging.getLogger(__name__)

_DREAM_TRIGGER_RE = re.compile(
    r'<dream_trigger\s+reason="([^"]*)"\s*/>',
    re.IGNORECASE,
)


def parse_dream_trigger_tags(response_text: str) -> tuple[str, list[dict]]:
    """Extract dream trigger tags from response text and strip them.

    Args:
        response_text: The raw response text from Symbia.

    Returns:
        tuple[str, list[dict]]: (cleaned_text, triggers_list)
        Each trigger dict has: reason (str)
    """
    if not response_text:
        return "", []

    triggers = []
    for match in _DREAM_TRIGGER_RE.finditer(response_text):
        reason = match.group(1).strip()
        triggers.append({"reason": reason})
        logger.info("Detected <dream_trigger> with reason: %s", reason[:120])

    cleaned = _DREAM_TRIGGER_RE.sub("", response_text).strip()
    return cleaned, triggers
