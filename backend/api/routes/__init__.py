"""
Backward-compatibility re-exports for the routes package.

Business logic has moved to backend/services/. These re-exports preserve
existing imports like:
    from backend.api.routes import _process_and_summarize_file
"""

from backend.api.helpers import (  # noqa: F401
    _build_response_attachments,  # noqa: F401
    _ensure_structural_tags,  # noqa: F401
    _parse_chat_request,  # noqa: F401
)
from backend.services.chat import ChatService  # noqa: F401
from backend.services.consolidation import ConsolidationService
from backend.services.file import FileService
from backend.services.metrics import MetricsService
from backend.services.note import NoteService  # noqa: F401
from backend.services.semantic_knot import SemanticKnotService
from backend.services.title import TitleService

# Re-export with original names for backward compat
_process_and_summarize_file = FileService.process_and_summarize
_reprocess_and_summarize_file_background = FileService.reprocess_and_summarize
_run_digest_worker_subprocess = FileService.run_digest_worker
_insert_system_message = None  # moved internally, kept in files.py

# These are provided by the ChatService via static methods
_fire_and_forget_semantic_knot_compaction = SemanticKnotService.fire_and_forget
_fire_and_forget_consolidation = ConsolidationService.fire_and_forget
_store_metrics = MetricsService.store
_build_metrics_info = MetricsService.build_info
_build_recommendations = MetricsService.build_recommendations
_generate_title = TitleService.generate
_generate_title_from_conversation = TitleService.generate_from_conversation
