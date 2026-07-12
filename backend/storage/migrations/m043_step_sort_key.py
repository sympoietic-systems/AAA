"""Add phase_group + sub_sequence columns and sort-key index to research_steps.

Replaces flat step_number with hierarchical (phase_group, query_group, sub_sequence)
composite key for correct rerun scoping and dynamic step ordering.
"""

import sqlite3

ADD_COLUMNS = """
ALTER TABLE research_steps ADD COLUMN phase_group INTEGER NOT NULL DEFAULT 0;
ALTER TABLE research_steps ADD COLUMN sub_sequence INTEGER NOT NULL DEFAULT 0;
"""

ADD_INDEX = """
CREATE INDEX IF NOT EXISTS idx_research_steps_sort
    ON research_steps(task_id, phase_group, query_group, sub_sequence);
"""


def up(conn: sqlite3.Connection) -> None:
    conn.executescript(ADD_COLUMNS)
    conn.executescript(ADD_INDEX)
    conn.commit()
