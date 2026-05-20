import sqlite3
from pathlib import Path
from typing import Optional


def get_db_path(db_path: str) -> Path:
    path = Path(db_path)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> sqlite3.Connection:
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversation_log (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP,
            agent_id         TEXT NOT NULL DEFAULT '',
            speaker          TEXT NOT NULL,
            content          TEXT NOT NULL,
            thinking         TEXT,
            embedding        BLOB NOT NULL,
            embedding_model  TEXT NOT NULL,
            embedding_dim    INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS error_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,
            module         TEXT NOT NULL,
            error_type     TEXT NOT NULL,
            error_message  TEXT NOT NULL,
            traceback      TEXT,
            context        TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_conversation_timestamp
            ON conversation_log(timestamp);

        CREATE INDEX IF NOT EXISTS idx_error_timestamp
            ON error_log(timestamp);

        CREATE TABLE IF NOT EXISTS conversation_metrics (
            message_id        INTEGER PRIMARY KEY REFERENCES conversation_log(id),
            s_t               REAL NOT NULL,
            novelty           REAL NOT NULL,
            rolling_entropy   REAL,
            coupling          REAL,
            agent_divergence  REAL,
            deficit           REAL NOT NULL,
            reverse_perturbation REAL,
            surprise_index    REAL,
            mutual_perturbation REAL,
            vitality          REAL,
            phase_shifts      TEXT,
            boringness        REAL,
            conceptual_velocity REAL,
            divergence_resolution_ratio REAL,
            paskian_health    REAL,
            temperature_rec   REAL,
            presence_penalty_rec REAL,
            frequency_penalty_rec REAL,
            homeostatic_state TEXT
        );
    """)
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN thinking TEXT"
        )
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN agent_id TEXT NOT NULL DEFAULT ''"
        )
    except sqlite3.OperationalError:
        pass
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
            conn.execute(
                f"ALTER TABLE conversation_metrics ADD COLUMN {col} {col_type}"
            )
        except sqlite3.OperationalError:
            pass
    for idx_col in ["deficit", "vitality"]:
        try:
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_metrics_{idx_col} ON conversation_metrics({idx_col})"
            )
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return conn
