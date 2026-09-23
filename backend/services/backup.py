"""WAL-consistent SQLite backup operations."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


def create_verified_backup(source_path: str | Path, backup_dir: str | Path, *, keep: int = 3) -> Path:
    """Create an online SQLite backup, verify it, then atomically publish it."""
    source = Path(source_path).resolve()
    destination_dir = Path(backup_dir).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    destination_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    destination = destination_dir / f"aaa_backup_{stamp}.db"
    temporary = destination.with_suffix(".db.tmp")
    temporary.unlink(missing_ok=True)

    try:
        with (
            closing(sqlite3.connect(str(source), timeout=30.0)) as source_conn,
            closing(sqlite3.connect(str(temporary), timeout=30.0)) as destination_conn,
        ):
            source_conn.backup(destination_conn)
            result = destination_conn.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise sqlite3.DatabaseError(f"Backup integrity check failed: {result!r}")
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    backups = sorted(destination_dir.glob("aaa_backup_*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
    for old_backup in backups[max(1, keep) :]:
        old_backup.unlink()
    return destination
