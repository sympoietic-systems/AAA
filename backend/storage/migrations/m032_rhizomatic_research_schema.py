"""Create research_tasks, research_branches, and scraped_assets tables.

Part of the Autonomous Research Engine (Phase 0).
See: docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Sections 4.7 and 7.
"""

import sqlite3

RESEARCH_TASKS_DDL = """
CREATE TABLE IF NOT EXISTS research_tasks (
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
    completed_at TIMESTAMP,

    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
    FOREIGN KEY (proposal_message_id) REFERENCES conversation_log(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status);
CREATE INDEX IF NOT EXISTS idx_research_tasks_conv ON research_tasks(conversation_id);
CREATE INDEX IF NOT EXISTS idx_research_tasks_trigger ON research_tasks(trigger_source);
CREATE INDEX IF NOT EXISTS idx_research_tasks_priority ON research_tasks(priority, proposed_at);
"""

RESEARCH_BRANCHES_DDL = """
CREATE TABLE IF NOT EXISTS research_branches (
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

CREATE INDEX IF NOT EXISTS idx_research_branches_task ON research_branches(task_id);
CREATE INDEX IF NOT EXISTS idx_research_branches_conv ON research_branches(conversation_id);
CREATE INDEX IF NOT EXISTS idx_research_branches_parent ON research_branches(parent_branch_id);
CREATE INDEX IF NOT EXISTS idx_research_branches_status ON research_branches(status);
"""

SCRAPED_ASSETS_DDL = """
CREATE TABLE IF NOT EXISTS scraped_assets (
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
    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (memory_node_id) REFERENCES memory_nodes(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_scraped_assets_branch ON scraped_assets(branch_id);
CREATE INDEX IF NOT EXISTS idx_scraped_assets_task ON scraped_assets(task_id);
CREATE INDEX IF NOT EXISTS idx_scraped_assets_node ON scraped_assets(memory_node_id);
"""


def up(conn: sqlite3.Connection) -> None:
    conn.executescript(RESEARCH_TASKS_DDL)
    conn.executescript(RESEARCH_BRANCHES_DDL)
    conn.executescript(SCRAPED_ASSETS_DDL)
    conn.commit()
