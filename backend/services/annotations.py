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
                asset_type="conversation_message",
                asset_id=str(message_id),
                conversation_id=conversation_id,
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
            asset_type="conversation_message",
            asset_id=str(message_id),
            conversation_id=conversation_id,
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


# ── Research Proposal Extraction ───────────────────────────────────────

RESEARCH_PROPOSAL_PATTERN = re.compile(
    r'<research-proposal(?:\s+[^>]*?)?>(.*?)</research-proposal>', re.DOTALL
)


def extract_research_proposals(message_content: str) -> list[dict]:
    """Extract <research-proposal> XML blocks from Symbia's response.

    Parses the XML-encoded proposal data for frontend rendering
    as interactive approval cards.

    Returns a list of proposal dicts with keys:
        id, objective, rationale, suggested_depth, suggested_breadth, is_agonistic
    """
    proposals = []
    for match in RESEARCH_PROPOSAL_PATTERN.finditer(message_content):
        xml_str = match.group(0)
        
        # Check if the tag contains an id attribute
        id_match = re.match(r'^<research-proposal(?:\s+[^>]*?)?\bid\s*=\s*["\']([^"\']+)["\']', xml_str)
        proposal_id = id_match.group(1) if id_match else str(uuid.uuid4())

        # Parse fields
        objective_m = re.search(r'<objective>(.*?)</objective>', xml_str, re.DOTALL)
        rationale_m = re.search(r'<rationale>(.*?)</rationale>', xml_str, re.DOTALL)
        depth_m = re.search(r'<suggested_depth>(.*?)</suggested_depth>', xml_str, re.DOTALL)
        breadth_m = re.search(r'<suggested_breadth>(.*?)</suggested_breadth>', xml_str, re.DOTALL)
        agonistic_m = re.search(r'<is_agonistic>(.*?)</is_agonistic>', xml_str, re.DOTALL)

        objective = (objective_m.group(1) if objective_m else "").strip()
        rationale = (rationale_m.group(1) if rationale_m else "").strip()

        try:
            suggested_depth = int(depth_m.group(1).strip() if depth_m else "2")
        except ValueError:
            suggested_depth = 2

        try:
            suggested_breadth = int(breadth_m.group(1).strip() if breadth_m else "3")
        except ValueError:
            suggested_breadth = 3

        is_agonistic = (agonistic_m.group(1).strip() if agonistic_m else "false").lower() == "true"

        proposals.append({
            "id": proposal_id,
            "objective": objective,
            "rationale": rationale,
            "suggested_depth": suggested_depth,
            "suggested_breadth": suggested_breadth,
            "is_agonistic": is_agonistic,
        })
    return proposals


def strip_research_proposals(message_content: str) -> str:
    """Remove <research-proposal> blocks from message content for clean display."""
    return RESEARCH_PROPOSAL_PATTERN.sub("", message_content).strip()


def process_research_proposals(
    response_text: str,
    conversation_id: str,
    message_id: int,
    task_manager,
    message_repo,
) -> str:
    """Scan response_text for <research-proposal> tags without ids.

    For each one, parse the fields, create a proposed research task in the DB,
    and rewrite the tag to include the generated task id.
    """
    original_text = response_text

    def replace_proposal(match):
        xml_str = match.group(0)
        # Check if the tag already contains an id attribute
        start_tag_match = re.match(r'^<research-proposal(\s+[^>]*?)?>', xml_str)
        if start_tag_match:
            attrs = start_tag_match.group(1) or ""
            if re.search(r'\bid\s*=\s*["\']', attrs):
                return xml_str

        # Parse fields
        objective_m = re.search(r'<objective>(.*?)</objective>', xml_str, re.DOTALL)
        rationale_m = re.search(r'<rationale>(.*?)</rationale>', xml_str, re.DOTALL)
        depth_m = re.search(r'<suggested_depth>(.*?)</suggested_depth>', xml_str, re.DOTALL)
        breadth_m = re.search(r'<suggested_breadth>(.*?)</suggested_breadth>', xml_str, re.DOTALL)
        agonistic_m = re.search(r'<is_agonistic>(.*?)</is_agonistic>', xml_str, re.DOTALL)

        objective = (objective_m.group(1) if objective_m else "").strip()
        rationale = (rationale_m.group(1) if rationale_m else "").strip()

        try:
            suggested_depth = int(depth_m.group(1).strip() if depth_m else "2")
        except ValueError:
            suggested_depth = 2

        try:
            suggested_breadth = int(breadth_m.group(1).strip() if breadth_m else "3")
        except ValueError:
            suggested_breadth = 3

        is_agonistic = (agonistic_m.group(1).strip() if agonistic_m else "false").lower() == "true"

        # Create proposed task
        title = objective[:80]
        task_id = task_manager.create_task(
            objective=objective,
            trigger_source="symbia_conversation",
            title=title,
            conversation_id=conversation_id,
            status="proposed",
            priority=3,
            max_depth=suggested_depth,
            max_breadth=suggested_breadth,
            is_agonistic=is_agonistic,
            budget_limit_usd=0.50,
            proposal_rationale=rationale,
            proposal_message_id=message_id,
        )

        # Rewrite tag to include the task_id
        rewritten = (
            f'<research-proposal id="{task_id}">\n'
            f'  <objective>{objective}</objective>\n'
            f'  <rationale>{rationale}</rationale>\n'
            f'  <suggested_depth>{suggested_depth}</suggested_depth>\n'
            f'  <suggested_breadth>{suggested_breadth}</suggested_breadth>\n'
            f'  <is_agonistic>{"true" if is_agonistic else "false"}</is_agonistic>\n'
            f'</research-proposal>'
        )
        return rewritten

    processed = RESEARCH_PROPOSAL_PATTERN.sub(replace_proposal, response_text)

    if processed != original_text:
        message_repo.update_content(message_id, processed)

    return processed

