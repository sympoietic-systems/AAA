import contextlib
import sqlite3


def up(conn):
    for col, col_type in [
        ("reverse_perturbation", "REAL"),
        ("surprise_index", "REAL"),
        ("mutual_perturbation", "REAL"),
        ("vitality", "REAL"),
        ("phase_shifts", "TEXT"),
        ("boringness", "REAL"),
        ("conceptual_velocity", "REAL"),
        ("divergence_resolution_ratio", "REAL"),
        ("paskian_health", "REAL"),
    ]:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute(f"ALTER TABLE conversation_metrics ADD COLUMN {col} {col_type}")
    for idx_col in ["deficit", "vitality"]:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_metrics_{idx_col} ON conversation_metrics({idx_col})")
