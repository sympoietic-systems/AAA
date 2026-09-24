"""Baseline SQLite schema (001-050 squashed) for fresh database installations.

When a fresh database is created (_migrations table is empty), this baseline schema
runs all DDL statements in a single transaction and marks historical migrations
(001 through 050) as applied. Existing production databases with active migration
records skip this baseline entirely.
"""

import sqlite3

HISTORICAL_MIGRATIONS = [
    "001_initial_schema",
    "002_conversation_log_extensions",
    "003_metrics_extensions",
    "004_perception_sediment",
    "005_structural_signatures",
    "006_perception_files",
    "007_consolidation_checkpoints",
    "008_perception_log",
    "009_exogenous_stream",
    "010_belief_system",
    "011_semantic_knots",
    "012_conversation_notes",
    "013_sediment_and_tags",
    "014_memory_nodes",
    "015_belief_tensions",
    "016_skill_system",
    "017_conversation_branching",
    "018_backfill_parent_message_ids",
    "019_resonance_links",
    "020_skill_versions",
    "021_skill_versions_source",
    "022_notifications",
    "023_belief_workshop",
    "024_notification_links",
    "025_dynamic_personality",
    "026_expertise_description",
    "027_dream_log",
    "028_memory_node_revisions",
    "029_ghost_merge_persistence",
    "030_compressed_messages",
    "031_belief_events_relax_constraints",
    "032_rhizomatic_research_schema",
    "033_research_meta_log",
    "034_research_orchestrator_schema",
    "035_rerun_count",
    "036_cached_inputs",
    "036_refusals",
    "037_meta_log_step_id",
    "038_rerun_version",
    "039_orchestrator_state",
    "040_dream_log_trigger_metadata",
    "041_unified_notes",
    "042_memory_node_source_columns",
    "043_step_sort_key",
    "044_injection_dedup",
    "045_display_name",
    "046_daily_summaries",
    "047_resource_optimization_indexes",
    "048_skill_blueprint_migration",
    "049_message_active_skills_beliefs",
    "050_recalibrate_belief_mass",
]

_BASELINE_DDL = """
CREATE TABLE belief_events (
        id TEXT PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        belief_id TEXT NOT NULL,
        source_type TEXT,
        source_id TEXT,
        alignment_coefficient REAL,
        perturbation_magnitude REAL,
        event_type TEXT,
        impact_score REAL,
        rationale TEXT,
        FOREIGN KEY(belief_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
    );

CREATE TABLE belief_nodes (
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
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, lifecycle_stage TEXT DEFAULT 'crystallized', last_reinforced_at DATETIME, last_dreamed_at DATETIME, evolved_from_proposal TEXT, genesis_materials TEXT, version INTEGER DEFAULT 1, merged_from TEXT, merged_into TEXT,
                UNIQUE(agent_id, label)
            );

CREATE TABLE belief_proposals (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL DEFAULT 'symbia',
                provisional_statement TEXT NOT NULL,
                source_trace TEXT NOT NULL, -- JSON formatted list of source trace objects
                initial_signature TEXT NOT NULL, -- JSON formatted 16D vector
                nucleation_mass REAL DEFAULT 0.1,
                confidence REAL DEFAULT 0.15,
                status TEXT CHECK(status IN ('pending', 'refined', 'rejected', 'adopted')) DEFAULT 'pending',
                suggested_label TEXT,
                suggested_statement TEXT,
                potential_merge_target TEXT,
                symbia_reflection TEXT,
                symbia_friction_rationale TEXT,
                rejection_rationale TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE belief_statement_versions (
                id TEXT PRIMARY KEY,
                belief_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                statement TEXT NOT NULL,
                vector_16d TEXT NOT NULL, -- JSON formatted 16D vector
                change_reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(belief_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
            );

CREATE TABLE belief_tensions (
                belief_a_id TEXT NOT NULL,
                belief_b_id TEXT NOT NULL,
                cosine_similarity REAL NOT NULL,
                tension_magnitude REAL NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (belief_a_id, belief_b_id),
                FOREIGN KEY (belief_a_id) REFERENCES belief_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (belief_b_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
            );

CREATE TABLE commitment_events (
                id TEXT PRIMARY KEY,
                commitment_id TEXT NOT NULL,
                event_type TEXT NOT NULL
                    CHECK(event_type IN (
                        'nucleation', 'crystallization', 'mass_update',
                        'statement_refinement', 'collapse'
                    )),
                rationale TEXT,
                mass_before REAL,
                mass_after REAL,
                confidence_before REAL,
                confidence_after REAL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(commitment_id) REFERENCES commitment_nodes(id) ON DELETE CASCADE
            );

CREATE TABLE commitment_nodes (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL DEFAULT 'symbia',
                label TEXT NOT NULL,
                statement TEXT NOT NULL,
                lifecycle_stage TEXT NOT NULL DEFAULT 'active'
                    CHECK(lifecycle_stage IN ('proto', 'active', 'spectral')),
                confidence REAL NOT NULL DEFAULT 0.0,
                ontological_mass REAL NOT NULL DEFAULT 1.0,
                vector_16d TEXT NOT NULL DEFAULT '[]',
                nucleation_rationale TEXT,
                collapse_rationale TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, label)
            );

CREATE TABLE compressed_messages (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id   TEXT NOT NULL,
            first_message_id  INTEGER NOT NULL,
            last_message_id   INTEGER NOT NULL,
            compressed_block  TEXT NOT NULL,
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );

CREATE TABLE consolidation_checkpoints (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id   TEXT NOT NULL,
                message_count     INTEGER NOT NULL,
                summary           TEXT NOT NULL,
                model             TEXT NOT NULL DEFAULT '',
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP, human_summary TEXT DEFAULT '', message_id INTEGER REFERENCES conversation_log(id) ON DELETE SET NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

CREATE TABLE conversation_log (
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
        , context_sent TEXT, conversation_id TEXT NOT NULL DEFAULT '', content_tokens INTEGER NOT NULL DEFAULT 0, thinking_tokens INTEGER, note_count INTEGER DEFAULT 0, structural_justification TEXT, metabolized INTEGER DEFAULT 0, parent_message_id INTEGER REFERENCES conversation_log(id) ON DELETE SET NULL, active_skills TEXT, active_beliefs TEXT);

CREATE TABLE conversation_metrics (
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

CREATE TABLE conversation_tags (
                conversation_id TEXT NOT NULL,
                tag             TEXT NOT NULL,
                tag_type        TEXT NOT NULL,
                PRIMARY KEY (conversation_id, tag),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

CREATE TABLE conversations (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT '',
            agent_id    TEXT NOT NULL DEFAULT '',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        , somatic_reservoir_ad REAL DEFAULT 0.0, matrix_warping REAL DEFAULT 0.0, immunological_directive_active INTEGER DEFAULT 0, requires_consolidation INTEGER DEFAULT 0, last_consolidated_at DATETIME);

CREATE TABLE daily_summaries (
            date TEXT PRIMARY KEY,
            summary TEXT NOT NULL,
            metrics_json TEXT DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE dream_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            action TEXT NOT NULL DEFAULT '',
            prompt_msg_id INTEGER,
            response_msg_id INTEGER,
            turns INTEGER NOT NULL DEFAULT 1,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        , trigger_reason TEXT DEFAULT '', source_conversation_id TEXT DEFAULT '');

CREATE TABLE error_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,
            module         TEXT NOT NULL,
            error_type     TEXT NOT NULL,
            error_message  TEXT NOT NULL,
            traceback      TEXT,
            context        TEXT
        );

CREATE TABLE exogenous_stream (
                id                      TEXT PRIMARY KEY,
                timestamp               DATETIME DEFAULT CURRENT_TIMESTAMP,
                query_used              TEXT NOT NULL,
                source_url              TEXT NOT NULL,
                raw_content             TEXT NOT NULL,
                interference_score      REAL DEFAULT 0.0,
                belief_nodes_implicated TEXT,
                state_vector_impact     TEXT,
                associated_file_name    TEXT
            );

CREATE TABLE expertise_nodes (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL DEFAULT 'symbia',
                domain TEXT NOT NULL,
                lifecycle_stage TEXT NOT NULL DEFAULT 'proto'
                    CHECK(lifecycle_stage IN ('proto', 'active', 'dormant')),
                ontological_mass REAL NOT NULL DEFAULT 0.05,
                level_label TEXT NOT NULL DEFAULT 'nascent'
                    CHECK(level_label IN ('nascent', 'developing', 'advanced', 'dormant')),
                vector_16d TEXT NOT NULL DEFAULT '[]',
                signal_count INTEGER NOT NULL DEFAULT 0,
                last_signal_at DATETIME,
                crystallization_rationale TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, description TEXT,
                UNIQUE(agent_id, domain)
            );

CREATE TABLE memory_nodes (
                    id                TEXT NOT NULL,
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
                    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP, revision_count INTEGER NOT NULL DEFAULT 0, last_merged_at DATETIME, source_type TEXT DEFAULT 'conversation', source_id TEXT DEFAULT '',
                    PRIMARY KEY (id, checkpoint_id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (checkpoint_id) REFERENCES consolidation_checkpoints(id) ON DELETE CASCADE
                );

CREATE TABLE message_links (
                id          TEXT PRIMARY KEY,
                source_id   INTEGER NOT NULL REFERENCES conversation_log(id) ON DELETE CASCADE,
                target_id   INTEGER NOT NULL REFERENCES conversation_log(id) ON DELETE CASCADE,
                link_type   TEXT NOT NULL DEFAULT 'resonance',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            , status TEXT NOT NULL DEFAULT 'active', justification TEXT DEFAULT '');

CREATE TABLE notes (
            id              TEXT PRIMARY KEY,
            asset_type      TEXT NOT NULL,
            asset_id        TEXT NOT NULL,
            conversation_id TEXT,
            selected_text   TEXT NOT NULL,
            comment         TEXT DEFAULT '',
            visibility      TEXT NOT NULL DEFAULT 'personal',
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE notifications (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                snippet TEXT NOT NULL,
                conversation_id TEXT,
                message_id INTEGER,
                parent_message_id INTEGER,
                speaker TEXT,
                source TEXT,
                read INTEGER DEFAULT 0,
                dismissed INTEGER DEFAULT 0
            , source_type TEXT, source_id TEXT);

CREATE TABLE perception_files (
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
                updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP, interference_score REAL DEFAULT 0.0, belief_nodes_implicated TEXT, state_vector_impact TEXT, display_name TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                UNIQUE(conversation_id, file_name)
            );

CREATE TABLE perception_log (
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
            );

CREATE TABLE perception_sediment (
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
            );

CREATE TABLE personality_state (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                agent_id TEXT NOT NULL DEFAULT 'symbia',
                aspirational_traits_json TEXT NOT NULL DEFAULT '{}',
                active_commitment_ids_json TEXT NOT NULL DEFAULT '[]',
                trait_computation_version INTEGER NOT NULL DEFAULT 1,
                last_recomputed_at DATETIME,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE refusals (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            conversation_id TEXT,
            message_id INTEGER,
            target_premise TEXT NOT NULL,
            incompatibility_claim TEXT NOT NULL,
            proposed_alternative TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

CREATE TABLE research_branches (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    parent_branch_id TEXT,
    query TEXT NOT NULL,
    goal TEXT NOT NULL,
    depth INTEGER NOT NULL,
    breadth INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'probing',
    vector_16d BLOB,
    homeostatic_tension REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_branch_id) REFERENCES research_branches(id) ON DELETE SET NULL
);

CREATE TABLE research_meta_log (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    branch_id TEXT,
    event_type TEXT NOT NULL,
    event_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, step_id TEXT,

    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (branch_id) REFERENCES research_branches(id) ON DELETE SET NULL
);

CREATE TABLE research_plans (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
);

CREATE TABLE research_step_results (
    id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    source_url TEXT,
    source_title TEXT,
    raw_content TEXT,
    analyzed_json TEXT,
    relevance_score REAL NOT NULL DEFAULT 0.0,
    novelty_score REAL NOT NULL DEFAULT 0.0,
    raw_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (step_id) REFERENCES research_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
);

CREATE TABLE research_steps (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    step_data TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    result_summary TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, rerun_version INTEGER NOT NULL DEFAULT 1, query_group INTEGER, query_text TEXT, phase_group INTEGER NOT NULL DEFAULT 0, sub_sequence INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES research_plans(id) ON DELETE CASCADE
);

CREATE TABLE research_tasks (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    trigger_source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    priority INTEGER NOT NULL DEFAULT 2,

    -- Execution parameters
    max_depth INTEGER NOT NULL DEFAULT 3,
    max_breadth INTEGER NOT NULL DEFAULT 4,
    is_agonistic INTEGER NOT NULL DEFAULT 0,

    -- Budget tracking
    budget_limit_usd REAL NOT NULL DEFAULT 0.50,
    budget_spent_usd REAL NOT NULL DEFAULT 0.0,

    -- Results summary
    branches_created INTEGER NOT NULL DEFAULT 0,
    assets_harvested INTEGER NOT NULL DEFAULT 0,
    lateral_flights INTEGER NOT NULL DEFAULT 0,
    bifurcation_triggered INTEGER NOT NULL DEFAULT 0,
    result_summary TEXT,

    -- Symbia proposal fields
    proposal_rationale TEXT,
    proposal_message_id INTEGER,
    approved_by TEXT,

    -- Timestamps
    proposed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP, rerun_count INTEGER NOT NULL DEFAULT 0, cached_inputs TEXT, orchestrator_state TEXT,

    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
    FOREIGN KEY (proposal_message_id) REFERENCES conversation_log(id) ON DELETE SET NULL
);

CREATE TABLE scraped_assets (
    id TEXT PRIMARY KEY,
    branch_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    memory_node_id TEXT,
    url TEXT NOT NULL,
    raw_markdown TEXT NOT NULL,
    relevance_score REAL NOT NULL DEFAULT 0.0,
    novelty_score REAL NOT NULL DEFAULT 0.0,
    diffractive_score REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (branch_id) REFERENCES research_branches(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
    -- Note: memory_node_id is a loose reference — FK to memory_nodes(id)
    -- is not possible because memory_nodes has a composite PK (id, checkpoint_id).
    -- The column is kept for logical linking; referential integrity is handled
    -- at the application layer.
);

CREATE TABLE sediment_injections (
                id                    TEXT PRIMARY KEY,
                source_conversation_id TEXT NOT NULL,
                source_file_name      TEXT NOT NULL,
                target_conversation_id TEXT NOT NULL,
                injected_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_conversation_id) REFERENCES conversations(id),
                FOREIGN KEY (target_conversation_id) REFERENCES conversations(id)
            );

CREATE TABLE semantic_knots (
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
            );

CREATE TABLE skill_events (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source_type TEXT,
                rationale TEXT,
                annotation TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(skill_id) REFERENCES skill_nodes(id) ON DELETE CASCADE
            );

CREATE TABLE skill_nodes (
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
            );

CREATE TABLE skill_versions (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                description TEXT NOT NULL,
                trigger_keywords TEXT,
                changelog TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, source TEXT DEFAULT 'user',
                FOREIGN KEY(skill_id) REFERENCES skill_nodes(id) ON DELETE CASCADE,
                UNIQUE(skill_id, version)
            );

CREATE INDEX idx_cc_conv ON consolidation_checkpoints(conversation_id);

CREATE INDEX idx_cc_message ON consolidation_checkpoints(message_id);

CREATE INDEX idx_commitment_agent ON commitment_nodes(agent_id);

CREATE INDEX idx_commitment_events_cid ON commitment_events(commitment_id);

CREATE INDEX idx_commitment_stage ON commitment_nodes(agent_id, lifecycle_stage);

CREATE INDEX idx_conversation_log_agent_ts
            ON conversation_log(agent_id, timestamp DESC);

CREATE INDEX idx_conversation_log_conv_id ON conversation_log(conversation_id);

CREATE INDEX idx_conversation_log_parent ON conversation_log(parent_message_id);

CREATE INDEX idx_conversation_log_sig
            ON conversation_log(structural_signature);

CREATE INDEX idx_conversation_timestamp
            ON conversation_log(timestamp);

CREATE INDEX idx_conversations_updated
            ON conversations(updated_at);

CREATE INDEX idx_ct_conv ON conversation_tags(conversation_id);

CREATE INDEX idx_ct_tag ON conversation_tags(tag);

CREATE INDEX idx_dream_log_conv
        ON dream_log(conversation_id, timestamp DESC)
    ;

CREATE INDEX idx_error_timestamp
            ON error_log(timestamp);

CREATE INDEX idx_expertise_agent ON expertise_nodes(agent_id);

CREATE INDEX idx_expertise_stage ON expertise_nodes(agent_id, lifecycle_stage);

CREATE INDEX idx_meta_log_branch ON research_meta_log(branch_id);

CREATE INDEX idx_meta_log_task ON research_meta_log(task_id);

CREATE INDEX idx_meta_log_type ON research_meta_log(event_type);

CREATE INDEX idx_metrics_deficit ON conversation_metrics(deficit);

CREATE INDEX idx_metrics_vitality ON conversation_metrics(vitality);

CREATE INDEX idx_ml_src ON message_links(source_id);

CREATE INDEX idx_ml_tgt ON message_links(target_id);

CREATE INDEX idx_mn_conv ON memory_nodes(conversation_id);

CREATE INDEX idx_mn_intensity ON memory_nodes(intensity);

CREATE INDEX idx_mn_source ON memory_nodes(source_type, source_id);

CREATE INDEX idx_mn_type ON memory_nodes(node_type);

CREATE INDEX idx_notes_asset ON notes(asset_type, asset_id);

CREATE INDEX idx_notes_conv ON notes(conversation_id);

CREATE INDEX idx_notifications_dismissed_ts
            ON notifications(dismissed, timestamp DESC);

CREATE INDEX idx_notifications_type
            ON notifications(type);

CREATE INDEX idx_pf_conv ON perception_files(conversation_id);

CREATE INDEX idx_ps_conv ON perception_sediment(conversation_id);

CREATE INDEX idx_ps_file ON perception_sediment(conversation_id, file_name);

CREATE INDEX idx_refusals_agent ON refusals(agent_id);

CREATE INDEX idx_refusals_conversation ON refusals(conversation_id);

CREATE INDEX idx_research_branches_conv ON research_branches(conversation_id);

CREATE INDEX idx_research_branches_parent ON research_branches(parent_branch_id);

CREATE INDEX idx_research_branches_status ON research_branches(status);

CREATE INDEX idx_research_branches_task ON research_branches(task_id);

CREATE INDEX idx_research_plans_task ON research_plans(task_id);

CREATE INDEX idx_research_steps_plan ON research_steps(plan_id);

CREATE INDEX idx_research_steps_sort
    ON research_steps(task_id, phase_group, query_group, sub_sequence);

CREATE INDEX idx_research_steps_status ON research_steps(status);

CREATE INDEX idx_research_steps_task ON research_steps(task_id);

CREATE INDEX idx_research_tasks_conv ON research_tasks(conversation_id);

CREATE INDEX idx_research_tasks_priority ON research_tasks(priority, proposed_at);

CREATE INDEX idx_research_tasks_status ON research_tasks(status);

CREATE INDEX idx_research_tasks_trigger ON research_tasks(trigger_source);

CREATE INDEX idx_scraped_assets_branch ON scraped_assets(branch_id);

CREATE INDEX idx_scraped_assets_node ON scraped_assets(memory_node_id);

CREATE INDEX idx_scraped_assets_task ON scraped_assets(task_id);

CREATE INDEX idx_si_source ON sediment_injections(source_conversation_id, source_file_name);

CREATE INDEX idx_si_target ON sediment_injections(target_conversation_id);

CREATE UNIQUE INDEX idx_si_unique_injection
            ON sediment_injections(source_conversation_id, source_file_name, target_conversation_id)
        ;

CREATE INDEX idx_sk_conv ON semantic_knots(conversation_id);

CREATE INDEX idx_step_results_step ON research_step_results(step_id);

CREATE INDEX idx_step_results_task ON research_step_results(task_id);

"""


def up(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(_BASELINE_DDL)
    conn.execute("PRAGMA foreign_keys = ON")


def recalibrate_belief_mass(conn: sqlite3.Connection) -> None:
    """Historical recalibration logic from migration 050."""
    import uuid
    from datetime import UTC, datetime

    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, label, ontological_mass, confidence, lifecycle_stage FROM belief_nodes WHERE lifecycle_stage NOT IN ('collapsed', 'faded')"
    )
    beliefs = cursor.fetchall()
    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

    for b_id, label, mass, conf, stage in beliefs:
        is_skill = label.startswith("skill:")
        target_mass = 0.80 if is_skill else 1.00

        new_mass = max(float(mass), target_mass)
        new_conf = max(float(conf), 0.85)
        new_stage = "crystallized" if stage in ("senescence", "crystallized") else stage

        cursor.execute(
            """UPDATE belief_nodes
               SET ontological_mass = ?, confidence = ?, lifecycle_stage = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (new_mass, new_conf, new_stage, b_id),
        )

        if is_skill:
            skill_name = label.split("skill:", 1)[1]
            cursor.execute(
                """UPDATE skill_nodes
                   SET ontological_mass = ?, confidence = ?, lifecycle_stage = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE name = ? AND lifecycle_stage NOT IN ('collapsed', 'faded')""",
                (new_mass, new_conf, new_stage, skill_name),
            )

        event_id = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO belief_events
               (id, timestamp, belief_id, source_type, source_id, alignment_coefficient, perturbation_magnitude, event_type, impact_score, rationale)
               VALUES (?, ?, ?, 'recalibration', 'm050_migration', 1.0, 0.0, 'recalibration', ?, ?)""",
            (
                event_id,
                now_str,
                b_id,
                round(new_mass - float(mass), 4),
                f"Migration 050: Recalibrated eroded belief mass from {float(mass):.3f} to {new_mass:.3f}",
            ),
        )

    conn.commit()
