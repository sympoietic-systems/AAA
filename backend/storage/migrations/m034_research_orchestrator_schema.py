"""Create research_plans, research_steps, research_step_results tables.

Supports the Somatic Research Orchestrator (Phase 6).
See: docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Sections 5.8 and 19.
"""

import sqlite3

RESEARCH_PLANS_DDL = """
CREATE TABLE IF NOT EXISTS research_plans (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_research_plans_task ON research_plans(task_id);
"""

RESEARCH_STEPS_DDL = """
CREATE TABLE IF NOT EXISTS research_steps (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    step_data TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    result_summary TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES research_plans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_research_steps_task ON research_steps(task_id);
CREATE INDEX IF NOT EXISTS idx_research_steps_plan ON research_steps(plan_id);
CREATE INDEX IF NOT EXISTS idx_research_steps_status ON research_steps(status);
"""

RESEARCH_STEP_RESULTS_DDL = """
CREATE TABLE IF NOT EXISTS research_step_results (
    id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    source_url TEXT,
    source_title TEXT,
    raw_content TEXT,
    analyzed_json TEXT,
    relevance_score REAL NOT NULL DEFAULT 0.0,
    novelty_score REAL NOT NULL DEFAULT 0.0,
    raw_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (step_id) REFERENCES research_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_step_results_step ON research_step_results(step_id);
CREATE INDEX IF NOT EXISTS idx_step_results_task ON research_step_results(task_id);
"""


def up(conn: sqlite3.Connection) -> None:
    conn.executescript(RESEARCH_PLANS_DDL)
    conn.executescript(RESEARCH_STEPS_DDL)
    conn.executescript(RESEARCH_STEP_RESULTS_DDL)
    conn.commit()
