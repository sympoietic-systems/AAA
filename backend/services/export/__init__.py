"""Export Service Package — Conversation and Research export generators."""

from backend.services.export.conversation import ConversationExportBuilder
from backend.services.export.research import ResearchExportBuilder


class ExportService:
    """Unified facade for conversation and research export generators."""

    INSTRUCTIONS = ConversationExportBuilder.INSTRUCTIONS

    # Conversation export delegation
    build_export = staticmethod(ConversationExportBuilder.build_export)
    _build_frontmatter = staticmethod(ConversationExportBuilder._build_frontmatter)
    _build_metadata = staticmethod(ConversationExportBuilder._build_metadata)
    _build_summary = staticmethod(ConversationExportBuilder._build_summary)
    _build_memory_nodes = staticmethod(ConversationExportBuilder._build_memory_nodes)
    _build_tree = staticmethod(ConversationExportBuilder._build_tree)
    _build_messages = staticmethod(ConversationExportBuilder._build_messages)
    _build_notes = staticmethod(ConversationExportBuilder._build_notes)
    _build_export_meta = staticmethod(ConversationExportBuilder._build_export_meta)

    # Research export delegation
    build_research_report_content = staticmethod(ResearchExportBuilder.build_research_report_content)
    build_research_export = staticmethod(ResearchExportBuilder.build_research_export)
    build_research_export_json = staticmethod(ResearchExportBuilder.build_research_export_json)
    _parse_step_data = staticmethod(ResearchExportBuilder._parse_step_data)
    _extract_llm_content = staticmethod(ResearchExportBuilder._extract_llm_content)
    build_research_stages_export = staticmethod(ResearchExportBuilder.build_research_stages_export)


__all__ = ["ExportService", "ConversationExportBuilder", "ResearchExportBuilder"]
