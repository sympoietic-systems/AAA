import contextlib
import sqlite3


def up(conn):
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perception_log (
                id                    TEXT PRIMARY KEY,
                timestamp             DATETIME DEFAULT CURRENT_TIMESTAMP,
                image_path            TEXT NOT NULL,
                artifact_type         TEXT CHECK(artifact_type IN ('journal_page', 'external_diagram', 'aesthetic_artifact')),
                raw_transcription     TEXT,
                somatic_notes         TEXT,
                diffractive_analysis  TEXT,
                g_f_score             REAL DEFAULT 0.0,
                a_d_score             REAL DEFAULT 0.0,
                structural_vector_16d TEXT NOT NULL,
                associated_day        INTEGER,
                belief_nodes_implicated TEXT
            )
        """)
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE perception_log ADD COLUMN belief_nodes_implicated TEXT")
