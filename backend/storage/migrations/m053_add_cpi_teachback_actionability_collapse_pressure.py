"""Add CPI, teachback ratio, actionability, collapse pressure, and phase transition magnitude columns to conversation_metrics."""

import sqlite3


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
