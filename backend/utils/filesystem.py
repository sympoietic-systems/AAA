import os
from datetime import datetime, timezone


UPLOAD_DIR = os.path.join("backend", "data", "uploads")


def get_upload_path(conversation_id: str, file_name: str) -> str:
    return os.path.join(UPLOAD_DIR, conversation_id, file_name)


def get_upload_conversation_dir(conversation_id: str) -> str:
    return os.path.join(UPLOAD_DIR, conversation_id)


def ensure_upload_dir(conversation_id: str) -> str:
    d = get_upload_conversation_dir(conversation_id)
    os.makedirs(d, exist_ok=True)
    return d


def to_utc(ts) -> datetime:
    if ts is None:
        return datetime.now(timezone.utc)
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts
