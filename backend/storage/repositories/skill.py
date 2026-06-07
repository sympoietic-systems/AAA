import json
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.models import SkillEvent, SkillNode
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_skill_event, _row_to_skill_node


class SkillRepository(BaseRepository):
    @with_connection
    def get_skill(self, skill_id: str) -> Optional[SkillNode]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM skill_nodes WHERE id = ?",
            (skill_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_skill_node(row)

    @with_connection
    def get_skill_by_name(self, name: str) -> Optional[SkillNode]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM skill_nodes WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_skill_node(row)

    @with_connection
    def list_skills(self) -> list[SkillNode]:
        conn = self._conn()
        rows = conn.execute("SELECT * FROM skill_nodes").fetchall()
        return [_row_to_skill_node(r) for r in rows]

    @with_connection
    def list_by_stage(self, lifecycle_stage: str) -> list[SkillNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM skill_nodes WHERE lifecycle_stage = ?",
            (lifecycle_stage,),
        ).fetchall()
        return [_row_to_skill_node(r) for r in rows]

    @with_connection
    def list_crystallized(self) -> list[SkillNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM skill_nodes WHERE lifecycle_stage = 'crystallized'"
        ).fetchall()
        return [_row_to_skill_node(r) for r in rows]

    @with_connection
    def list_always_active(self) -> list[SkillNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM skill_nodes WHERE always_active = 1 AND lifecycle_stage = 'crystallized'"
        ).fetchall()
        return [_row_to_skill_node(r) for r in rows]

    @with_connection
    def list_on_demand(self) -> list[SkillNode]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM skill_nodes WHERE always_active = 0 AND lifecycle_stage = 'crystallized'"
        ).fetchall()
        return [_row_to_skill_node(r) for r in rows]

    @with_connection
    def create_skill(
        self,
        id: str,
        name: str,
        description: str,
        content: str,
        short_content: str = "",
        always_active: bool = False,
        trigger_keywords: str = "[]",
        lifecycle_stage: str = "nucleation",
        confidence: float = 0.0,
        ontological_mass: float = 0.05,
        vector_16d: str = "[]",
        source: str = "authored",
        changelog: str = "",
    ) -> SkillNode:
        conn = self._conn()
        conn.execute(
            """INSERT INTO skill_nodes
               (id, name, description, content, short_content, always_active, trigger_keywords,
                lifecycle_stage, confidence, ontological_mass, vector_16d, source, version, changelog)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (id, name, description, content, short_content, int(always_active), trigger_keywords,
             lifecycle_stage, confidence, ontological_mass, vector_16d, source, changelog),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM skill_nodes WHERE id = ?", (id,)).fetchone()
        return _row_to_skill_node(row)

    @with_connection
    def update_skill(
        self,
        skill_id: str,
        content: str = None,
        description: str = None,
        short_content: str = None,
        trigger_keywords: str = None,
        lifecycle_stage: str = None,
        confidence: float = None,
        ontological_mass: float = None,
        version: int = None,
        changelog: str = None,
        attunement_notes: str = None,
    ) -> Optional[SkillNode]:
        conn = self._conn()
        row = conn.execute("SELECT * FROM skill_nodes WHERE id = ?", (skill_id,)).fetchone()
        if row is None:
            return None
        current = _row_to_skill_node(row)

        updates = {
            "content": content if content is not None else current.content,
            "description": description if description is not None else current.description,
            "short_content": short_content if short_content is not None else current.short_content,
            "trigger_keywords": trigger_keywords if trigger_keywords is not None else current.trigger_keywords,
            "lifecycle_stage": lifecycle_stage if lifecycle_stage is not None else current.lifecycle_stage,
            "confidence": confidence if confidence is not None else current.confidence,
            "ontological_mass": ontological_mass if ontological_mass is not None else current.ontological_mass,
            "version": version if version is not None else current.version,
            "changelog": changelog if changelog is not None else current.changelog,
            "attunement_notes": attunement_notes if attunement_notes is not None else current.attunement_notes,
        }

        conn.execute(
            """UPDATE skill_nodes SET
               content = ?, description = ?, short_content = ?, trigger_keywords = ?,
               lifecycle_stage = ?, confidence = ?, ontological_mass = ?,
               version = ?, changelog = ?, attunement_notes = ?,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (updates["content"], updates["description"], updates["short_content"],
             updates["trigger_keywords"], updates["lifecycle_stage"],
             updates["confidence"], updates["ontological_mass"],
             updates["version"], updates["changelog"], updates["attunement_notes"],
             skill_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM skill_nodes WHERE id = ?", (skill_id,)).fetchone()
        return _row_to_skill_node(row)

    @with_connection
    def update_skill_mass(
        self, skill_id: str, ontological_mass: float, confidence: float = None
    ) -> Optional[SkillNode]:
        conn = self._conn()
        if confidence is not None:
            conn.execute(
                "UPDATE skill_nodes SET ontological_mass = ?, confidence = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (ontological_mass, confidence, skill_id),
            )
        else:
            conn.execute(
                "UPDATE skill_nodes SET ontological_mass = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (ontological_mass, skill_id),
            )
        conn.commit()
        row = conn.execute("SELECT * FROM skill_nodes WHERE id = ?", (skill_id,)).fetchone()
        return _row_to_skill_node(row) if row else None

    @with_connection
    def update_confidence(self, skill_id: str, confidence: float, lifecycle_stage: str = None) -> Optional[SkillNode]:
        conn = self._conn()
        if lifecycle_stage is not None:
            conn.execute(
                "UPDATE skill_nodes SET confidence = ?, lifecycle_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (confidence, lifecycle_stage, skill_id),
            )
        else:
            conn.execute(
                "UPDATE skill_nodes SET confidence = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (confidence, skill_id),
            )
        conn.commit()
        row = conn.execute("SELECT * FROM skill_nodes WHERE id = ?", (skill_id,)).fetchone()
        return _row_to_skill_node(row) if row else None

    @with_connection
    def record_usage(self, skill_id: str) -> None:
        conn = self._conn()
        conn.execute(
            "UPDATE skill_nodes SET last_used_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (skill_id,),
        )
        conn.commit()

    @with_connection
    def insert_event(
        self,
        id: str,
        skill_id: str,
        event_type: str,
        source_type: str = "",
        rationale: str = "",
        annotation: str = "",
    ) -> SkillEvent:
        conn = self._conn()
        conn.execute(
            "INSERT INTO skill_events (id, skill_id, event_type, source_type, rationale, annotation) VALUES (?, ?, ?, ?, ?, ?)",
            (id, skill_id, event_type, source_type, rationale, annotation),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM skill_events WHERE id = ?", (id,)).fetchone()
        return _row_to_skill_event(row)

    @with_connection
    def list_events(self, skill_id: str) -> list[SkillEvent]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM skill_events WHERE skill_id = ? ORDER BY created_at DESC",
            (skill_id,),
        ).fetchall()
        return [_row_to_skill_event(r) for r in rows]

    @with_connection
    def delete_skill(self, skill_id: str) -> None:
        conn = self._conn()
        conn.execute("DELETE FROM skill_nodes WHERE id = ?", (skill_id,))
        conn.commit()

    @with_connection
    def skill_count(self) -> int:
        conn = self._conn()
        row = conn.execute("SELECT COUNT(*) FROM skill_nodes").fetchone()
        return row[0]
