import re
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


def _split_mark_at_block_boundaries(wrapped: str, note_id: str) -> str:
    """Split a single <mark> spanning block or inline formatting boundaries
    into multiple <mark> segments.

    Block boundaries in markdown are double newlines (\\n\\n).
    Inline formatting boundaries are markdown formatting delimiters (**, *, `, etc.)
    that create separate HTML elements when rendered.

    The split keeps markdown formatting delimiters OUTSIDE the <mark> tags so
    the markdown parser processes them correctly, while the text content inside
    the formatting remains wrapped in <mark> for highlighting.

    Example: <mark>some **bold** text</mark>
    becomes: <mark>some </mark>**<mark>bold</mark>**<mark> text</mark>

    Each segment gets data-note-id="{note_id}" for frontend lookup.
    The first segment also gets id="note-highlight-{note_id}" for scroll targeting.
    """
    # Extract the inner content between <mark ...> and </mark>
    open_match = re.match(r'<mark[^>]*>', wrapped)
    if not open_match:
        return wrapped

    open_tag_end = open_match.end()
    inner = wrapped[open_tag_end:-len('</mark>')]

    # Inline markdown patterns: (full_pattern, open_group_idx, content_group_idx, close_group_idx)
    # Each pattern captures: open_delim, content, close_delim in groups 1,2,3
    # Order matters: longer/more specific patterns first to avoid partial matches.
    # Single-char patterns use lookbehind/lookahead to avoid matching inside ** constructs.
    inline_patterns = [
        r'(\*\*)(.+?)(\*\*)',                     # **bold**
        r'(__)(.+?)(__)',                          # __bold__
        r'(?<!\*)(\*)(?!\*)(.+?)(?<!\*)(\*)(?!\*)',  # *italic* (not inside **)
        r'(?<!\w)(_)(.+?)(_)(?!\w)',               # _italic_ (word boundaries)
        r'(~~)(.+?)(~~)',                           # ~~strikethrough~~
        r'(``)(.+?)(``)',                           # ``double backtick``
        r'(?<!`)(`)(?<!`)(.+?)(?<!`)(`)(?!`)',     # `inline code` (not inside ``)
        r'(\[)([^\]]+)(\]\([^)]+\))',               # [text](url)
    ]

    # Check if we need any splitting at all
    has_block_breaks = '\n\n' in inner
    has_inline_fmt = any(re.search(p, inner) for p in inline_patterns)

    if not has_block_breaks and not has_inline_fmt:
        return (
            f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">'
            + inner
            + '</mark>'
        )

    def _process_segment(text: str, is_first: bool) -> tuple[str, bool]:
        """Process a text segment, splitting at inline formatting boundaries.
        Returns (result_string, updated_is_first)."""
        # Find all inline formatting matches with their positions
        matches = []
        for pattern in inline_patterns:
            for m in re.finditer(pattern, text):
                matches.append((m.start(), m.end(), m.group(1), m.group(2), m.group(3)))

        if not matches:
            # No inline formatting in this segment
            if is_first:
                return (
                    f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">'
                    + text
                    + '</mark>'
                ), False
            else:
                return (
                    f'<mark data-note-id="{note_id}">'
                    + text
                    + '</mark>'
                ), False

        # Sort matches by position, remove overlapping
        matches.sort(key=lambda x: x[0])
        filtered = []
        last_end = -1
        for start, end, od, ct, cd in matches:
            if start >= last_end:
                filtered.append((start, end, od, ct, cd))
                last_end = end
        matches = filtered

        parts = []
        pos = 0

        for start, end, open_delim, content, close_delim in matches:
            # Plain text before this match
            before = text[pos:start]
            if before:
                if is_first:
                    parts.append(f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">')
                    is_first = False
                else:
                    parts.append(f'<mark data-note-id="{note_id}">')
                parts.append(before)
                parts.append('</mark>')

            # Formatting: open_delim + <mark>content</mark> + close_delim
            parts.append(open_delim)
            if is_first:
                parts.append(f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">')
                is_first = False
            else:
                parts.append(f'<mark data-note-id="{note_id}">')
            parts.append(content)
            parts.append('</mark>')
            parts.append(close_delim)

            pos = end

        # Remaining text after last match
        remaining = text[pos:]
        if remaining:
            if is_first:
                parts.append(f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">')
                is_first = False
            else:
                parts.append(f'<mark data-note-id="{note_id}">')
            parts.append(remaining)
            parts.append('</mark>')

        return ''.join(parts), is_first

    # Step 1: Split at block boundaries (\n\n)
    if has_block_breaks:
        segments = re.split(r'(\n\n+)', inner)
    else:
        segments = [inner]

    # Step 2: Process each segment
    final_parts = []
    is_first = True

    for seg in segments:
        if re.match(r'\n\n+', seg):
            # Block boundary - just emit the \n\n separator
            # (all marks from previous segment are already closed)
            final_parts.append(seg)
            is_first = False
            continue

        processed, is_first = _process_segment(seg, is_first)
        final_parts.append(processed)

    result = ''.join(final_parts)

    # Clean up: remove empty marks like <mark ...></mark>
    result = re.sub(r'<mark[^>]*></mark>', '', result)

    # Ensure we have at least one mark with the primary id
    if f'id="note-highlight-{note_id}"' not in result and 'data-note-id' in result:
        result = result.replace(
            f'<mark data-note-id="{note_id}">',
            f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">',
            1
        )

    # Edge case: if no marks survived cleanup (entire content was formatting)
    # fall back to wrapping the entire inner content in a single mark
    if 'data-note-id' not in result:
        return (
            f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">'
            + inner
            + '</mark>'
        )

    return result


def _remove_note_marks(content: str, note_id: str) -> str:
    """Remove all <mark>/<aaa-note> tags for the given note_id from content.

    Handles both:
    - Split marks: <mark data-note-id="..." ...>...</mark> segments
    - Legacy marks: <mark id="...">...</mark> or <aaa-note id="...">...</aaa-note>
    - New format: <mark id="note-highlight-..." data-note-id="...">...</mark>
    """
    # Strategy 1: Remove split marks using data-note-id attribute
    if f'data-note-id="{note_id}"' in content:
        # Replace open tags with a placeholder, then remove placeholder + adjacent close tags
        placeholder = f'\x00NOTE_{note_id}\x00'
        result = re.sub(
            rf'<(?:aaa-note|mark)\s[^>]*data-note-id="{note_id}"[^>]*>',
            placeholder,
            content
        )

        # Remove close tags that are adjacent to placeholders (possibly with whitespace)
        result = re.sub(
            rf'{re.escape(placeholder)}\s*</(?:aaa-note|mark)>',
            '',
            result
        )

        # For split marks: remove orphaned close tags that were between our removed open tags
        # e.g. </mark>\n\n<placeholder>text</mark> -> after removing: </mark>\n\ntext</mark>
        # The remaining close tags are now orphaned since their open tag was removed.
        remaining_placeholders = result.count(placeholder)
        result = result.replace(placeholder, '')

        if remaining_placeholders > 0:
            balanced = _balance_mark_tags(result)
            if balanced != result:
                result = balanced

        if result != content:
            return result

    # Strategy 2: Legacy marks with just id (unsplit, older format)
    new_content = re.sub(
        rf'<(?:aaa-note|mark) id="{note_id}">(.*?)</(?:aaa-note|mark)>',
        r'\1',
        content,
        flags=re.DOTALL
    )
    if new_content != content:
        return new_content

    # Strategy 3: marks with id="note-highlight-..."
    new_content = re.sub(
        rf'<(?:aaa-note|mark)\s[^>]*id="note-highlight-{note_id}"[^>]*>(.*?)</(?:aaa-note|mark)>',
        r'\1',
        content,
        flags=re.DOTALL
    )
    return new_content


def _balance_mark_tags(content: str) -> str:
    """Remove orphaned </mark> or </aaa-note> close tags that have no matching open tag.

    Walks through the content tracking open/close balance and removes excess close tags.
    """
    # Pattern to match mark/aaa-note open and close tags
    tag_pattern = re.compile(r'<(?:aaa-note|mark)(?:\s[^>]*)?>|</(?:aaa-note|mark)>')

    result = []
    last_end = 0
    depth = 0

    for m in tag_pattern.finditer(content):
        result.append(content[last_end:m.start()])
        tag = m.group()

        if tag.startswith('</'):
            if depth > 0:
                depth -= 1
                result.append(tag)  # keep matched close tag
            # else: orphaned close tag, skip it
        else:
            depth += 1
            result.append(tag)

        last_end = m.end()

    result.append(content[last_end:])
    return ''.join(result)


class NoteRepository(BaseRepository):
    @with_connection
    def create_self_note(
        self,
        id: str,
        conversation_id: str,
        message_id: int,
        selected_text: str,
        comment: str = "",
        visibility: str = "personal",
    ) -> dict:
        """Create a note record for apparatus-authored inline annotations.
        Unlike create_note, this does not modify message content — the tag
        is already present in Symbia's response and will be updated with
        the ID by the post-processor."""
        conn = self._conn()
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

                    wrapped = (
                        f'<mark id="{id}">'
                        + content[start_content:end_content + 1]
                        + f'</mark>'
                    )
                    wrapped = _split_mark_at_block_boundaries(wrapped, id)
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
                        wrapped = _split_mark_at_block_boundaries(wrapped, id)
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
                new_content = _remove_note_marks(content, note_id)

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
