import sqlite3

from backend.storage.migrations import (
    MigrationRunner,
    m050_baseline_schema,
    run_all_migrations,
)


def test_migration_053_applies_to_existing_production_db():
    conn = sqlite3.connect(":memory:")
    try:
        runner = MigrationRunner(conn)
        runner._ensure_tracking_table()

        # 1. Initialize full baseline schema as prod did
        m050_baseline_schema.up(conn)
        for name in m050_baseline_schema.HISTORICAL_MIGRATIONS:
            runner._mark_applied(name)

        # Mark 051 and 052 migrations as already applied on production
        runner._mark_applied("051_activation_provenance")
        runner._mark_applied("051_add_pole_vacancy_rupture_skill")
        runner._mark_applied("052_research_action_receipts")

        # Simulate the pre-053 state where conversation_metrics lacks the new columns:
        # Re-create conversation_metrics without cpi, teachback_ratio, actionability, collapse_pressure
        conn.execute("DROP TABLE conversation_metrics")
        conn.execute("""
            CREATE TABLE conversation_metrics (
                message_id INTEGER PRIMARY KEY REFERENCES conversation_log(id),
                s_t REAL NOT NULL,
                novelty REAL NOT NULL,
                rolling_entropy REAL,
                coupling REAL,
                agent_divergence REAL,
                deficit REAL NOT NULL,
                reverse_perturbation REAL,
                surprise_index REAL,
                mutual_perturbation REAL,
                vitality REAL,
                phase_shifts TEXT,
                boringness REAL,
                conceptual_velocity REAL,
                divergence_resolution_ratio REAL,
                paskian_health REAL,
                temperature_rec REAL,
                presence_penalty_rec REAL,
                frequency_penalty_rec REAL,
                homeostatic_state TEXT
            )
        """)
        # Insert a historical message and metric row before m053 runs
        conn.execute(
            "INSERT INTO conversation_log (id, speaker, content, embedding, embedding_model, embedding_dim) VALUES (10, 'human', 'let us design and test the plan', X'00', 'test', 1)"
        )
        conn.execute("""
            INSERT INTO conversation_metrics (
                message_id, s_t, novelty, deficit, boringness, conceptual_velocity
            ) VALUES (10, 0.4, 0.5, 0.2, 0.38, 0.60)
        """)
        conn.commit()

        # Verify m053 is NOT applied yet
        assert not runner._is_applied("053_add_cpi_teachback_actionability_collapse_pressure")

        # Run migration runner: this simulates deployment on production!
        run_all_migrations(conn)

        # 1. Assert m053 is now marked applied
        assert runner._is_applied("053_add_cpi_teachback_actionability_collapse_pressure")

        # 2. Assert columns now exist in conversation_metrics
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(conversation_metrics)")
        cols = {row[1] for row in cursor.fetchall()}
        assert "cpi" in cols
        assert "teachback_ratio" in cols
        assert "actionability" in cols
        assert "collapse_pressure" in cols
        assert "phase_transition_magnitude" in cols

        # 3. Assert historical row 10 was automatically backfilled!
        backfilled_row = conn.execute(
            "SELECT collapse_pressure, actionability, teachback_ratio, cpi FROM conversation_metrics WHERE message_id = 10"
        ).fetchone()
        assert backfilled_row[0] == 0.38  # collapse_pressure backfilled from boringness
        assert backfilled_row[1] == 0.85  # actionability backfilled from content keywords
        assert backfilled_row[2] == 0.50  # teachback_ratio default
        assert backfilled_row[3] is not None and backfilled_row[3] > 0  # cpi computed

        # 4. Assert new insert with new columns works
        conn.execute(
            "INSERT INTO conversation_log (id, speaker, content, embedding, embedding_model, embedding_dim) VALUES (1, 'human', 'hi', X'00', 'test', 1)"
        )
        conn.execute("""
            INSERT INTO conversation_metrics (
                message_id, s_t, novelty, deficit, cpi, teachback_ratio, actionability, collapse_pressure
            ) VALUES (1, 0.5, 0.5, 0.2, 0.45, 0.60, 0.70, 0.15)
        """)
        row = conn.execute(
            "SELECT cpi, teachback_ratio, actionability, collapse_pressure FROM conversation_metrics WHERE message_id = 1"
        ).fetchone()
        assert row[0] == 0.45
        assert row[1] == 0.60
        assert row[2] == 0.70
        assert row[3] == 0.15

        # 5. Assert idempotency
        run_all_migrations(conn)
    finally:
        conn.close()


def test_migration_053_propagates_backfill_database_errors():
    import pytest

    from backend.storage.migrations import m053_add_cpi_teachback_actionability_collapse_pressure as migration

    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            "CREATE TABLE conversation_metrics (message_id INTEGER, boringness REAL, conceptual_velocity REAL)"
        )
        with pytest.raises(sqlite3.OperationalError, match="conversation_log"):
            migration.up(conn)
    finally:
        conn.close()
