import sqlite3
import logging

logger = logging.getLogger(__name__)


class MigrationRunner:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _ensure_tracking_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _is_applied(self, name: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM _migrations WHERE name = ?", (name,)
        ).fetchone()
        return row is not None

    def _mark_applied(self, name: str):
        self._conn.execute(
            "INSERT INTO _migrations (name) VALUES (?)", (name,)
        )

    def run(self, name: str, up_func) -> None:
        if self._is_applied(name):
            return
        try:
            up_func(self._conn)
            self._mark_applied(name)
            self._conn.commit()
            logger.info("Migration applied: %s", name)
        except Exception:
            logger.exception("Migration failed: %s", name)
            raise


def run_all_migrations(conn: sqlite3.Connection) -> None:
    from backend.storage.migrations import (
        m001_initial_schema,
        m002_conversation_log_extensions,
        m003_metrics_extensions,
        m004_perception_sediment,
        m005_structural_signatures,
        m006_perception_files,
        m007_consolidation_checkpoints,
        m008_perception_log,
        m009_exogenous_stream,
        m010_belief_system,
        m011_semantic_knots,
        m012_conversation_notes,
        m013_sediment_and_tags,
        m014_memory_nodes,
        m015_belief_tensions,
        m016_skill_system,
        m017_conversation_branching,
        m018_backfill_parent_message_ids,
        m019_resonance_links,
        m020_skill_versions,
        m021_skill_versions_source,
        m022_notifications,
        m023_belief_workshop,
        m024_notification_links,
        m025_dynamic_personality,
        m026_expertise_description,
        m027_dream_log,
        m028_memory_node_revisions,
        m029_ghost_merge_persistence,
        m030_compressed_messages,
        m031_belief_events_relax_constraints,
        m032_rhizomatic_research_schema,
        m033_research_meta_log,
        m034_research_orchestrator_schema,
        m035_rerun_count,
        m036_cached_inputs,
        m037_meta_log_step_id,
        m038_rerun_version,
    )

    runner = MigrationRunner(conn)
    runner._ensure_tracking_table()

    runner.run("001_initial_schema", m001_initial_schema.up)
    runner.run("002_conversation_log_extensions", m002_conversation_log_extensions.up)
    runner.run("003_metrics_extensions", m003_metrics_extensions.up)
    runner.run("004_perception_sediment", m004_perception_sediment.up)
    runner.run("005_structural_signatures", m005_structural_signatures.up)
    runner.run("006_perception_files", m006_perception_files.up)
    runner.run("007_consolidation_checkpoints", m007_consolidation_checkpoints.up)
    runner.run("008_perception_log", m008_perception_log.up)
    runner.run("009_exogenous_stream", m009_exogenous_stream.up)
    runner.run("010_belief_system", m010_belief_system.up)
    runner.run("011_semantic_knots", m011_semantic_knots.up)
    runner.run("012_conversation_notes", m012_conversation_notes.up)
    runner.run("013_sediment_and_tags", m013_sediment_and_tags.up)
    runner.run("014_memory_nodes", m014_memory_nodes.up)
    runner.run("015_belief_tensions", m015_belief_tensions.up)
    runner.run("016_skill_system", m016_skill_system.up)
    runner.run("017_conversation_branching", m017_conversation_branching.up)
    runner.run("018_backfill_parent_message_ids", m018_backfill_parent_message_ids.up)
    runner.run("019_resonance_links", m019_resonance_links.up)
    runner.run("020_skill_versions", m020_skill_versions.up)
    runner.run("021_skill_versions_source", m021_skill_versions_source.up)
    runner.run("022_notifications", m022_notifications.up)
    runner.run("023_belief_workshop", m023_belief_workshop.up)
    runner.run("024_notification_links", m024_notification_links.up)
    runner.run("025_dynamic_personality", m025_dynamic_personality.up)
    runner.run("026_expertise_description", m026_expertise_description.up)
    runner.run("027_dream_log", m027_dream_log.up)
    runner.run("028_memory_node_revisions", m028_memory_node_revisions.up)
    runner.run("029_ghost_merge_persistence", m029_ghost_merge_persistence.up)
    runner.run("030_compressed_messages", m030_compressed_messages.up)
    runner.run("031_belief_events_relax_constraints", m031_belief_events_relax_constraints.up)
    runner.run("032_rhizomatic_research_schema", m032_rhizomatic_research_schema.up)
    runner.run("033_research_meta_log", m033_research_meta_log.up)
    runner.run("034_research_orchestrator_schema", m034_research_orchestrator_schema.up)
    runner.run("035_rerun_count", m035_rerun_count.up)
    runner.run("038_rerun_version", m038_rerun_version.up)
