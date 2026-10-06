import sqlite3


def up(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(research_tasks)")}
    if "subresearch_policy" not in columns:
        conn.execute("ALTER TABLE research_tasks ADD COLUMN subresearch_policy TEXT NOT NULL DEFAULT 'off'")
    conn.execute("""CREATE TABLE IF NOT EXISTS research_branch_proposals (
        proposal_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
        action_id TEXT NOT NULL REFERENCES research_action_receipts(action_id) ON DELETE CASCADE,
        proposal_json TEXT NOT NULL, status TEXT NOT NULL
    )""")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_branch_proposal ON research_branch_proposals(task_id) WHERE status='pending'"
    )
