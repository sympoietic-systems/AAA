"""Database migration runner and baseline schema management."""

import importlib
import logging
import re
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class MigrationRunner:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _ensure_tracking_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _is_applied(self, name: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM _migrations WHERE name = ?", (name,)).fetchone()
        return row is not None

    def _mark_applied(self, name: str):
        self._conn.execute("INSERT INTO _migrations (name) VALUES (?)", (name,))

    def run(self, name: str, up_func) -> None:
        if self._is_applied(name):
            return
        try:
            up_func(self._conn)
            self._mark_applied(name)
            self._conn.commit()
            logger.info("Migration applied: %s", name)
        except Exception:
            logger.exception("Migration failed: %s", name)
            raise


def run_all_migrations(conn: sqlite3.Connection) -> None:
    """Run baseline schema for fresh databases and any pending post-baseline migrations (m051+)."""
    runner = MigrationRunner(conn)
    runner._ensure_tracking_table()

    # Fast-path for fresh databases: run consolidated baseline schema (001-050 squashed)
    cur = conn.execute("SELECT COUNT(1) FROM _migrations")
    if cur.fetchone()[0] == 0:
        from backend.storage.migrations import m050_baseline_schema

        m050_baseline_schema.up(conn)
        for name in m050_baseline_schema.HISTORICAL_MIGRATIONS:
            runner._mark_applied(name)
        conn.commit()
        logger.info("Fresh database initialized with baseline schema (001-050 marked applied).")

    # Discover and apply any future migrations (m051_*.py and beyond)
    migrations_dir = Path(__file__).parent
    migration_files = sorted(migrations_dir.glob("m[0-9][0-9][0-9]_*.py"))

    for file_path in migration_files:
        stem = file_path.stem
        match = re.match(r"^m(\d{3})_(.+)$", stem)
        if not match:
            continue
        num = int(match.group(1))
        if num <= 50:
            continue  # Covered by baseline schema

        migration_name = f"{match.group(1)}_{match.group(2)}"
        if not runner._is_applied(migration_name):
            mod = importlib.import_module(f"backend.storage.migrations.{stem}")
            if hasattr(mod, "up"):
                runner.run(migration_name, mod.up)
