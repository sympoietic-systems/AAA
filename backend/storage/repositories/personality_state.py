import json
from datetime import datetime, timezone
from typing import Optional

from backend.storage.connection import with_connection
from backend.storage.models import PersonalityState
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_personality_state


class PersonalityStateRepository(BaseRepository):
    """Persistence for the single-row personality state table."""

    @with_connection
    def get(self, agent_id: str = "symbia") -> Optional[PersonalityState]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM personality_state WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_personality_state(row)

    @with_connection
    def upsert(self, state: PersonalityState) -> None:
        conn = self._conn()
        existing = conn.execute(
            "SELECT id FROM personality_state WHERE agent_id = ?",
            (state.agent_id,),
        ).fetchone()
        now = datetime.now(timezone.utc).isoformat()

        if existing:
            conn.execute(
                """UPDATE personality_state
                   SET aspirational_traits_json = ?,
                       active_commitment_ids_json = ?,
                       trait_computation_version = ?,
                       last_recomputed_at = ?,
                       updated_at = ?
                   WHERE agent_id = ?""",
                (state.aspirational_traits_json,
                 state.active_commitment_ids_json,
                 state.trait_computation_version,
                 state.last_recomputed_at,
                 now,
                 state.agent_id),
            )
        else:
            conn.execute(
                """INSERT OR REPLACE INTO personality_state
                   (id, agent_id, aspirational_traits_json,
                    active_commitment_ids_json, trait_computation_version,
                    last_recomputed_at, updated_at)
                   VALUES (1, ?, ?, ?, ?, ?, ?)""",
                (state.agent_id, state.aspirational_traits_json,
                 state.active_commitment_ids_json,
                 state.trait_computation_version,
                 state.last_recomputed_at, now),
            )
        conn.commit()

    @with_connection
    def get_aspirational_traits(self, agent_id: str = "symbia") -> dict:
        """Convenience: returns parsed aspirational traits dict, or empty dict."""
        state = self.get(agent_id)
        if state is None or not state.aspirational_traits_json:
            return {}
        try:
            return json.loads(state.aspirational_traits_json)
        except (json.JSONDecodeError, TypeError):
            return {}
