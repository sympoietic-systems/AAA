import sqlite3

from backend.storage.migrations.m070_belief_event_history_index import up


def test_belief_history_uses_index_without_sorting_or_scanning():
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE belief_events (id TEXT, belief_id TEXT, timestamp TEXT)")
        conn.executemany(
            "INSERT INTO belief_events VALUES (?, ?, ?)",
            [("a", "belief", "2026-01-01"), ("b", "belief", "2026-01-02"), ("c", "other", "2026-01-03")],
        )
        up(conn)
        up(conn)
        sql = "SELECT * FROM belief_events WHERE belief_id = ? ORDER BY timestamp DESC LIMIT ?"
        plan = " ".join(row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql, ("belief", 1)))
        assert "SEARCH belief_events USING INDEX idx_belief_events_belief_timestamp" in plan
        assert "TEMP B-TREE" not in plan
        assert conn.execute(sql, ("belief", 1)).fetchone()[0] == "b"
