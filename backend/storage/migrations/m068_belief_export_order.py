"""Export ordering metadata; receipt payloads remain in their existing ledgers."""

import sqlite3
import uuid


def up(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS belief_export_meta (id INTEGER PRIMARY KEY CHECK(id=1), "
        "database_id TEXT NOT NULL, legacy_generation INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute("INSERT OR IGNORE INTO belief_export_meta(id,database_id) VALUES (1,?)", (str(uuid.uuid4()),))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS belief_assessment_completions (sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
        "ledger_id TEXT NOT NULL UNIQUE, "
        "index_origin TEXT NOT NULL CHECK(index_origin IN ('existing_receipt','forward_completion')))"
    )
    # Index actual existing receipts, without synthesizing any receipt, time, decision or reasoning.
    conn.execute(
        "INSERT OR IGNORE INTO belief_assessment_completions(ledger_id,index_origin) "
        "SELECT id,'existing_receipt' FROM belief_admission WHERE status='complete' ORDER BY rowid"
    )
    for operation in ("INSERT", "UPDATE"):
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS index_assessment_completion_{operation.lower()} AFTER {operation} "
            "ON belief_admission WHEN NEW.status='complete' BEGIN "
            "INSERT OR IGNORE INTO belief_assessment_completions(ledger_id,index_origin) "
            "VALUES (NEW.id,'forward_completion'); END"
        )
    for operation in ("UPDATE", "DELETE"):
        conn.execute(
            f"CREATE TRIGGER IF NOT EXISTS immutable_assessment_completion_{operation.lower()} BEFORE {operation} "
            "ON belief_assessment_completions BEGIN SELECT RAISE(ABORT,'export completion order retained'); END"
        )
        for table in ("belief_events", "belief_admission"):
            condition = (
                " WHEN OLD.assessment_id IS NULL AND OLD.status='complete'" if table == "belief_admission" else ""
            )
            conn.execute(
                f"CREATE TRIGGER IF NOT EXISTS export_legacy_{table}_{operation.lower()} AFTER {operation} "
                f"ON {table}{condition} BEGIN UPDATE belief_export_meta SET legacy_generation=legacy_generation+1 "
                "WHERE id=1; END"
            )
    for table in ("belief_nodes", "belief_proposals"):
        for operation in ("UPDATE OF agent_id", "DELETE"):
            suffix = "owner" if operation.startswith("UPDATE") else "delete"
            conn.execute(
                f"CREATE TRIGGER IF NOT EXISTS export_{table}_{suffix} AFTER {operation} ON {table} "
                "BEGIN UPDATE belief_export_meta SET legacy_generation=legacy_generation+1 WHERE id=1; END"
            )
    for table, column in (
        ("belief_encounters", "received_at"),
        ("belief_review_decisions", "timestamp"),
        ("belief_review_events", "timestamp"),
    ):
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_export_{table} ON {table}(agent_id,{column},id)")
