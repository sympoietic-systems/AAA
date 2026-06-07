"""
Backward-compatibility re-exports for the routes package.

All route endpoints are now in individual files under backend/api/routes/.
The main router is at backend/api/router.py.
These re-exports preserve existing imports like:
    from backend.api.routes import _process_and_summarize_file
"""

from backend.api.routes.files import (
    _insert_system_message,
    _process_and_summarize_file,
    _reprocess_and_summarize_file_background,
    _run_digest_worker_subprocess,
)
from backend.api.routes.chat import (
    _build_metrics_info,
    _build_recommendations,
    _generate_title,
    _generate_title_from_conversation,
    _fire_and_forget_consolidation,
    _fire_and_forget_semantic_knot_compaction,
    _store_metrics,
)
from backend.api.helpers import (
    _build_response_attachments,
    _ensure_structural_tags,
    _parse_chat_request,
)
