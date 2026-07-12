import logging
import uuid

logger = logging.getLogger(__name__)


class NoteService:
    @staticmethod
    async def metabolize_background(
        state, conversation_id: str, message_id: int, selected_text: str, comment: str, note_id: str
    ):
        try:
            state.message_repo.increment_message_note_count(message_id, 1)
        except Exception as e:
            logger.error("Failed to increment message note count: %s", e)

        belief_metabolism = getattr(state, "belief_metabolism", None)
        if belief_metabolism:
            await belief_metabolism.metabolize_note(
                conversation_id=conversation_id,
                message_id=message_id,
                selected_text=selected_text,
                comment=comment,
                note_id=note_id,
            )

    @staticmethod
    def create(
        note_repo,
        asset_type: str,
        asset_id: str,
        conversation_id: str | None = None,
        selected_text: str = "",
        comment: str = "",
        visibility: str = "personal",
        start_offset: int | None = None,
    ) -> dict:
        note_id = str(uuid.uuid4())
        return note_repo.create_note(
            id=note_id,
            asset_type=asset_type,
            asset_id=asset_id,
            conversation_id=conversation_id,
            selected_text=selected_text,
            comment=comment,
            visibility=visibility,
            start_offset=start_offset,
        )

    @staticmethod
    def get(note_repo, note_id: str) -> dict | None:
        return note_repo.get_note(note_id)

    @staticmethod
    def list_by_conversation(note_repo, conversation_id: str) -> list[dict]:
        return note_repo.get_notes_by_conversation(conversation_id)

    @staticmethod
    def list_by_asset(note_repo, asset_type: str, asset_id: str) -> list[dict]:
        return note_repo.get_notes_by_asset(asset_type, asset_id)

    @staticmethod
    def list_by_task_with_steps(note_repo, task_id: str) -> list[dict]:
        return note_repo.get_notes_by_task_with_steps(task_id)

    @staticmethod
    def update(note_repo, note_id: str, comment: str | None = None, visibility: str | None = None) -> dict | None:
        return note_repo.update_note(note_id, comment=comment, visibility=visibility)

    @staticmethod
    def delete(note_repo, note_id: str) -> None:
        note_repo.delete_note(note_id)
