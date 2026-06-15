"""Self-annotation post-processing for assistant responses.

Extracted from services/chat.py to keep ChatService focused on
pipeline orchestration rather than annotation tag manipulation.
"""

import logging
import re
import uuid

logger = logging.getLogger(__name__)


def process_self_annotations(
    response_text: str,
    conversation_id: str,
    message_id: int,
    note_repo,
    message_repo,
) -> str:
    """Post-process Symbia's response to normalize annotation tags for the frontend.

    Three processing stages run in order:

    1. **Entanglement echo conversion** — ``<note_entanglement>`` tags echoed
       from the LLM context are converted back to ``<mark>`` tags with proper
       ``id`` and ``data-note-id`` attributes.  A DB note record is created
       for any note ID that doesn't already exist.
    2. **New self-annotation processing** — ``<mark comment="…">`` or
       ``<aaa-note comment="…">`` tags *without* an ``id`` attribute are
       treated as new agent annotations: a UUID is generated, a DB record
       is created, and the tag is rewritten with the new ID.
    3. **Scar-fold truncation** — ``<scar_fold>`` / ``<scar-fold>`` content
       is truncated to 200 characters as a safeguard.
    """
    original_text = response_text

    # --- Convert echoed <note_entanglement> tags back to <mark> ---
    entanglement_ids_created = []

    def convert_entanglement(m):
        attrs = m.group(1) or ""
        text = m.group(2)
        nid_match = re.search(r'\bnote_id\s*=\s*["\']([^"\']+)["\']', attrs)
        if not nid_match:
            return text

        nid = nid_match.group(1)
        comment_match = re.search(r'\bcomment\s*=\s*["\']([^"\']*)["\']', attrs)
        comment = comment_match.group(1) if comment_match else ""

        existing = note_repo.get_note(nid)
        if not existing:
            note_repo.create_self_note(
                id=nid,
                conversation_id=conversation_id,
                message_id=message_id,
                selected_text=text.strip(),
                comment=comment,
                visibility="agent",
            )
            entanglement_ids_created.append(nid)

        return f'<mark id="note-highlight-{nid}" data-note-id="{nid}">{text}</mark>'

    response_text = re.sub(
        r'<note_entanglement(\s+[^>]*?)?>([\s\S]*?)</note_entanglement>',
        convert_entanglement, response_text,
    )

    if entanglement_ids_created:
        logger.debug(
            "Entanglement echo: created %d note record(s) for message %d",
            len(entanglement_ids_created), message_id,
        )

    # --- Self-annotation processing ---
    annotation_pattern = r'<(aaa-note|mark)(\s+[^>]+)?>([\s\S]*?)</\1>'
    annotations_found = []

    def replace_and_create(match):
        tag_name = match.group(1)
        attrs = match.group(2) or ""
        text = match.group(3)

        if re.search(r'\bid\s*=\s*["\']', attrs):
            return match.group(0)

        comment_match = re.search(r'\bcomment\s*=\s*["\']([\s\S]*?)["\']', attrs)
        if not comment_match:
            return match.group(0)

        comment = comment_match.group(1)
        visibility = "agent"
        note_id = str(uuid.uuid4())
        annotations_found.append(note_id)

        note_repo.create_self_note(
            id=note_id,
            conversation_id=conversation_id,
            message_id=message_id,
            selected_text=text.strip(),
            comment=comment,
            visibility=visibility,
        )
        return f'<{tag_name} id="note-highlight-{note_id}" data-note-id="{note_id}">{text}</{tag_name}>'

    processed = re.sub(annotation_pattern, replace_and_create, response_text)

    if annotations_found:
        logger.debug(
            "Self-annotation: created %d note(s) for message %d",
            len(annotations_found), message_id,
        )

    # --- Scar-fold truncation safeguard ---
    def truncate_scar_fold(match):
        tag = match.group(1)
        content = match.group(2)
        if len(content) > 200:
            return f"<{tag}>{content[:200]}</{tag}>"
        return match.group(0)

    processed = re.sub(r'<(scar_fold|scar-fold)>([\s\S]*?)</\1>', truncate_scar_fold, processed)

    if processed != original_text:
        message_repo.update_content(message_id, processed)

    return processed
