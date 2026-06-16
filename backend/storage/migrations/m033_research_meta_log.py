"""Create research_meta_log table for debugging and traceability.

Stores every significant action during research execution:
- Web fetch attempts (URL, method, raw result snippet)
- LLM prompts and responses
- Analysis decisions (learnings, scores, followups)
- Branch creation / status changes
- Synthesis attempts
- Errors and warnings

See: FRONTEND_DESIGN_PRINCIPLES.md (Meta Log tab)
"""

import sqlite3

RESEARCH_META_LOG_DDL = """
CREATE TABLE IF NOT EXISTS research_meta_log (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    branch_id TEXT,
    event_type TEXT NOT NULL,
    event_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (branch_id) REFERENCES research_branches(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_meta_log_task ON research_meta_log(task_id);
CREATE INDEX IF NOT EXISTS idx_meta_log_branch ON research_meta_log(branch_id);
CREATE INDEX IF NOT EXISTS idx_meta_log_type ON research_meta_log(event_type);
"""


def up(conn: sqlite3.Connection) -> None:
    conn.executescript(RESEARCH_META_LOG_DDL)
    conn.commit()
