"""HTML/Markdown tag manipulation utilities for conversation message notes.

Extracted from NoteRepository to separate markup logic from data access.
"""

import re


def split_mark_at_block_boundaries(wrapped: str, note_id: str) -> str:
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
    open_match = re.match(r'<mark[^>]*>', wrapped)
    if not open_match:
        return wrapped

    open_tag_end = open_match.end()
    inner = wrapped[open_tag_end:-len('</mark>')]

    inline_patterns = [
        r'(\*\*)(.+?)(\*\*)',
        r'(__)(.+?)(__)',
        r'(?<!\*)(\*)(?!\*)(.+?)(?<!\*)(\*)(?!\*)',
        r'(?<!\w)(_)(.+?)(_)(?!\w)',
        r'(~~)(.+?)(~~)',
        r'(``)(.+?)(``)',
        r'(?<!`)(`)(?<!`)(.+?)(?<!`)(`)(?!`)',
        r'(\[)([^\]]+)(\]\([^)]+\))',
    ]

    has_block_breaks = '\n\n' in inner
    has_inline_fmt = any(re.search(p, inner) for p in inline_patterns)

    if not has_block_breaks and not has_inline_fmt:
        return (
            f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">'
            + inner
            + '</mark>'
        )

    def _process_segment(text: str, is_first: bool) -> tuple[str, bool]:
        matches = []
        for pattern in inline_patterns:
            for m in re.finditer(pattern, text):
                matches.append((m.start(), m.end(), m.group(1), m.group(2), m.group(3)))

        if not matches:
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
            before = text[pos:start]
            if before:
                if is_first:
                    parts.append(f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">')
                    is_first = False
                else:
                    parts.append(f'<mark data-note-id="{note_id}">')
                parts.append(before)
                parts.append('</mark>')

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

    if has_block_breaks:
        segments = re.split(r'(\n\n+)', inner)
    else:
        segments = [inner]

    final_parts = []
    is_first = True

    for seg in segments:
        if re.match(r'\n\n+', seg):
            final_parts.append(seg)
            is_first = False
            continue

        processed, is_first = _process_segment(seg, is_first)
        final_parts.append(processed)

    result = ''.join(final_parts)

    result = re.sub(r'<mark[^>]*></mark>', '', result)

    if f'id="note-highlight-{note_id}"' not in result and 'data-note-id' in result:
        result = result.replace(
            f'<mark data-note-id="{note_id}">',
            f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">',
            1
        )

    if 'data-note-id' not in result:
        return (
            f'<mark id="note-highlight-{note_id}" data-note-id="{note_id}">'
            + inner
            + '</mark>'
        )

    return result


def remove_note_marks(content: str, note_id: str) -> str:
    """Remove all <mark>/<aaa-note> tags for the given note_id from content.

    Handles both:
    - Split marks: <mark data-note-id="..." ...>...</mark> segments
    - Legacy marks: <mark id="...">...</mark> or <aaa-note id="...">...</aaa-note>
    - New format: <mark id="note-highlight-..." data-note-id="...">...</mark>
    """
    if f'data-note-id="{note_id}"' in content:
        placeholder = f'\x00NOTE_{note_id}\x00'
        result = re.sub(
            rf'<(?:aaa-note|mark)\s[^>]*data-note-id="{note_id}"[^>]*>',
            placeholder,
            content
        )

        result = re.sub(
            rf'{re.escape(placeholder)}\s*</(?:aaa-note|mark)>',
            '',
            result
        )

        result = result.replace(placeholder, '')

        if placeholder in result:
            result = balance_tags(result)

        if result != content:
            return result

    new_content = re.sub(
        rf'<(?:aaa-note|mark) id="{note_id}">(.*?)</(?:aaa-note|mark)>',
        r'\1',
        content,
        flags=re.DOTALL
    )
    if new_content != content:
        return new_content

    new_content = re.sub(
        rf'<(?:aaa-note|mark)\s[^>]*id="note-highlight-{note_id}"[^>]*>(.*?)</(?:aaa-note|mark)>',
        r'\1',
        content,
        flags=re.DOTALL
    )
    return new_content


def balance_tags(content: str) -> str:
    """Remove orphaned </mark> or </aaa-note> close tags that have no matching open tag.

    Walks through the content tracking open/close balance and removes excess close tags.
    """
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
                result.append(tag)
        else:
            depth += 1
            result.append(tag)

        last_end = m.end()

    result.append(content[last_end:])
    return ''.join(result)
