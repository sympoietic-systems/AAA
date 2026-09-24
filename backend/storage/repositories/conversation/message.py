"""Compatibility facade for focused message repository collaborators."""

from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.conversation.message_core import MessageCoreRepository
from backend.storage.repositories.conversation.message_graph import MessageGraphRepository
from backend.storage.repositories.conversation.message_history import MessageHistoryRepository
from backend.storage.repositories.conversation.message_vector import MessageVectorRepository


class MessageRepository(
    MessageCoreRepository,
    MessageHistoryRepository,
    MessageVectorRepository,
    MessageGraphRepository,
):
    """Preserve the historical repository API while delegating by responsibility."""

    def __init__(self, db_path: str):
        BaseRepository.__init__(self, db_path)
        self._normalize_legacy_links()
