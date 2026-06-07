import re
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class NoteRepository(BaseRepository):
    @with_connection
    def create_note(
        self,
        id: str,
        conversation_id: str,
        message_id: int,
        selected_text: str,
        comment: str = "",
        visibility: str = "personal",
        start_offset: Optional[int] = None,
    ) -> dict:
        conn = self._conn()

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

                    new_content = (
                        content[:start_content]
                        + f'<mark id="{id}">'
                        + content[start_content:end_content + 1]
                        + f'</mark>'
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
                        new_content = (
                            content[:start]
                            + f'<mark id="{id}">'
                            + content[start:end]
                            + f'</mark>'
                            + content[end:]
                        )

            if new_content is not None:
                conn.execute(
                    "UPDATE conversation_log SET content = ? WHERE id = ?",
                    (new_content, message_id),
                )

        conn.execute(
            """INSERT INTO conversation_notes (id, conversation_id, message_id, selected_text, comment, visibility)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (id, conversation_id, message_id, selected_text, comment, visibility),
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM conversation_notes WHERE id = ?", (id,)
        ).fetchone()
        return dict(row) if row else {}

    @with_connection
    def get_note(self, note_id: str) -> Optional[dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM conversation_notes WHERE id = ?", (note_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def get_notes_by_conversation(self, conversation_id: str) -> list[dict]:
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM conversation_notes WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
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
            row = conn.execute("SELECT * FROM conversation_notes WHERE id = ?", (note_id,)).fetchone()
            return dict(row) if row else None

        updates.append("updated_at = CURRENT_TIMESTAMP")
        sql_params = params + [note_id]

        conn.execute(
            f"UPDATE conversation_notes SET {', '.join(updates)} WHERE id = ?",
            sql_params
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversation_notes WHERE id = ?", (note_id,)
        ).fetchone()
        return dict(row) if row else None

    @with_connection
    def delete_note(self, note_id: str) -> None:
        conn = self._conn()

        row_note = conn.execute(
            "SELECT message_id FROM conversation_notes WHERE id = ?", (note_id,)
        ).fetchone()

        if row_note:
            message_id = row_note["message_id"]
            row_msg = conn.execute(
                "SELECT content FROM conversation_log WHERE id = ?", (message_id,)
            ).fetchone()
            if row_msg:
                content = row_msg["content"]
                new_content = re.sub(
                    rf'<(?:aaa-note|mark) id="{note_id}">(.*?)</(?:aaa-note|mark)>',
                    r'\1',
                    content
                )
                if new_content != content:
                    conn.execute(
                        "UPDATE conversation_log SET content = ? WHERE id = ?",
                        (new_content, message_id),
                    )

        conn.execute(
            "DELETE FROM conversation_notes WHERE id = ?",
            (note_id,),
        )
        conn.commit()
