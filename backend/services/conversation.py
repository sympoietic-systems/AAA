from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.storage.repositories import (
        ConsolidationCheckpointRepository,
        ConversationRepository,
        MemoryNodeRepository,
        MessageRepository,
        NoteRepository,
    )

logger = logging.getLogger(__name__)


class ConversationService:
    @staticmethod
    def ensure_structural_tags(conv_repo, conversation) -> list[dict]:
        existing_tags = conv_repo.get_tags(conversation.id)
        has_structural = False
        for et in existing_tags:
            if et["tag_type"] == "structural":
                has_structural = True
                break

        if has_structural:
            return existing_tags

        title = conversation.title or ""
        agent_id = getattr(conversation, "agent_id", "symbia") or "symbia"
        if agent_id != "symbia":
            structural_tag = "other agents"
        elif "Dream Log" in title or "Internal Diary" in title or "dream" in title.lower():
            structural_tag = "dreams"
        elif "consultation:" in title.lower():
            structural_tag = "other agents"
        else:
            structural_tag = "user conversation"

        conv_repo.add_tag(conversation.id, structural_tag, "structural")
        return conv_repo.get_tags(conversation.id)

    @staticmethod
    def build_conversation_info(conv_repo, checkpoint_repo, conv):
        from backend.services.conversation import ConversationService as CS

        tags = CS.ensure_structural_tags(conv_repo, conv)
        summary = None
        human_summary = None
        if checkpoint_repo:
            cp = checkpoint_repo.get_latest(conv.id)
            if cp:
                summary = cp.get("summary")
                human_summary = cp.get("human_summary")
        return {
            "id": conv.id,
            "title": conv.title,
            "agent_id": getattr(conv, "agent_id", None),
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "message_count": conv.message_count,
            "tags": [{"tag": t["tag"], "tag_type": t["tag_type"]} for t in tags],
            "summary": summary,
            "human_summary": human_summary,
        }


class ConversationUseCases:
    """Conversation persistence workflows behind an async boundary."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        checkpoint_repo: ConsolidationCheckpointRepository | None = None,
        note_repo: NoteRepository | None = None,
        memory_node_repo: MemoryNodeRepository | None = None,
    ) -> None:
        self._conversations = conversation_repo
        self._messages = message_repo
        self._checkpoints = checkpoint_repo
        self._notes = note_repo
        self._memory_nodes = memory_node_repo

    def _require_conversation(self, conversation_id: str):
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            raise LookupError("Conversation not found")
        return conversation

    async def list(self, *, tag: str | None, search: str | None, limit: int | None, offset: int | None):
        return await asyncio.to_thread(self._list, tag=tag, search=search, limit=limit, offset=offset)

    def _list(self, *, tag: str | None, search: str | None, limit: int | None, offset: int | None):
        conversations = self._conversations.list_all(tag=tag, search=search, limit=limit, offset=offset)
        total = self._conversations.count_all(tag=tag, search=search)
        return [
            ConversationService.build_conversation_info(self._conversations, self._checkpoints, item)
            for item in conversations
        ], total

    async def get(self, conversation_id: str) -> dict:
        return await asyncio.to_thread(self._get, conversation_id)

    def _get(self, conversation_id: str) -> dict:
        conversation = self._require_conversation(conversation_id)
        return ConversationService.build_conversation_info(self._conversations, self._checkpoints, conversation)

    async def update_title(self, conversation_id: str, title: str) -> dict:
        return await asyncio.to_thread(self._update_title, conversation_id, title)

    def _update_title(self, conversation_id: str, title: str) -> dict:
        self._require_conversation(conversation_id)
        self._conversations.update_title(conversation_id, title)
        conversation = self._require_conversation(conversation_id)
        return ConversationService.build_conversation_info(self._conversations, self._checkpoints, conversation)

    async def delete(self, conversation_id: str) -> None:
        await asyncio.to_thread(self._delete, conversation_id)

    def _delete(self, conversation_id: str) -> None:
        self._require_conversation(conversation_id)
        self._conversations.delete(conversation_id)

    async def delete_message(self, conversation_id: str, message_id: int) -> None:
        await asyncio.to_thread(self._delete_message, conversation_id, message_id)

    def _delete_message(self, conversation_id: str, message_id: int) -> None:
        self._require_conversation(conversation_id)
        message = self._messages.get_by_id(message_id)
        if message is None or message.conversation_id != conversation_id:
            raise LookupError("Message not found in this conversation")
        self._messages.delete_message(message_id)
        self._conversations.touch(conversation_id)

    async def generate_human_summary(self, conversation_id: str, background_engine) -> dict:
        conversation, messages, ancestor_ids, leaf_message_id = await asyncio.to_thread(
            self._summary_context, conversation_id
        )
        from backend.metabolisation.consolidation import generate_human_summary_text

        human_summary = await generate_human_summary_text(background_engine, messages)
        if not human_summary:
            raise RuntimeError("Failed to generate human summary")
        return await asyncio.to_thread(
            self._save_human_summary,
            conversation,
            messages,
            ancestor_ids,
            leaf_message_id,
            human_summary,
        )

    def _summary_context(self, conversation_id: str):
        conversation = self._require_conversation(conversation_id)
        recent = self._messages.get_recent(limit=1, conversation_id=conversation_id)
        if not recent:
            raise LookupError("No messages in conversation")
        leaf_message_id = recent[0].id
        messages = self._messages.get_ancestor_path(leaf_message_id)
        ancestor_ids = [message.id for message in messages if message.id is not None]
        return conversation, messages, ancestor_ids, leaf_message_id

    def _save_human_summary(
        self,
        conversation,
        messages,
        ancestor_ids: list[int],
        leaf_message_id: int,
        human_summary: str,
    ) -> dict:
        if self._checkpoints:
            checkpoint = self._checkpoints.get_latest_checkpoint_for_path(conversation.id, ancestor_ids)
            if checkpoint and checkpoint.get("id"):
                self._checkpoints.update_human_summary(checkpoint["id"], human_summary)
            else:
                self._checkpoints.save(
                    conversation.id,
                    len(messages),
                    "",
                    human_summary=human_summary,
                    message_id=leaf_message_id,
                )
        return ConversationService.build_conversation_info(self._conversations, self._checkpoints, conversation)

    async def generate_title(self, conversation_id: str, background_engine) -> dict:
        await asyncio.to_thread(self._require_conversation, conversation_id)
        from backend.services.title import TitleService

        title = await TitleService.generate_from_conversation(background_engine, self._messages, conversation_id)
        return await asyncio.to_thread(self._update_title, conversation_id, title)

    async def commit_branch(
        self,
        conversation_id: str,
        *,
        speaker: str,
        content: str,
        parent_message_id: int | None,
        agent_id: str,
        embedder,
        content_tokens: int,
    ):
        await asyncio.to_thread(self._touch_existing_conversation, conversation_id)
        embedding = b""
        embedding_model = "unknown"
        embedding_dim = 0
        if embedder.service.is_loaded:
            try:
                vector = await embedder.service.encode_async(content)
                embedding = embedder.service.serialize(vector)
                embedding_model = embedder.service.model_name
                embedding_dim = embedder.service.dim
            except (RuntimeError, ValueError, OSError):
                logger.warning("Failed to embed committed branch message", exc_info=True)
        message = await asyncio.to_thread(
            self._messages.insert,
            speaker=speaker,
            content=content,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            agent_id=agent_id,
            conversation_id=conversation_id,
            content_tokens=content_tokens,
            parent_message_id=parent_message_id,
        )
        return message, bool(embedding)

    def _touch_existing_conversation(self, conversation_id: str) -> None:
        self._require_conversation(conversation_id)
        self._conversations.touch(conversation_id)

    async def tree(self, conversation_id: str):
        return await asyncio.to_thread(self._tree, conversation_id)

    def _tree(self, conversation_id: str):
        self._require_conversation(conversation_id)
        return (
            self._messages.get_messages_by_conversation(conversation_id),
            self._messages.get_message_links(conversation_id),
        )

    async def create_link(self, **values):
        return await asyncio.to_thread(self._messages.add_message_link, **values)

    async def confirm_link(self, link_id: str) -> None:
        await asyncio.to_thread(self._messages.confirm_message_link, link_id)

    async def delete_link(self, link_id: str) -> None:
        await asyncio.to_thread(self._messages.delete_message_link, link_id)

    async def export(self, conversation_id: str) -> tuple[str, str]:
        return await asyncio.to_thread(self._export, conversation_id)

    def _export(self, conversation_id: str) -> tuple[str, str]:
        conversation = self._require_conversation(conversation_id)
        checkpoint = self._checkpoints.get_latest(conversation_id) if self._checkpoints else None
        notes = self._notes.get_notes_by_conversation(conversation_id) if self._notes else []
        memory_nodes = self._memory_nodes.get_nodes(conversation_id) if self._memory_nodes else []
        from backend.services.export import ExportService

        markdown = ExportService.build_export(
            conv={
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else "",
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else "",
                "message_count": conversation.message_count,
                "agent_id": conversation.agent_id,
            },
            tags=self._conversations.get_tags(conversation_id),
            checkpoint=checkpoint,
            messages=self._messages.get_messages_by_conversation(conversation_id),
            links=self._messages.get_message_links(conversation_id),
            notes=notes,
            memory_nodes=memory_nodes,
        )
        safe_title = (
            conversation.title.strip().replace(" ", "_").replace("/", "_")[:80]
            if conversation.title
            else "conversation"
        )
        return markdown, f"{safe_title}_{conversation_id[:8]}.md"

    async def spectral_suggestions(
        self,
        conversation_id: str,
        message_id: int,
        threshold: float,
    ) -> list[dict]:
        return await asyncio.to_thread(self._spectral_suggestions, conversation_id, message_id, threshold)

    def _spectral_suggestions(self, conversation_id: str, message_id: int, threshold: float) -> list[dict]:
        path = self._messages.get_ancestor_path(message_id)
        ancestor_ids = [message.id for message in path]
        return self._messages.get_parallel_messages_by_similarity(
            conversation_id=conversation_id,
            message_id=message_id,
            ancestor_ids=ancestor_ids,
            threshold=threshold,
            limit=5,
        )
