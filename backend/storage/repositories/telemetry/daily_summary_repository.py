from backend.storage.connection import with_connection
from backend.storage.repositories.base import BaseRepository


class DailySummaryRepository(BaseRepository):
    @with_connection
    def get_by_date(self, date_str: str) -> dict | None:
        conn = self._conn()
        row = conn.execute(
            """SELECT date, summary, metrics_json, created_at, updated_at
               FROM daily_summaries
               WHERE date = ?""",
            (date_str,),
        ).fetchone()
        if row:
            return dict(row)
        return None

    @with_connection
    def upsert_summary(self, date_str: str, summary: str, metrics_json: str = "{}") -> None:
        conn = self._conn()
        conn.execute(
            """INSERT INTO daily_summaries (date, summary, metrics_json, updated_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(date) DO UPDATE SET
                   summary = excluded.summary,
                   metrics_json = excluded.metrics_json,
                   updated_at = CURRENT_TIMESTAMP""",
            (date_str, summary, metrics_json),
        )
        conn.commit()

    @with_connection
    def list_summarized_dates(self) -> set[str]:
        conn = self._conn()
        rows = conn.execute("SELECT date FROM daily_summaries").fetchall()
        return {r["date"] for r in rows}

    @with_connection
    def get_daily_index_aggregates(self, summarized_dates: set[str] | None = None) -> list[dict]:
        conn = self._conn()
        if summarized_dates is None:
            summarized_dates = {r["date"] for r in conn.execute("SELECT date FROM daily_summaries").fetchall()}

        # Single-pass aggregations grouped by date across activity tables
        msg_counts = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT strftime('%Y-%m-%d', timestamp), COUNT(*) FROM conversation_log WHERE timestamp IS NOT NULL GROUP BY 1"
            ).fetchall()
            if r[0]
        }
        node_counts = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT strftime('%Y-%m-%d', created_at), COUNT(DISTINCT id) FROM memory_nodes WHERE created_at IS NOT NULL GROUP BY 1"
            ).fetchall()
            if r[0]
        }
        res_counts = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT strftime('%Y-%m-%d', proposed_at), COUNT(*) FROM research_tasks WHERE proposed_at IS NOT NULL GROUP BY 1"
            ).fetchall()
            if r[0]
        }
        b_counts = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT strftime('%Y-%m-%d', timestamp), COUNT(*) FROM belief_events WHERE timestamp IS NOT NULL AND event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick') GROUP BY 1"
            ).fetchall()
            if r[0]
        }
        s_counts = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT strftime('%Y-%m-%d', created_at), COUNT(*) FROM skill_events WHERE created_at IS NOT NULL AND event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick') GROUP BY 1"
            ).fetchall()
            if r[0]
        }
        c_counts = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT strftime('%Y-%m-%d', created_at), COUNT(*) FROM commitment_events WHERE created_at IS NOT NULL AND event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick') GROUP BY 1"
            ).fetchall()
            if r[0]
        }

        all_dates = sorted(
            set(msg_counts)
            | set(node_counts)
            | set(res_counts)
            | set(b_counts)
            | set(s_counts)
            | set(c_counts)
            | set(summarized_dates),
            reverse=True,
        )

        dates_list = []
        for d_str in all_dates:
            msg_cnt = msg_counts.get(d_str, 0)
            node_cnt = node_counts.get(d_str, 0)
            res_cnt = res_counts.get(d_str, 0)
            evo_cnt = b_counts.get(d_str, 0) + s_counts.get(d_str, 0) + c_counts.get(d_str, 0)

            dates_list.append(
                {
                    "date": d_str,
                    "has_conversations": msg_cnt > 0,
                    "message_count": msg_cnt,
                    "memory_node_count": node_cnt,
                    "research_task_count": res_cnt,
                    "evolution_count": evo_cnt,
                    "has_summary": d_str in summarized_dates,
                }
            )
        return dates_list

    @with_connection
    def get_daily_details(self, date_str: str, cached_summary: str | None = None) -> dict:
        conn = self._conn()

        # 1. Conversations & Message Counts
        conv_rows = conn.execute(
            """SELECT DISTINCT c.id, c.title,
                      (SELECT COUNT(*) FROM conversation_log WHERE conversation_id = c.id AND strftime('%Y-%m-%d', timestamp) = ?) as msg_cnt
               FROM conversations c
               JOIN conversation_log cl ON cl.conversation_id = c.id
               WHERE strftime('%Y-%m-%d', cl.timestamp) = ?""",
            (date_str, date_str),
        ).fetchall()

        conversations = [
            {"id": r["id"], "title": r["title"] or "Untitled", "message_count": r["msg_cnt"]} for r in conv_rows
        ]
        total_messages = sum(c["message_count"] for c in conversations)

        # 2. Memory Nodes Accreted
        node_rows = conn.execute(
            """SELECT id, node_type, intra_active_text, intensity, glitch_potential, created_at
               FROM memory_nodes
               WHERE strftime('%Y-%m-%d', created_at) = ?
               ORDER BY created_at ASC""",
            (date_str,),
        ).fetchall()

        memory_nodes = [
            {
                "id": r["id"],
                "node_type": r["node_type"],
                "intra_active_text": r["intra_active_text"],
                "intensity": r["intensity"],
                "glitch_potential": r["glitch_potential"],
                "created_at": str(r["created_at"]) if r["created_at"] else None,
            }
            for r in node_rows
        ]

        # 3. Research Tasks
        res_rows = conn.execute(
            """SELECT id, title, objective, status, proposed_at, completed_at
               FROM research_tasks
               WHERE strftime('%Y-%m-%d', proposed_at) = ? OR strftime('%Y-%m-%d', completed_at) = ?
               ORDER BY proposed_at ASC""",
            (date_str, date_str),
        ).fetchall()

        research_tasks = [
            {
                "id": r["id"],
                "title": r["title"],
                "objective": r["objective"],
                "status": r["status"],
                "proposed_at": str(r["proposed_at"]) if r["proposed_at"] else None,
                "completed_at": str(r["completed_at"]) if r["completed_at"] else None,
            }
            for r in res_rows
        ]

        # 4. Evolution Events
        be_rows = conn.execute(
            """SELECT be.id, be.belief_id, be.event_type, be.rationale, be.impact_score, be.timestamp,
                      b.label, b.statement, b.lifecycle_stage
               FROM belief_events be
               LEFT JOIN belief_nodes b ON be.belief_id = b.id
               WHERE strftime('%Y-%m-%d', be.timestamp) = ?
                 AND be.event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick')
               ORDER BY be.timestamp DESC""",
            (date_str,),
        ).fetchall()

        belief_events = [
            {
                "id": r["id"],
                "belief_id": r["belief_id"],
                "label": r["label"] or r["belief_id"],
                "statement": r["statement"] or "",
                "event_type": r["event_type"],
                "rationale": r["rationale"],
                "impact_score": r["impact_score"],
                "lifecycle_stage": r["lifecycle_stage"],
                "created_at": str(r["timestamp"]) if r["timestamp"] else None,
            }
            for r in be_rows
        ]

        se_rows = conn.execute(
            """SELECT se.id, se.skill_id, se.event_type, se.rationale, se.created_at,
                      s.name, s.lifecycle_stage
               FROM skill_events se
               LEFT JOIN skill_nodes s ON se.skill_id = s.id
               WHERE strftime('%Y-%m-%d', se.created_at) = ?
                 AND se.event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick')
               ORDER BY se.created_at DESC""",
            (date_str,),
        ).fetchall()

        skill_events = [
            {
                "id": r["id"],
                "skill_id": r["skill_id"],
                "name": r["name"] or r["skill_id"],
                "event_type": r["event_type"],
                "rationale": r["rationale"],
                "lifecycle_stage": r["lifecycle_stage"],
                "created_at": str(r["created_at"]) if r["created_at"] else None,
            }
            for r in se_rows
        ]

        ce_rows = conn.execute(
            """SELECT ce.id, ce.commitment_id, ce.event_type, ce.rationale, ce.created_at,
                      c.label, c.statement, c.lifecycle_stage
               FROM commitment_events ce
               LEFT JOIN commitment_nodes c ON ce.commitment_id = c.id
               WHERE strftime('%Y-%m-%d', ce.created_at) = ?
                 AND ce.event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick')
               ORDER BY ce.created_at DESC""",
            (date_str,),
        ).fetchall()

        commitment_events = [
            {
                "id": r["id"],
                "commitment_id": r["commitment_id"],
                "label": r["label"] or r["commitment_id"],
                "statement": r["statement"] or "",
                "event_type": r["event_type"],
                "rationale": r["rationale"],
                "lifecycle_stage": r["lifecycle_stage"],
                "created_at": str(r["created_at"]) if r["created_at"] else None,
            }
            for r in ce_rows
        ]

        evolution_count = len(belief_events) + len(skill_events) + len(commitment_events)

        return {
            "date": date_str,
            "metrics": {
                "conversation_count": len(conversations),
                "message_count": total_messages,
                "memory_node_count": len(memory_nodes),
                "research_task_count": len(research_tasks),
                "evolution_count": evolution_count,
            },
            "memory_nodes": memory_nodes,
            "evolution": {
                "beliefs": belief_events,
                "skills": skill_events,
                "commitments": commitment_events,
            },
            "conversations": conversations,
            "research_tasks": research_tasks,
            "summary": cached_summary,
        }

    @with_connection
    def get_daily_transcripts(self, date_str: str) -> list[str]:
        conn = self._conn()
        msg_rows = conn.execute(
            """SELECT cl.conversation_id, cl.speaker, cl.content, c.title
               FROM conversation_log cl
               LEFT JOIN conversations c ON cl.conversation_id = c.id
               WHERE strftime('%Y-%m-%d', cl.timestamp) = ?
               ORDER BY cl.conversation_id, cl.id ASC""",
            (date_str,),
        ).fetchall()

        transcripts: list[str] = []
        if msg_rows:
            current_conv = None
            for r in msg_rows:
                conv_title = r["title"] or r["conversation_id"]
                if current_conv != r["conversation_id"]:
                    current_conv = r["conversation_id"]
                    transcripts.append(f"\n--- Conversation: {conv_title} ---")
                speaker = (r["speaker"] or "user").upper()
                content_text = r["content"][:500] if r["content"] else ""
                transcripts.append(f"{speaker}: {content_text}")
        return transcripts
