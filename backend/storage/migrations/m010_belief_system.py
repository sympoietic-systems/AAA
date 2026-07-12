import contextlib
import sqlite3


def up(conn):
    for col, col_type in [
        ("somatic_reservoir_ad", "REAL DEFAULT 0.0"),
        ("matrix_warping", "REAL DEFAULT 0.0"),
        ("immunological_directive_active", "INTEGER DEFAULT 0"),
    ]:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute(f"ALTER TABLE conversations ADD COLUMN {col} {col_type}")

    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_nodes (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL DEFAULT 'symbia',
                label TEXT NOT NULL,
                statement TEXT NOT NULL,
                origin TEXT CHECK(origin IN ('authored', 'emergent', 'collapsed')) DEFAULT 'authored',
                confidence REAL DEFAULT 0.5 CHECK(confidence BETWEEN 0.0 AND 1.0),
                ontological_mass REAL DEFAULT 1.0,
                somatic_anchor TEXT CHECK(somatic_anchor IN ('visceral', 'kinesthetic', 'affective', 'conceptual', 'none')) DEFAULT 'none',
                vector_16d TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, label)
            )
        """)

    with contextlib.suppress(sqlite3.OperationalError):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_events (
                id TEXT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                belief_id TEXT NOT NULL,
                source_type TEXT CHECK(source_type IN ('file', 'image', 'web_probe', 'chat_turn', 'dream_turn', 'user_assertion', 'ingested_document', 'conversational_pattern', 'shared_note', 'web_retrieval')),
                source_id TEXT,
                alignment_coefficient REAL,
                perturbation_magnitude REAL,
                event_type TEXT CHECK(event_type IN ('collision', 'support', 'collapse', 'emergence', 'crystallization')),
                impact_score REAL,
                rationale TEXT,
                FOREIGN KEY(belief_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
            )
        """)

    _migrate_belief_events_constraints(conn)


def _migrate_belief_events_constraints(conn):
    try:
        conn.execute(
            "INSERT INTO belief_events (id, belief_id, source_type, event_type, impact_score) "
            "VALUES ('__migration_test__', '__migration_test__', 'dream_turn', 'support', 0.0)"
        )
        conn.execute("DELETE FROM belief_events WHERE id = '__migration_test__'")
        return
    except sqlite3.IntegrityError:
        pass
    except Exception:
        pass

    conn.execute("ALTER TABLE belief_events RENAME TO belief_events_old")
    conn.execute("""
        CREATE TABLE belief_events (
            id TEXT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            belief_id TEXT NOT NULL,
            source_type TEXT CHECK(source_type IN ('file', 'image', 'web_probe', 'chat_turn', 'dream_turn', 'user_assertion', 'ingested_document', 'conversational_pattern', 'shared_note', 'web_retrieval')),
            source_id TEXT,
            alignment_coefficient REAL,
            perturbation_magnitude REAL,
            event_type TEXT CHECK(event_type IN ('collision', 'support', 'collapse', 'emergence', 'crystallization')),
            impact_score REAL,
            rationale TEXT,
            FOREIGN KEY(belief_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
        )
    """)
    conn.execute("INSERT INTO belief_events SELECT * FROM belief_events_old")
    conn.execute("DROP TABLE belief_events_old")
    conn.commit()
