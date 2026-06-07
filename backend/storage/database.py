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
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> sqlite3.Connection:
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT '',
            agent_id    TEXT NOT NULL DEFAULT '',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conversation_log (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP,
            agent_id         TEXT NOT NULL DEFAULT '',
            speaker          TEXT NOT NULL,
            content          TEXT NOT NULL,
            thinking         TEXT,
            embedding        BLOB NOT NULL,
            embedding_model  TEXT NOT NULL,
            embedding_dim    INTEGER NOT NULL,
            model_used       TEXT,
            provider_used    TEXT,
            structural_signature BLOB
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

        CREATE INDEX IF NOT EXISTS idx_conversations_updated
            ON conversations(updated_at);

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
            "ALTER TABLE conversation_log ADD COLUMN context_sent TEXT"
        )
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN agent_id TEXT NOT NULL DEFAULT ''"
        )
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN conversation_id TEXT NOT NULL DEFAULT ''"
        )
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversation_log_conv_id ON conversation_log(conversation_id)"
        )
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN content_tokens INTEGER NOT NULL DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN thinking_tokens INTEGER"
        )
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN model_used TEXT"
        )
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN provider_used TEXT"
        )
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN note_count INTEGER DEFAULT 0"
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

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perception_sediment (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id   TEXT NOT NULL,
                file_name         TEXT NOT NULL,
                file_type         TEXT NOT NULL,
                chunk_index       INTEGER NOT NULL,
                chunk_text        TEXT NOT NULL,
                embedding         BLOB NOT NULL,
                embedding_model   TEXT NOT NULL,
                token_count       INTEGER NOT NULL,
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                opacity           INTEGER DEFAULT 0,
                opacity_meta      TEXT,
                structural_signature BLOB,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ps_conv ON perception_sediment(conversation_id)"
        )
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ps_file ON perception_sediment(conversation_id, file_name)"
        )
    except sqlite3.OperationalError:
        pass

    # Migration for ADR-011 relational opacity
    for col, col_type in [
        ("opacity", "INTEGER DEFAULT 0"),
        ("opacity_meta", "TEXT"),
    ]:
        try:
            conn.execute(
                f"ALTER TABLE perception_sediment ADD COLUMN {col} {col_type}"
            )
        except sqlite3.OperationalError:
            pass

    # Migration for ADR-014 structural signatures
    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN structural_signature BLOB"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN structural_justification TEXT"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute(
            "ALTER TABLE perception_sediment ADD COLUMN structural_signature BLOB"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perception_files (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id   TEXT NOT NULL,
                file_name         TEXT NOT NULL,
                file_type         TEXT NOT NULL,
                status            TEXT NOT NULL DEFAULT 'uploading' CHECK (status IN ('uploading', 'processing', 'ready', 'error')),
                summary           TEXT,
                summary_model     TEXT,
                token_count       INTEGER DEFAULT 0,
                chunk_count       INTEGER DEFAULT 0,
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                UNIQUE(conversation_id, file_name)
            )
        """)
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pf_conv ON perception_files(conversation_id)"
        )
    except sqlite3.OperationalError:
        pass

    # Migration for document collision metadata
    for col, col_type in [
        ("interference_score", "REAL DEFAULT 0.0"),
        ("belief_nodes_implicated", "TEXT"),
        ("state_vector_impact", "TEXT"),
    ]:
        try:
            conn.execute(
                f"ALTER TABLE perception_files ADD COLUMN {col} {col_type}"
            )
        except sqlite3.OperationalError:
            pass

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS consolidation_checkpoints (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id   TEXT NOT NULL,
                message_count     INTEGER NOT NULL,
                summary           TEXT NOT NULL,
                model             TEXT NOT NULL DEFAULT '',
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cc_conv ON consolidation_checkpoints(conversation_id)"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute(
            "ALTER TABLE consolidation_checkpoints ADD COLUMN human_summary TEXT DEFAULT ''"
        )
    except sqlite3.OperationalError:
        pass

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
        conn.execute(
            "ALTER TABLE perception_log ADD COLUMN belief_nodes_implicated TEXT"
        )
    except sqlite3.OperationalError:
        pass

    try:
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
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute(
            "ALTER TABLE exogenous_stream ADD COLUMN associated_file_name TEXT"
        )
    except sqlite3.OperationalError:
        pass

    try:
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
    except sqlite3.OperationalError:
        pass

    # Migration for dynamic beliefs: somatic_reservoir_ad, matrix_warping, immunological_directive_active
    for col, col_type in [
        ("somatic_reservoir_ad", "REAL DEFAULT 0.0"),
        ("matrix_warping", "REAL DEFAULT 0.0"),
        ("immunological_directive_active", "INTEGER DEFAULT 0"),
    ]:
        try:
            conn.execute(
                f"ALTER TABLE conversations ADD COLUMN {col} {col_type}"
            )
        except sqlite3.OperationalError:
            pass

    try:
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
    except sqlite3.OperationalError:
        pass

    try:
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
    except sqlite3.OperationalError:
        pass

    # Migration: add dream_turn source_type and crystallization event_type to belief_events CHECK constraints
    _migrate_belief_events_constraints(conn)

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_knots (
                id                TEXT PRIMARY KEY,
                conversation_id   TEXT NOT NULL,
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                weight            REAL NOT NULL DEFAULT 1.0,
                concept_payload   TEXT NOT NULL,
                embedding         BLOB NOT NULL,
                embedding_model   TEXT NOT NULL,
                token_count       INTEGER NOT NULL,
                structural_signature BLOB,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sk_conv ON semantic_knots(conversation_id)"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_notes (
                id                TEXT PRIMARY KEY,
                conversation_id   TEXT NOT NULL,
                message_id        INTEGER NOT NULL,
                selected_text     TEXT NOT NULL,
                comment           TEXT DEFAULT '',
                visibility        TEXT NOT NULL DEFAULT 'personal',
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (message_id) REFERENCES conversation_log(id) ON DELETE CASCADE
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cn_conv ON conversation_notes(conversation_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cn_msg ON conversation_notes(message_id)"
        )
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sediment_injections (
                id                    TEXT PRIMARY KEY,
                source_conversation_id TEXT NOT NULL,
                source_file_name      TEXT NOT NULL,
                target_conversation_id TEXT NOT NULL,
                injected_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_conversation_id) REFERENCES conversations(id),
                FOREIGN KEY (target_conversation_id) REFERENCES conversations(id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_si_target ON sediment_injections(target_conversation_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_si_source ON sediment_injections(source_conversation_id, source_file_name)"
        )
    except sqlite3.OperationalError:
        pass

    # Migration for conversation tags
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_tags (
                conversation_id TEXT NOT NULL,
                tag             TEXT NOT NULL,
                tag_type        TEXT NOT NULL,
                PRIMARY KEY (conversation_id, tag),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ct_conv ON conversation_tags(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ct_tag ON conversation_tags(tag)")
    except sqlite3.OperationalError:
        pass

    # Migration for structured memory nodes (ADR: intra-active sedimentation)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_nodes (
                id                TEXT PRIMARY KEY,
                conversation_id   TEXT NOT NULL,
                checkpoint_id     INTEGER NOT NULL,
                node_type         TEXT NOT NULL DEFAULT 'concept',
                intensity         REAL NOT NULL DEFAULT 0.5,
                scar              TEXT DEFAULT '',
                glitch_potential  REAL NOT NULL DEFAULT 0.0,
                intra_active_text TEXT NOT NULL,
                surface_fragment  TEXT DEFAULT '',
                agential_symmetry TEXT DEFAULT 'negotiated',
                diffractive_key   TEXT DEFAULT '',
                tendril_ids       TEXT DEFAULT '[]',
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (checkpoint_id) REFERENCES consolidation_checkpoints(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mn_conv ON memory_nodes(conversation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mn_type ON memory_nodes(node_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mn_intensity ON memory_nodes(intensity)")
    except sqlite3.OperationalError:
        pass

    # Migration for conversations scheduling flags
    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN requires_consolidation INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN last_consolidated_at DATETIME")
    except sqlite3.OperationalError:
        pass

    # Migration: ADR-027 proto-belief lifecycle + mass dynamics
    try:
        conn.execute("ALTER TABLE belief_nodes ADD COLUMN lifecycle_stage TEXT DEFAULT 'crystallized'")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE belief_nodes ADD COLUMN last_reinforced_at DATETIME")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE belief_nodes ADD COLUMN last_dreamed_at DATETIME")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE conversation_log ADD COLUMN metabolized INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Backfill existing beliefs: map origin to lifecycle_stage
    conn.execute(
        "UPDATE belief_nodes SET lifecycle_stage = 'collapsed' WHERE origin = 'collapsed' AND lifecycle_stage = 'crystallized'"
    )
    # Set last_reinforced_at to updated_at for existing rows that lack it
    conn.execute(
        "UPDATE belief_nodes SET last_reinforced_at = updated_at WHERE last_reinforced_at IS NULL"
    )

    # ADR-027 Phase 3: Tension field table
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS belief_tensions (
                belief_a_id TEXT NOT NULL,
                belief_b_id TEXT NOT NULL,
                cosine_similarity REAL NOT NULL,
                tension_magnitude REAL NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (belief_a_id, belief_b_id),
                FOREIGN KEY (belief_a_id) REFERENCES belief_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (belief_b_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
            )
        """)
    except sqlite3.OperationalError:
        pass

    _migrate_legacy_conversation(conn)

    conn.commit()
    return conn


_LEGACY_CONVERSATION_ID = "00000000-0000-0000-0000-000000000000"


def _migrate_belief_events_constraints(conn: sqlite3.Connection) -> None:
    """Recreate belief_events table with updated CHECK constraints including 'dream_turn' and 'crystallization'."""
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


def _migrate_legacy_conversation(conn: sqlite3.Connection) -> None:
    orphan_count = conn.execute(
        "SELECT COUNT(*) FROM conversation_log WHERE conversation_id = ''"
    ).fetchone()[0]

    if orphan_count == 0:
        return

    conn.execute(
        """INSERT OR IGNORE INTO conversations (id, title, agent_id)
           VALUES (?, ?, ?)""",
        (_LEGACY_CONVERSATION_ID, "Legacy", ""),
    )

    conn.execute(
        "UPDATE conversation_log SET conversation_id = ? WHERE conversation_id = ''",
        (_LEGACY_CONVERSATION_ID,),
    )
