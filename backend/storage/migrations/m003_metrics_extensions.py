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
        try:
            conn.execute(f"ALTER TABLE conversation_metrics ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass
    for idx_col in ["deficit", "vitality"]:
        try:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_metrics_{idx_col} ON conversation_metrics({idx_col})")
        except sqlite3.OperationalError:
            pass
