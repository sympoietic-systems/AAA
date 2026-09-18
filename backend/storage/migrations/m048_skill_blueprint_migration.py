"""Migration 048: Procedural Skills Tag Consolidation.

Deactivates always_active flag on XML tag skills (now consolidated into Tag Protocols prompt),
freeing ~2,500+ tokens per turn without modifying any skill's evolved textual content.

Evolved skill content refactoring is managed dynamically via LLM using:
    python -m backend.scripts.refactor_skills_with_llm
"""

import sqlite3
from datetime import datetime, timezone

TAG_SKILL_NAMES = {
    "self-annotation",
    "scar-fold-marginalia",
    "dream-trigger",
    "self-triggered-dreaming",
    "belief-nucleation",
    "skill-nucleation",
}


def up(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, always_active FROM skill_nodes")
    rows = cursor.fetchall()

    now_str = datetime.now(timezone.utc).isoformat()

    for row in rows:
        skill_id = row[0]
        skill_name = row[1]
        always_active = row[2]

        # Deactivate always_active on XML tag skills to free system prompt capacity
        if skill_name in TAG_SKILL_NAMES or skill_id in TAG_SKILL_NAMES:
            if always_active == 1:
                cursor.execute(
                    "UPDATE skill_nodes SET always_active = 0, updated_at = ? WHERE id = ?",
                    (now_str, skill_id),
                )
