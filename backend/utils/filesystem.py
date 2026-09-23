import os
from datetime import UTC, datetime

from backend.utils.security import safe_resolve_path, sanitize_filename, sanitize_identifier

UPLOAD_DIR = os.path.join("backend", "data", "uploads")


def get_upload_conversation_dir(conversation_id: str) -> str:
    safe_conv_id = sanitize_identifier(conversation_id, field_name="conversation_id")
    conv_dir = safe_resolve_path(UPLOAD_DIR, safe_conv_id)
    return str(conv_dir)


def get_upload_path(conversation_id: str, file_name: str) -> str:
    safe_conv_id = sanitize_identifier(conversation_id, field_name="conversation_id")
    safe_file_name = sanitize_filename(file_name)
    target_path = safe_resolve_path(UPLOAD_DIR, safe_conv_id, safe_file_name)
    return str(target_path)


def ensure_upload_dir(conversation_id: str) -> str:
    d = get_upload_conversation_dir(conversation_id)
    os.makedirs(d, exist_ok=True)
    return d


def to_utc(ts) -> datetime:
    if ts is None:
        return datetime.now(UTC)
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts
