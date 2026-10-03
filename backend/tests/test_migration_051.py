import sqlite3

from backend.storage.migrations import run_all_migrations


def test_migration_051_seeds_pole_vacancy_rupture_skill():
    conn = sqlite3.connect(":memory:")
    try:
        # Run all migrations (fresh DB runs m050 baseline + m051)
        run_all_migrations(conn)

        # 1. Assert migration tracking
        row = conn.execute("SELECT 1 FROM _migrations WHERE name = '051_add_pole_vacancy_rupture_skill'").fetchone()
        assert row is not None, "Migration 051 should be recorded in _migrations"

        # 2. Assert skill_nodes entry
        skill_row = conn.execute(
            "SELECT id, name, always_active, lifecycle_stage, trigger_keywords FROM skill_nodes WHERE id = 'pole-vacancy-rupture'"
        ).fetchone()
        assert skill_row is not None, "Skill pole-vacancy-rupture should exist in skill_nodes"
        assert skill_row[1] == "pole-vacancy-rupture"
        assert skill_row[2] == 0  # On-demand, not always_active
        assert skill_row[3] == "crystallized"
        assert "pole_vacancy" in skill_row[4]

        # 3. Assert belief bridge
        belief_row = conn.execute(
            "SELECT label, agent_id, lifecycle_stage FROM belief_nodes WHERE label = 'skill:pole-vacancy-rupture'"
        ).fetchone()
        assert belief_row is not None, "Belief bridge skill:pole-vacancy-rupture should exist"
        assert belief_row[1] == "symbia"
        assert belief_row[2] == "crystallized"

        # 4. Assert idempotency (running migrations again should succeed without error)
        run_all_migrations(conn)
    finally:
        conn.close()


def test_migration_051_applies_to_existing_production_db():
    conn = sqlite3.connect(":memory:")
    try:
        from backend.storage.migrations import MigrationRunner, m050_baseline_schema

        # Simulate an existing production database: baseline is up, 001-050 marked applied
        runner = MigrationRunner(conn)
        runner._ensure_tracking_table()
        m050_baseline_schema.up(conn)
        for name in m050_baseline_schema.HISTORICAL_MIGRATIONS:
            runner._mark_applied(name)
        conn.commit()

        # At this point, _migrations has 001-050, but NOT 051
        assert not runner._is_applied("051_add_pole_vacancy_rupture_skill")

        # Run all migrations - should detect and apply 051
        run_all_migrations(conn)

        assert runner._is_applied("051_add_pole_vacancy_rupture_skill")

        skill_row = conn.execute("SELECT id, name FROM skill_nodes WHERE id = 'pole-vacancy-rupture'").fetchone()
        assert skill_row is not None
        assert skill_row[1] == "pole-vacancy-rupture"
    finally:
        conn.close()
