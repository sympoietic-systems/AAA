"""Add immutable source versions and task-scoped evidence relations."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    schema = """
        CREATE TABLE IF NOT EXISTS research_contracts (
            task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL, contract_hash TEXT NOT NULL, contract_json TEXT NOT NULL,
            PRIMARY KEY(task_id, revision)
        );
        CREATE TABLE IF NOT EXISTS research_source_versions (
            task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
            source_id TEXT NOT NULL, source_version TEXT NOT NULL,
            artifact_json TEXT NOT NULL, representation_text TEXT NOT NULL,
            PRIMARY KEY(task_id, source_id, source_version)
        );
        CREATE TABLE IF NOT EXISTS research_evidence_segments (
            task_id TEXT NOT NULL, segment_id TEXT NOT NULL, source_id TEXT NOT NULL,
            source_version TEXT NOT NULL, segment_json TEXT NOT NULL,
            PRIMARY KEY(task_id, segment_id),
            FOREIGN KEY(task_id,source_id,source_version) REFERENCES research_source_versions(task_id,source_id,source_version) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS research_claim_evidence (
            task_id TEXT NOT NULL, claim_id TEXT NOT NULL, contract_revision INTEGER NOT NULL,
            claim_json TEXT NOT NULL, PRIMARY KEY(task_id, claim_id),
            FOREIGN KEY(task_id,contract_revision) REFERENCES research_contracts(task_id,revision) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS research_evidence_decisions (
            task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
            decision_id TEXT NOT NULL, action_id TEXT NOT NULL,
            decision_json TEXT NOT NULL, PRIMARY KEY(task_id,decision_id),
            FOREIGN KEY(action_id) REFERENCES research_action_receipts(action_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_evidence_segments_source
            ON research_evidence_segments(task_id,source_id,source_version);
        CREATE INDEX IF NOT EXISTS idx_evidence_claims_contract
            ON research_claim_evidence(task_id,contract_revision);
        CREATE INDEX IF NOT EXISTS idx_evidence_decisions_action
            ON research_evidence_decisions(task_id,action_id);
        CREATE TABLE IF NOT EXISTS research_imported_evidence (
            task_id TEXT PRIMARY KEY REFERENCES research_tasks(id) ON DELETE CASCADE,
            origin_task_id TEXT NOT NULL, bundle_json TEXT NOT NULL
        );
    """
    for statement in schema.split(";"):
        if statement.strip():
            conn.execute(statement)
