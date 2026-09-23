import sqlite3

from backend.services.backup import create_verified_backup


def test_v10_online_backup_contains_wal_commits_and_restores(tmp_path):
    source = tmp_path / "source.db"
    backup_dir = tmp_path / "backups"
    connection = sqlite3.connect(source)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
    connection.execute("INSERT INTO events(value) VALUES ('before')")
    connection.commit()
    connection.execute("INSERT INTO events(value) VALUES ('wal-commit')")
    connection.commit()

    backup = create_verified_backup(source, backup_dir)

    with sqlite3.connect(backup) as restored:
        values = [row[0] for row in restored.execute("SELECT value FROM events ORDER BY id")]
        integrity = restored.execute("PRAGMA integrity_check").fetchone()[0]
    connection.close()
    assert values == ["before", "wal-commit"]
    assert integrity == "ok"


def test_backup_retention_runs_only_after_verified_publish(tmp_path):
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE value (id INTEGER PRIMARY KEY)")
    backup_dir = tmp_path / "backups"

    for _ in range(4):
        create_verified_backup(source, backup_dir, keep=2)

    assert len(list(backup_dir.glob("aaa_backup_*.db"))) == 2
    assert not list(backup_dir.glob("*.tmp"))
