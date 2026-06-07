import sqlite3


def up(conn):
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_nodes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                content TEXT NOT NULL,
                short_content TEXT,
                always_active INTEGER DEFAULT 0,
                trigger_keywords TEXT,
                lifecycle_stage TEXT DEFAULT 'nucleation',
                confidence REAL DEFAULT 0.0 CHECK(confidence BETWEEN 0.0 AND 1.0),
                ontological_mass REAL DEFAULT 0.05,
                vector_16d TEXT,
                source TEXT CHECK(source IN ('authored', 'emergent')) DEFAULT 'authored',
                version INTEGER DEFAULT 1,
                changelog TEXT,
                attunement_notes TEXT,
                last_used_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_events (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source_type TEXT,
                rationale TEXT,
                annotation TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(skill_id) REFERENCES skill_nodes(id) ON DELETE CASCADE
            )
        """)
    except sqlite3.OperationalError:
        pass
