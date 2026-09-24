"""Import-safe route package with lazy compatibility attributes."""


def __getattr__(name: str):
    if name in {"_build_response_attachments", "_ensure_structural_tags", "_parse_chat_request"}:
        from backend.api import helpers

        return getattr(helpers, name)
    if name in {
        "_process_and_summarize_file",
        "_reprocess_and_summarize_file_background",
        "_run_digest_worker_subprocess",
    }:
        from backend.services.file import FileService

        return {
            "_process_and_summarize_file": FileService.process_and_summarize,
            "_reprocess_and_summarize_file_background": FileService.reprocess_and_summarize,
            "_run_digest_worker_subprocess": FileService.run_digest_worker,
        }[name]
    if name == "_fire_and_forget_semantic_knot_compaction":
        from backend.services.semantic_knot import SemanticKnotService

        return SemanticKnotService.fire_and_forget
    if name == "_fire_and_forget_consolidation":
        from backend.services.consolidation import ConsolidationService

        return ConsolidationService.fire_and_forget
    if name in {"_store_metrics", "_build_metrics_info", "_build_recommendations"}:
        from backend.services.metrics import MetricsService

        return {
            "_store_metrics": MetricsService.store,
            "_build_metrics_info": MetricsService.build_info,
            "_build_recommendations": MetricsService.build_recommendations,
        }[name]
    if name in {"_generate_title", "_generate_title_from_conversation"}:
        from backend.services.title import TitleService

        return {
            "_generate_title": TitleService.generate,
            "_generate_title_from_conversation": TitleService.generate_from_conversation,
        }[name]
    if name == "_insert_system_message":
        return None
    raise AttributeError(name)
