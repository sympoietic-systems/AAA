"""Add CPI, teachback ratio, actionability, collapse pressure, and phase transition magnitude columns to conversation_metrics and backfill historical records."""

import sqlite3

from backend.modules.metrics.health import _compute_cpi
from backend.modules.sensory.intervention_policy import estimate_actionability


def up(conn: sqlite3.Connection) -> None:
    columns_to_add = [
        ("cpi", "REAL"),
        ("teachback_ratio", "REAL"),
        ("actionability", "REAL"),
        ("collapse_pressure", "REAL"),
        ("phase_transition_magnitude", "REAL"),
    ]

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(conversation_metrics)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            conn.execute(f"ALTER TABLE conversation_metrics ADD COLUMN {col_name} {col_type}")

    # 1. Backfill collapse_pressure from existing boringness values
    conn.execute("""
        UPDATE conversation_metrics
        SET collapse_pressure = boringness
        WHERE collapse_pressure IS NULL AND boringness IS NOT NULL
    """)

    # 2. Backfill actionability, teachback_ratio, and CPI for historical rows
    try:
        cursor.execute("""
            SELECT cm.message_id, cm.conceptual_velocity, cl.content
            FROM conversation_metrics cm
            JOIN conversation_log cl ON cm.message_id = cl.id
            WHERE cm.cpi IS NULL OR cm.actionability IS NULL
        """)
        rows = cursor.fetchall()

        for msg_id, velocity, content in rows:
            act = estimate_actionability(content or "")
            tb = 0.50
            cpi = _compute_cpi(velocity, tb, act) if velocity is not None else 0.10
            conn.execute("""
                UPDATE conversation_metrics
                SET actionability = ?, teachback_ratio = COALESCE(teachback_ratio, ?), cpi = ?
                WHERE message_id = ?
            """, (act, tb, cpi, msg_id))
    except sqlite3.OperationalError:
        pass
