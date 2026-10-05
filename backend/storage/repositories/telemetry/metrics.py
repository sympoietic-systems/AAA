from backend.storage.connection import with_connection
from backend.storage.models import MetricsRecord
from backend.storage.repositories.base import BaseRepository
from backend.storage.row_mappers import _row_to_metrics


class MetricsRepository(BaseRepository):
    @with_connection
    def insert(
        self,
        message_id: int,
        s_t: float,
        novelty: float,
        deficit: float,
        rolling_entropy: float | None = None,
        coupling: float | None = None,
        agent_divergence: float | None = None,
        reverse_perturbation: float | None = None,
        surprise_index: float | None = None,
        mutual_perturbation: float | None = None,
        vitality: float | None = None,
        phase_shifts: str | None = None,
        boringness: float | None = None,
        conceptual_velocity: float | None = None,
        divergence_resolution_ratio: float | None = None,
        paskian_health: float | None = None,
        temperature_rec: float | None = None,
        presence_penalty_rec: float | None = None,
        frequency_penalty_rec: float | None = None,
        homeostatic_state: str | None = None,
    ) -> MetricsRecord:
        conn = self._conn()
        conn.execute(
            """INSERT OR REPLACE INTO conversation_metrics
               (message_id, s_t, novelty, rolling_entropy, coupling,
                agent_divergence, deficit, reverse_perturbation, surprise_index,
                mutual_perturbation, vitality, phase_shifts,
                boringness, conceptual_velocity, divergence_resolution_ratio,
                paskian_health,
                temperature_rec, presence_penalty_rec, frequency_penalty_rec,
                homeostatic_state)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message_id,
                s_t,
                novelty,
                rolling_entropy,
                coupling,
                agent_divergence,
                deficit,
                reverse_perturbation,
                surprise_index,
                mutual_perturbation,
                vitality,
                phase_shifts,
                boringness,
                conceptual_velocity,
                divergence_resolution_ratio,
                paskian_health,
                temperature_rec,
                presence_penalty_rec,
                frequency_penalty_rec,
                homeostatic_state,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM conversation_metrics WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        return _row_to_metrics(row)

    @with_connection
    def get_recent(self, limit: int = 50, conversation_id: str | None = None) -> list[MetricsRecord]:
        conn = self._conn()
        if conversation_id:
            rows = conn.execute(
                """SELECT cm.* FROM conversation_metrics cm
                   JOIN conversation_log cl ON cm.message_id = cl.id
                   WHERE cl.conversation_id = ?
                   ORDER BY cm.message_id DESC LIMIT ?""",
                (conversation_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversation_metrics ORDER BY message_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_metrics(r) for r in reversed(rows)]

    @with_connection
    def get_aggregates(self, limit: int = 20, conversation_id: str | None = None) -> dict:
        conn = self._conn()
        if conversation_id:
            inner_query = """SELECT cm.* FROM conversation_metrics cm
                             JOIN conversation_log cl ON cm.message_id = cl.id
                             WHERE cl.conversation_id = ?
                             ORDER BY cm.message_id DESC LIMIT ?"""
            params: tuple = (conversation_id, limit)
        else:
            inner_query = """SELECT * FROM conversation_metrics
                             ORDER BY message_id DESC LIMIT ?"""
            params = (limit,)

        row = conn.execute(
            f"""SELECT
                 AVG(s_t) as avg_s_t,
                 AVG(novelty) as avg_novelty,
                 AVG(rolling_entropy) as avg_entropy,
                 AVG(coupling) as avg_coupling,
                 AVG(agent_divergence) as avg_divergence,
                 AVG(deficit) as avg_deficit,
                 AVG(reverse_perturbation) as avg_rev_pert,
                 AVG(surprise_index) as avg_surprise,
                 AVG(mutual_perturbation) as avg_mpi,
                 AVG(vitality) as avg_vitality,
                 AVG(boringness) as avg_boringness,
                 AVG(conceptual_velocity) as avg_velocity,
                 AVG(divergence_resolution_ratio) as avg_drr,
                 AVG(paskian_health) as avg_pask_health,
                 COUNT(*) as count
               FROM (
                 {inner_query}
               )""",
            params,
        ).fetchone()
        if row is None or row["count"] == 0:
            return {"count": 0}
        return {
            "count": row["count"],
            "avg_pairwise_similarity": round(row["avg_s_t"], 4) if row["avg_s_t"] is not None else None,
            "avg_novelty": round(row["avg_novelty"], 4) if row["avg_novelty"] is not None else None,
            "avg_rolling_entropy": round(row["avg_entropy"], 6) if row["avg_entropy"] is not None else None,
            "avg_coupling": round(row["avg_coupling"], 4) if row["avg_coupling"] is not None else None,
            "avg_agent_divergence": round(row["avg_divergence"], 4) if row["avg_divergence"] is not None else None,
            "avg_deficit": round(row["avg_deficit"], 4) if row["avg_deficit"] is not None else None,
            "avg_reverse_perturbation": round(row["avg_rev_pert"], 4) if row["avg_rev_pert"] is not None else None,
            "avg_surprise_index": round(row["avg_surprise"], 4) if row["avg_surprise"] is not None else None,
            "avg_mutual_perturbation": round(row["avg_mpi"], 4) if row["avg_mpi"] is not None else None,
            "avg_vitality": round(row["avg_vitality"], 4) if row["avg_vitality"] is not None else None,
            "avg_boringness": round(row["avg_boringness"], 4) if row["avg_boringness"] is not None else None,
            "avg_conceptual_velocity": round(row["avg_velocity"], 4) if row["avg_velocity"] is not None else None,
            "avg_drr": round(row["avg_drr"], 4) if row["avg_drr"] is not None else None,
            "avg_paskian_health": round(row["avg_pask_health"], 4) if row["avg_pask_health"] is not None else None,
        }

    @with_connection
    def get_latest(
        self, require_complete: bool = False, conversation_id: str | None = None
    ) -> MetricsRecord | None:
        conn = self._conn()
        if conversation_id:
            if require_complete:
                row = conn.execute(
                    """SELECT cm.* FROM conversation_metrics cm
                       JOIN conversation_log cl ON cm.message_id = cl.id
                       WHERE cl.conversation_id = ? AND cm.boringness IS NOT NULL
                       ORDER BY cm.message_id DESC LIMIT 1""",
                    (conversation_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT cm.* FROM conversation_metrics cm
                       JOIN conversation_log cl ON cm.message_id = cl.id
                       WHERE cl.conversation_id = ?
                       ORDER BY cm.message_id DESC LIMIT 1""",
                    (conversation_id,),
                ).fetchone()
        else:
            if require_complete:
                row = conn.execute(
                    "SELECT * FROM conversation_metrics WHERE boringness IS NOT NULL ORDER BY message_id DESC LIMIT 1"
                ).fetchone()
            else:
                row = conn.execute("SELECT * FROM conversation_metrics ORDER BY message_id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return _row_to_metrics(row)
