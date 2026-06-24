import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("aaa.research_logger")


def now_utc_str() -> str:
    """Return current UTC timestamp as ISO-like string for DB insertions."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def log_research_meta(
    meta_log_repo,
    task_id: str,
    event_type: str,
    data: dict,
    branch_id: Optional[str] = None,
    step_id: Optional[str] = None,
) -> None:
    """Log a research event to the meta-log for debugging and traceability.

    Shared by SomaticResearchOrchestrator and SomaticResearchEngine.
    """
    try:
        if meta_log_repo is None:
            return
        meta_log_repo.create({
            "id": str(uuid.uuid4()),
            "task_id": task_id,
            "branch_id": branch_id if branch_id else None,
            "step_id": step_id if step_id else None,
            "event_type": event_type,
            "event_data": json.dumps(data, default=str, ensure_ascii=False),
            "created_at": now_utc_str(),
        })
    except Exception:
        logger.warning(
            "Failed to persist meta log for task %s event %s",
            task_id, event_type,
        )
