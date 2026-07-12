import contextlib
import sqlite3


def up(conn):
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exogenous_stream (
                id                      TEXT PRIMARY KEY,
                timestamp               DATETIME DEFAULT CURRENT_TIMESTAMP,
                query_used              TEXT NOT NULL,
                source_url              TEXT NOT NULL,
                raw_content             TEXT NOT NULL,
                interference_score      REAL DEFAULT 0.0,
                belief_nodes_implicated TEXT,
                state_vector_impact     TEXT,
                associated_file_name    TEXT
            )
        """)
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("ALTER TABLE exogenous_stream ADD COLUMN associated_file_name TEXT")
    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("""
            UPDATE exogenous_stream
            SET associated_file_name = (
                SELECT file_name FROM perception_files
                WHERE file_type = 'web_probe'
                  AND summary LIKE '%' || exogenous_stream.query_used || '%'
                LIMIT 1
            )
            WHERE associated_file_name IS NULL
        """)
