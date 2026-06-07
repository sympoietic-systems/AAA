import sqlite3


def up(conn):
    try:
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
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE perception_log ADD COLUMN belief_nodes_implicated TEXT")
    except sqlite3.OperationalError:
        pass
