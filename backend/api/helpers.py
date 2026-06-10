from typing import Optional

from fastapi import Request

from backend.utils.token_counter import estimate_tokens

from .schemas import AttachmentInfo


async def _parse_chat_request(request: Request) -> tuple[str, str, str, Optional[list[dict]], Optional[bool], Optional[int], Optional[int]]:
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        content = str(form.get("content", ""))
        conversation_id = str(form.get("conversation_id", ""))
        speaker = str(form.get("speaker", "human"))
        uploaded_files = form.getlist("files")
        include_structural_scoring_raw = form.get("include_structural_scoring")
        if include_structural_scoring_raw is not None:
            include_structural_scoring = str(include_structural_scoring_raw).lower() in ("true", "1", "yes")
        else:
            include_structural_scoring = None
        max_tokens_raw = form.get("max_tokens")
        max_tokens = int(max_tokens_raw) if max_tokens_raw is not None else None
        
        parent_message_id_raw = form.get("parent_message_id")
        parent_message_id = int(parent_message_id_raw) if parent_message_id_raw is not None and str(parent_message_id_raw).strip() != "" else None

        attachments: list[dict] = []
        for f in uploaded_files:
            if not hasattr(f, "filename") or not f.filename:
                continue
            file_bytes = await f.read()
            ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "txt"
            if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"):
                file_type = "image"
            elif ext == "pdf":
                file_type = "pdf"
            elif ext == "docx":
                file_type = "docx"
            elif ext == "md":
                file_type = "md"
            elif ext == "epub":
                file_type = "epub"
            elif ext == "mobi":
                file_type = "mobi"
            else:
                file_type = "txt"
            attachments.append({
                "file_name": f.filename,
                "file_type": file_type,
                "content": file_bytes,
            })

        return content, speaker, conversation_id, (attachments if attachments else None), include_structural_scoring, max_tokens, parent_message_id

    body = await request.json()
    content = body.get("content", "")
    speaker = body.get("speaker", "human")
    conversation_id = body.get("conversation_id", "")
    json_attachments = body.get("attachments")
    include_structural_scoring = body.get("include_structural_scoring")
    max_tokens = body.get("max_tokens")
    parent_message_id_raw = body.get("parent_message_id")
    parent_message_id = int(parent_message_id_raw) if parent_message_id_raw is not None and str(parent_message_id_raw).strip() != "" else None
    
    parsed_attachments = None
    if json_attachments:
        parsed_attachments = [
            {
                "file_name": a.get("file_name", ""),
                "file_type": a.get("file_type", "txt"),
                "content": a.get("content", ""),
            }
            for a in json_attachments
        ] if isinstance(json_attachments, list) else None

    return content, speaker, conversation_id, parsed_attachments, include_structural_scoring, max_tokens, parent_message_id


def _build_response_attachments(
    attachments: list[dict] | None, result
) -> list[AttachmentInfo] | None:
    if not attachments:
        return None
    response_attachments: list[AttachmentInfo] = []
    for att in attachments:
        file_name = att.get("file_name", "")
        file_type = att.get("file_type", "txt")
        content = att.get("content", "")
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        token_count = estimate_tokens(content) if content else 0
        preview = content[:200] if content else None
        response_attachments.append(AttachmentInfo(
            file_name=file_name,
            file_type=file_type,
            token_count=token_count,
            preview=preview,
        ))
    return response_attachments if response_attachments else None


def _ensure_structural_tags(conv_repo, conversation) -> list[dict]:
    existing_tags = conv_repo.get_tags(conversation.id)
    has_structural = False
    for et in existing_tags:
        if et["tag_type"] == "structural":
            has_structural = True
            break

    if has_structural:
        return existing_tags

    title = conversation.title or ""
    if "Dream Log" in title or "Internal Diary" in title or "dream" in title.lower():
        structural_tag = "dreams"
    elif "consultation:" in title.lower():
        structural_tag = "other agents"
    else:
        structural_tag = "user conversation"

    conv_repo.add_tag(conversation.id, structural_tag, "structural")
    return conv_repo.get_tags(conversation.id)
