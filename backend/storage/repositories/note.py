import re
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.note_markup import (
    split_mark_at_block_boundaries,
    remove_note_marks,
)


class NoteRepository(BaseRepository):
    @with_connection
    def create_self_note(
        self,
        id: str,
        asset_type: str,
        asset_id: str,
        conversation_id: Optional[str] = None,
        selected_text: str = "",
        comment: str = "",
        visibility: str = "personal",
    ) -> dict:
        conn = self._conn()
        conn.execute(
            """INSERT INTO notes (id, asset_type, asset_id, conversation_id, selected_text, comment, visibility)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (id, asset_type, asset_id, conversation_id, selected_text, comment, visibility),
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM notes WHERE id = ?", (id,)
        ).fetchone()
        return dict(row) if row else {}

    @with_connection
    def create_note(
        self,
        id: str,
        asset_type: str,
        asset_id: str,
        conversation_id: Optional[str] = None,
        selected_text: str = "",
        comment: str = "",
        visibility: str = "personal",
        start_offset: Optional[int] = None,
    ) -> dict:
        conn = self._conn()

        if asset_type == "conversation_message":
            try:
                message_id = int(asset_id)
            except (ValueError, TypeError):
                message_id = None
        else:
            message_id = None

        if asset_type == "conversation_message" and message_id is not None:
            row_msg = conn.execute(
                "SELECT content FROM conversation_log WHERE id = ?", (message_id,)
            ).fetchone()
            if row_msg:
                content = row_msg["content"]
                new_content = None
                if start_offset is not None:
                    plain_chars = []
                    mapping = []

                    i = 0
                    n = len(content)

                    while i < n:
                        if content[i:].startswith('<mark') or content[i:].startswith('<aaa-note'):
                            close_idx = content.find('>', i)
                            if close_idx != -1:
                                i = close_idx + 1
                                continue
                        elif content[i:].startswith('</mark>') or content[i:].startswith('</aaa-note>'):
                            close_idx = content.find('>', i)
                            if close_idx != -1:
                                i = close_idx + 1
                                continue

                        char = content[i]
                        if char in ('*', '_', '`', '~'):
                            i += 1
                            continue

                        plain_chars.append(char)
                        mapping.append(i)
                        i += 1

                    plain_text = "".join(plain_chars)

                    matches = []
                    start_search = 0
                    while True:
                        idx = plain_text.find(selected_text, start_search)
                        if idx == -1:
                            break
                        matches.append(idx)
                        start_search = idx + 1

                    if matches:
                        chosen_idx = min(matches, key=lambda x: abs(x - start_offset))

                        start_plain = chosen_idx
                        end_plain = chosen_idx + len(selected_text) - 1

                        start_content = mapping[start_plain]
                        end_content = mapping[end_plain]

                        wrapped = (
                            f'<mark id="{id}">'
                            + content[start_content:end_content + 1]
                            + f'</mark>'
                        )
                        wrapped = split_mark_at_block_boundaries(wrapped, id)
                        new_content = (
                            content[:start_content]
                            + wrapped
                            + content[end_content + 1:]
                        )

                if new_content is None:
                    trimmed_sel = selected_text.strip()
                    if trimmed_sel:
                        pattern_parts = []
                        filler = r"(?:[\*_~`]|<[^>]+>)*"
                        for char in trimmed_sel:
                            if char.isspace():
                                pattern_parts.append(r"(?:[\s\*_~`]|<[^>]+>)*")
                            else:
                                pattern_parts.append(re.escape(char))
                        pattern = filler.join(pattern_parts)
                        match = re.search(pattern, content)
                        if match:
                            start, end = match.span()
                            wrapped = (
                                f'<mark id="{id}">'
                                + content[start:end]
                                + f'</mark>'
                            )
                            wrapped = split_mark_at_block_boundaries(wrapped, id)
                            new_content = (
                                content[:start]
                                + wrapped
                                + content[end:]
                            )

                if new_content is not None:
                    conn.execute(
                        "UPDATE conversation_log SET content = ? WHERE id = ?",
                        (new_content, message_id),
                    )

        conn.execute(
            """INSERT INTO notes (id, asset_type, asset_id, conversation_id, selected_text, comment, visibility)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (id, asset_type, asset_id, conversation_id, selected_text, comment, visibility),
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM notes WHERE id = ?", (id,)
        ).fetchone()
        return dict(row) if row else {}

    @with_connection
    def get_note(self, note_id: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def get_notes_by_asset(self, asset_type: str, asset_id: str) -> list[dict]:
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM notes WHERE asset_type = ? AND asset_id = ? ORDER BY created_at ASC",
            (asset_type, asset_id),
        )
        return [dict(row) for row in cursor.fetchall()]

    @with_connection
    def get_notes_by_conversation(self, conversation_id: str) -> list[dict]:
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM notes WHERE asset_type = 'conversation_message' AND conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    @with_connection
    def get_notes_by_task(self, task_id: str) -> list[dict]:
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM notes WHERE asset_type = 'research_task' AND asset_id = ? ORDER BY created_at ASC",
            (task_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    @with_connection
    def get_notes_by_task_with_steps(self, task_id: str) -> list[dict]:
        conn = self._conn()
        cursor = conn.execute(
            """
            SELECT n.*, s.step_number, s.step_type
            FROM notes n
            LEFT JOIN research_steps s ON n.asset_type = 'research_step' AND n.asset_id = s.id
            WHERE (n.asset_type = 'research_task' AND n.asset_id = ?)
               OR (n.asset_type = 'research_step' AND n.asset_id IN (
                   SELECT id FROM research_steps WHERE task_id = ?
               ))
            ORDER BY n.created_at ASC
            """,
            (task_id, task_id),
        )
        return [dict(row) for row in cursor.fetchall()]

    @with_connection
    def update_note(self, note_id: str, comment: Optional[str] = None, visibility: Optional[str] = None) -> Optional[dict]:
        conn = self._conn()
        updates = []
        params = []
        if comment is not None:
            updates.append("comment = ?")
            params.append(comment)
        if visibility is not None:
            updates.append("visibility = ?")
            params.append(visibility)

        if not updates:
            row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
            return dict(row) if row else None

        updates.append("updated_at = CURRENT_TIMESTAMP")
        sql_params = params + [note_id]

        conn.execute(
            f"UPDATE notes SET {', '.join(updates)} WHERE id = ?",
            sql_params
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def delete_note(self, note_id: str) -> None:
        conn = self._conn()

        row_note = conn.execute(
            "SELECT asset_type, asset_id FROM notes WHERE id = ?", (note_id,)
        ).fetchone()

        if row_note and row_note["asset_type"] == "conversation_message":
            try:
                message_id = int(row_note["asset_id"])
            except (ValueError, TypeError):
                message_id = None

            if message_id is not None:
                row_msg = conn.execute(
                    "SELECT content FROM conversation_log WHERE id = ?", (message_id,)
                ).fetchone()
                if row_msg:
                    content = row_msg["content"]
                    new_content = remove_note_marks(content, note_id)

                    if new_content != content:
                        conn.execute(
                            "UPDATE conversation_log SET content = ? WHERE id = ?",
                            (new_content, message_id),
                        )

        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()

    @with_connection
    def delete_notes_by_asset(self, asset_type: str, asset_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM notes WHERE asset_type = ? AND asset_id = ?",
            (asset_type, asset_id),
        )
        conn.commit()
