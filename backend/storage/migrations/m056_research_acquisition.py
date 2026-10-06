import sqlite3


def up(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS research_acquisitions (
        acquisition_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
        action_id TEXT NOT NULL REFERENCES research_action_receipts(action_id) ON DELETE CASCADE,
        receipt_json TEXT NOT NULL, outcome TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_acquisitions_action ON research_acquisitions(task_id,action_id)")
