import re
from typing import Any
from backend.pipeline.metadata import ModuleMeta
from backend.storage.repository import MessageRepository
from backend.utils.token_counter import caveman_compress

from .base import ProcessingModule


def process_inline_notes(content: str, notes_by_id: dict) -> str:
    """Prepare inline note tags for LLM context by filtering on visibility.

    Handles both legacy (``<mark id="ID">``) and split
    (``<mark id="note-highlight-ID" data-note-id="ID">``) tag formats.

    Visibility behaviour:
      - **personal** → tag stripped, inner text preserved (invisible to LLM).
      - **shared / agent** → rewritten to ``<note_entanglement note_id="…" comment="…">``
        so the LLM can see and reference the annotation.
      - **unknown / hallucinated ID** → tag stripped, inner text preserved.

    ``<scar-fold>`` / ``<scar_fold>`` tags pass through untouched (truncated
    to 200 chars as a safeguard).
    """
    # Matches <aaa-note ...>...</aaa-note> or <mark ...>...</mark>
    pattern = r'<(aaa-note|mark)(\s+[^>]*?)?>([\s\S]*?)</\1>'

    def replace_tag(match):
        tag_name = match.group(1)
        attrs = match.group(2) or ""
        text = match.group(3)

        # Extract note ID from attributes (try data-note-id first, then id)
        note_id_match = re.search(r'\bdata-note-id\s*=\s*["\']([^"\']+)["\']', attrs)
        if not note_id_match:
            note_id_match = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs)

        if not note_id_match:
            return text  # Strip the formatting tag if there's no ID

        note_id = note_id_match.group(1)
        if note_id.startswith("note-highlight-"):
            note_id = note_id.replace("note-highlight-", "")

        note = notes_by_id.get(note_id)
        if note and note.get("visibility") in ("shared", "agent"):
            comment = note.get("comment", "")
            return f'<note_entanglement note_id="{note_id}" comment="{comment}">{text}</note_entanglement>'
        else:
            return text

    content = re.sub(pattern, replace_tag, content)

    # Scar folds pass through untouched — they are preserved in Symbia's context
    # as material folds for self-reflexive annotations. Truncate to 200 chars as safeguard.
    def truncate_scar_fold(match):
        tag = match.group(1)
        inner = match.group(2)
        if len(inner) > 200:
            return f"<{tag}>{inner[:200]}</{tag}>"
        return match.group(0)

    content = re.sub(r'<(scar_fold|scar-fold)>([\s\S]*?)</\1>', truncate_scar_fold, content)

    return content


class ContextCollectorModule(ProcessingModule):
    def __init__(
        self,
        message_repo: MessageRepository,
        note_repo: Any,
        max_history: int = 20,
        floating_window: int = 8,
        caveman_enabled: bool = True,
        compressed_message_repo: Any = None,
        llm_compression_enabled: bool = False,
    ):
        self._repo = message_repo
        self._note_repo = note_repo
        self._max_history = max_history
        self._floating_window = floating_window
        self._caveman_enabled = caveman_enabled
        self._compressed_message_repo = compressed_message_repo
        self._llm_compression_enabled = llm_compression_enabled

    @property
    def name(self) -> str:
        return "context_collector"

    @property
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="context_collector",
            description="Gathers conversation history with tiered compression and processes conversation notes",
            category="memory",
            always_run=True,
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        conversation_id = payload.get("conversation_id", "")
        parent_message_id = payload.get("parent_message_id")
        
        if parent_message_id is None and conversation_id:
            last_msgs = self._repo.get_recent(limit=1, conversation_id=conversation_id)
            if last_msgs:
                parent_message_id = last_msgs[0].id

        if parent_message_id is not None:
            raw_msgs = self._repo.get_ancestor_path(parent_message_id, limit=self._max_history)
            payload["branch_context_tag"] = f"msg_{parent_message_id}"
            payload["ancestor_message_ids"] = [msg.id for msg in raw_msgs if msg.id is not None]
        else:
            raw_msgs = self._repo.get_recent(
                limit=self._max_history,
                conversation_id=conversation_id if conversation_id else None,
            )
            payload["branch_context_tag"] = "root"
            payload["ancestor_message_ids"] = [msg.id for msg in raw_msgs if msg.id is not None]

        # Load notes for visibility stripping and entanglement injection
        notes = self._note_repo.get_notes_by_conversation(conversation_id) if conversation_id else []
        notes_by_id = {n["id"]: n for n in notes}
        notes_by_msg_id = {}
        for n in notes:
            notes_by_msg_id.setdefault(n["message_id"], []).append(n)

        # R5: Load compressed blocks for middle history if LLM compression enabled
        compressed_blocks: dict[int, str] = {}
        if (
            self._llm_compression_enabled
            and self._compressed_message_repo
            and conversation_id
        ):
            try:
                tier2_msg_ids = [
                    row.id for row in raw_msgs
                    if row.id is not None
                    and (len(raw_msgs) - 1 - raw_msgs.index(row)) >= self._floating_window
                ]
                if tier2_msg_ids:
                    blocks = self._compressed_message_repo.get_for_messages(
                        conversation_id, tier2_msg_ids
                    )
                    for block in blocks:
                        # Map each message ID in range to the compressed block
                        for mid in range(block["first_message_id"], block["last_message_id"] + 1):
                            compressed_blocks[mid] = block["compressed_block"]
            except Exception:
                pass

        messages: list[dict] = []

        total = len(raw_msgs)
        for i, row in enumerate(raw_msgs):
            position_from_end = total - 1 - i
            
            if row.speaker == "apparatus":
                role = "assistant"
            elif row.speaker == "system":
                role = "system"
            else:
                role = "user"

            if role == "system":
                first_line = row.content.split("\n")[0].strip()
                content = f"[System Notification: {first_line}]"
            elif position_from_end < self._floating_window:
                content = row.content
            else:
                # R5: Prefer LLM-compressed block over caveman compression
                compressed_block = compressed_blocks.get(row.id)
                if compressed_block:
                    content = (
                        f'<sedimented_strata message_id="{row.id}" speaker="{role}" '
                        f'position_from_end="{position_from_end}" compressed="llm">'
                        f'{compressed_block}</sedimented_strata>'
                    )
                else:
                    compressed = caveman_compress(row.content) if self._caveman_enabled else row.content
                    content = f'<sedimented_strata message_id="{row.id}" speaker="{role}" position_from_end="{position_from_end}">{compressed}</sedimented_strata>'

            # Parse inline notes (strip personal, replace shared)
            content = process_inline_notes(content, notes_by_id)

            messages.append({"role": role, "content": content})

            # Inject shared note system notifications immediately after the annotated message
            msg_notes = notes_by_msg_id.get(row.id, [])
            for note in msg_notes:
                if note.get("visibility") == "shared":
                    speaker_label = "user" if role == "user" else "assistant"
                    comment_part = f" | Comment: \"{note['comment']}\"" if note.get("comment") else ""
                    messages.append({
                        "role": "system",
                        "content": f"[Shared Note on message from {speaker_label}]: Highlighted: \"{note['selected_text']}\"{comment_part}"
                    })

        current = payload.get("content", "")
        if current:
            # We don't expect inline notes in current input message since user hasn't sent it yet,
            # but we can process it just in case
            current_processed = process_inline_notes(current, notes_by_id)
            messages.append({"role": "user", "content": current_processed})

        payload["messages"] = messages
        payload["raw_msg_count"] = total

        return payload
