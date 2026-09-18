"""Migration 050: Recalibrate belief mass and synchronized skill values.

Restores active beliefs that suffered severe time-based atrophy during periods
of user inactivity, establishing healthy crystallization buffers:
- Core philosophical beliefs -> 1.00 mass
- Skill bridge beliefs (skill:*) -> 0.80 mass
- Synchronize skill_nodes table mass to match
- Restore any beliefs inappropriately transitioned to senescence due to disuse
"""

import sqlite3
import uuid
from datetime import UTC, datetime


def up(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    # 1. Fetch active beliefs
    cursor.execute(
        "SELECT id, label, ontological_mass, confidence, lifecycle_stage FROM belief_nodes WHERE lifecycle_stage NOT IN ('collapsed', 'faded')"
    )
    beliefs = cursor.fetchall()
    now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

    for b_id, label, mass, conf, stage in beliefs:
        is_skill = label.startswith("skill:")
        target_mass = 0.80 if is_skill else 1.00

        # Only elevate if current mass is eroded below target
        new_mass = max(float(mass), target_mass)
        new_conf = max(float(conf), 0.85)
        new_stage = "crystallized" if stage in ("senescence", "crystallized") else stage

        cursor.execute(
            """UPDATE belief_nodes
               SET ontological_mass = ?, confidence = ?, lifecycle_stage = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (new_mass, new_conf, new_stage, b_id),
        )

        # Synchronize corresponding skill in skill_nodes if this is a skill bridge
        if is_skill:
            skill_name = label.split("skill:", 1)[1]
            cursor.execute(
                """UPDATE skill_nodes
                   SET ontological_mass = ?, confidence = ?, lifecycle_stage = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE name = ? AND lifecycle_stage NOT IN ('collapsed', 'faded')""",
                (new_mass, new_conf, new_stage, skill_name),
            )

        # Record recalibration event in belief_events
        event_id = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO belief_events
               (id, timestamp, belief_id, source_type, source_id, alignment_coefficient, perturbation_magnitude, event_type, impact_score, rationale)
               VALUES (?, ?, ?, 'recalibration', 'm050_migration', 1.0, 0.0, 'recalibration', ?, ?)""",
            (
                event_id,
                now_str,
                b_id,
                round(new_mass - float(mass), 4),
                f"Migration 050: Recalibrated eroded belief mass from {float(mass):.3f} to {new_mass:.3f}",
            ),
        )

    conn.commit()
