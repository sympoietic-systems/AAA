"""Stable claim identity and inert representation of historical belief XML."""

import hashlib
import re
import unicodedata


def statement_key(statement: str) -> str:
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", statement).strip()).casefold()
    return hashlib.sha256(normalized.encode()).hexdigest()


def inert_belief_history(content: str) -> str:
    """Keep historical claims readable while removing their action syntax in prompts only."""
    return re.sub(
        r"</?belief[-_](?:nucleate|proposal)\b[^>]*>",
        "[historical belief candidate]",
        content,
        flags=re.I,
    )
