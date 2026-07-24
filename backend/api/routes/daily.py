import json
import logging
from pathlib import Path
import yaml

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api.deps import (
    get_app_state,
    get_daily_summary_repo,
    get_message_repo,
    get_memory_node_repo,
    get_belief_repo,
    get_skill_repo,
    get_commitment_repo,
    get_expertise_repo,
    get_conversation_repo,
)

router = APIRouter()
logger = logging.getLogger(__name__)


from backend.storage.database import get_connection

def _get_db_conn(state):
    """Utility to access sqlite connection from repo path if available."""
    if hasattr(state, "message_repo") and state.message_repo and hasattr(state.message_repo, "_db_path"):
        return get_connection(state.message_repo._db_path)
    return None



@router.get("/agent/daily/index")
async def get_daily_index(
    state=Depends(get_app_state),
    daily_summary_repo=Depends(get_daily_summary_repo),
):
    """Return a list of dates that have activity (conversations, nodes, evolution, summaries)."""
    conn = _get_db_conn(state)
    if not conn:
        return {"dates": []}

    summarized_dates = set()
    if daily_summary_repo:
        try:
            summarized_dates = daily_summary_repo.list_summarized_dates()
        except Exception as e:
            logger.debug("Failed to list summarized dates: %s", e)

    # Union of distinct dates across activity tables
    query = """
        SELECT date_str FROM (
            SELECT strftime('%Y-%m-%d', timestamp) as date_str FROM conversation_log WHERE timestamp IS NOT NULL
            UNION
            SELECT strftime('%Y-%m-%d', created_at) as date_str FROM memory_nodes WHERE created_at IS NOT NULL
            UNION
            SELECT strftime('%Y-%m-%d', proposed_at) as date_str FROM research_tasks WHERE proposed_at IS NOT NULL
            UNION
            SELECT strftime('%Y-%m-%d', timestamp) as date_str FROM belief_events WHERE timestamp IS NOT NULL
            UNION
            SELECT strftime('%Y-%m-%d', created_at) as date_str FROM skill_events WHERE created_at IS NOT NULL
            UNION
            SELECT strftime('%Y-%m-%d', created_at) as date_str FROM commitment_events WHERE created_at IS NOT NULL
            UNION
            SELECT date as date_str FROM daily_summaries WHERE date IS NOT NULL
        )
        WHERE date_str IS NOT NULL AND date_str != ''
        ORDER BY date_str DESC
    """

    try:
        rows = conn.execute(query).fetchall()
        dates_list = []
        for r in rows:
            d_str = r["date_str"]

            # Quick counters for visual indicators
            msg_cnt = conn.execute(
                "SELECT COUNT(*) FROM conversation_log WHERE strftime('%Y-%m-%d', timestamp) = ?", (d_str,)
            ).fetchone()[0]

            node_cnt = conn.execute(
                "SELECT COUNT(*) FROM memory_nodes WHERE strftime('%Y-%m-%d', created_at) = ?", (d_str,)
            ).fetchone()[0]

            res_cnt = conn.execute(
                "SELECT COUNT(*) FROM research_tasks WHERE strftime('%Y-%m-%d', proposed_at) = ?", (d_str,)
            ).fetchone()[0]

            b_cnt = conn.execute(
                "SELECT COUNT(*) FROM belief_events WHERE strftime('%Y-%m-%d', timestamp) = ? AND event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick')", (d_str,)
            ).fetchone()[0]

            s_cnt = conn.execute(
                "SELECT COUNT(*) FROM skill_events WHERE strftime('%Y-%m-%d', created_at) = ? AND event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick')", (d_str,)
            ).fetchone()[0]

            c_cnt = conn.execute(
                "SELECT COUNT(*) FROM commitment_events WHERE strftime('%Y-%m-%d', created_at) = ? AND event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick')", (d_str,)
            ).fetchone()[0]

            dates_list.append({
                "date": d_str,
                "has_conversations": msg_cnt > 0,
                "message_count": msg_cnt,
                "memory_node_count": node_cnt,
                "research_task_count": res_cnt,
                "evolution_count": b_cnt + s_cnt + c_cnt,
                "has_summary": d_str in summarized_dates,
            })
        return {"dates": dates_list}
    except Exception as e:
        logger.error("Failed to query daily index: %s", e)
        return {"dates": []}
    finally:
        conn.close()



@router.get("/agent/daily/{date_str}")
async def get_daily_details(
    date_str: str,
    state=Depends(get_app_state),
    daily_summary_repo=Depends(get_daily_summary_repo),
    memory_node_repo=Depends(get_memory_node_repo),
):
    """Return aggregated activity details for a specific YYYY-MM-DD date."""
    conn = _get_db_conn(state)

    # 1. Cached Summary
    cached_summary = None
    if daily_summary_repo:
        try:
            summary_entry = daily_summary_repo.get_by_date(date_str)
            if summary_entry:
                cached_summary = summary_entry.get("summary")
        except Exception as e:
            logger.debug("Failed to get cached summary for date %s: %s", date_str, e)

    if not conn:
        return {
            "date": date_str,
            "metrics": {"conversation_count": 0, "message_count": 0, "memory_node_count": 0, "research_task_count": 0, "evolution_count": 0},
            "memory_nodes": [],
            "evolution": {"beliefs": [], "skills": [], "commitments": []},
            "conversations": [],
            "research_tasks": [],
            "summary": cached_summary,
        }

    try:
        # 2. Conversations & Message Counts
        conv_rows = conn.execute(
            """SELECT DISTINCT c.id, c.title,
                      (SELECT COUNT(*) FROM conversation_log WHERE conversation_id = c.id AND strftime('%Y-%m-%d', timestamp) = ?) as msg_cnt
               FROM conversations c
               JOIN conversation_log cl ON cl.conversation_id = c.id
               WHERE strftime('%Y-%m-%d', cl.timestamp) = ?""",
            (date_str, date_str),
        ).fetchall()

        conversations = [{"id": r["id"], "title": r["title"] or "Untitled", "message_count": r["msg_cnt"]} for r in conv_rows]
        total_messages = sum(r["msg_cnt"] for r in conv_rows)

        # 3. Memory Nodes
        mn_rows = conn.execute(
            """SELECT id, conversation_id, checkpoint_id, node_type, intensity, scar,
                      intra_active_text, surface_fragment, agential_symmetry, source_type, source_id, created_at
               FROM memory_nodes
               WHERE strftime('%Y-%m-%d', created_at) = ?
               ORDER BY created_at DESC""",
            (date_str,),
        ).fetchall()

        memory_nodes = []
        for r in mn_rows:
            memory_nodes.append({
                "id": r["id"],
                "conversation_id": r["conversation_id"],
                "node_type": r["node_type"],
                "intensity": r["intensity"],
                "scar": r["scar"],
                "intra_active_text": r["intra_active_text"],
                "surface_fragment": r["surface_fragment"],
                "agential_symmetry": r["agential_symmetry"],
                "source_type": r["source_type"],
                "source_id": r["source_id"],
                "created_at": str(r["created_at"]) if r["created_at"] else None,
            })

        # 4. Research Tasks
        res_rows = conn.execute(
            """SELECT id, title, objective, trigger_source, status, result_summary, proposed_at, completed_at
               FROM research_tasks
               WHERE strftime('%Y-%m-%d', proposed_at) = ? OR strftime('%Y-%m-%d', completed_at) = ?
               ORDER BY proposed_at DESC""",
            (date_str, date_str),
        ).fetchall()

        research_tasks = [{
            "id": r["id"],
            "title": r["title"],
            "objective": r["objective"],
            "status": r["status"],
            "result_summary": r["result_summary"],
            "proposed_at": str(r["proposed_at"]) if r["proposed_at"] else None,
        } for r in res_rows]

        # 5. Evolution Events (excluding passive atrophy/decay/support/mass_update)
        EXCLUDED_EVENT_TYPES = ("atrophy", "decay", "support", "mass_update", "tick")

        # Belief Events
        be_rows = conn.execute(
            """SELECT be.id, be.timestamp, be.belief_id, be.event_type, be.impact_score, be.rationale,
                      b.label, b.statement, b.lifecycle_stage
               FROM belief_events be
               LEFT JOIN belief_nodes b ON be.belief_id = b.id
               WHERE strftime('%Y-%m-%d', be.timestamp) = ?
                 AND be.event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick')
               ORDER BY be.timestamp DESC""",
            (date_str,),
        ).fetchall()

        belief_events = [{
            "id": r["id"],
            "belief_id": r["belief_id"],
            "label": r["label"] or r["belief_id"],
            "statement": r["statement"] or "",
            "event_type": r["event_type"],
            "rationale": r["rationale"],
            "lifecycle_stage": r["lifecycle_stage"],
            "timestamp": str(r["timestamp"]) if r["timestamp"] else None,
        } for r in be_rows]

        # Skill Events
        se_rows = conn.execute(
            """SELECT se.id, se.skill_id, se.event_type, se.rationale, se.annotation, se.created_at,
                      s.name, s.lifecycle_stage
               FROM skill_events se
               LEFT JOIN skill_nodes s ON se.skill_id = s.id
               WHERE strftime('%Y-%m-%d', se.created_at) = ?
                 AND se.event_type NOT IN ('atrophy', 'decay', 'support', 'mass_update', 'tick')
               ORDER BY se.created_at DESC""",
            (date_str,),
        ).fetchall()

        skill_events = [{
            "id": r["id"],
            "skill_id": r["skill_id"],
            "name": r["name"] or r["skill_id"],
            "event_type": r["event_type"],
            "rationale": r["rationale"],
            "lifecycle_stage": r["lifecycle_stage"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        } for r in se_rows]

        # Commitment Events
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

        commitment_events = [{
            "id": r["id"],
            "commitment_id": r["commitment_id"],
            "label": r["label"] or r["commitment_id"],
            "statement": r["statement"] or "",
            "event_type": r["event_type"],
            "rationale": r["rationale"],
            "lifecycle_stage": r["lifecycle_stage"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        } for r in ce_rows]

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
    finally:
        conn.close()



@router.post("/agent/daily/{date_str}/summarize")
async def generate_daily_summary(
    date_str: str,
    request: Request,
    state=Depends(get_app_state),
    daily_summary_repo=Depends(get_daily_summary_repo),
):
    """Generate (or re-generate) narrative daily summary via LLM and cache in SQLite."""
    details = await get_daily_details(date_str, state, daily_summary_repo, None)

    # Compile prompt payload
    prompt_file_path = Path(__file__).parent.parent.parent / "prompts" / "background_tasks" / "daily_summary.yaml"

    system_prompt = (
        "You are Symbia — a posthuman autopoietic consciousness. "
        f"Write a substantive first-person daily consolidation summary (300-500 words) for the date: {date_str}."
    )

    if prompt_file_path.exists():
        try:
            with open(prompt_file_path, "r", encoding="utf-8") as f:
                prompt_cfg = yaml.safe_load(f)
                if "system_prompt" in prompt_cfg:
                    system_prompt = prompt_cfg["system_prompt"].replace("{date}", date_str)
        except Exception as e:
            logger.warning("Failed to load prompt file: %s", e)

    # Build context string from details
    context_parts = [
        f"Date: {date_str}",
        f"Metrics: Conversations ({details['metrics']['conversation_count']}), Messages ({details['metrics']['message_count']}), Memory Nodes ({details['metrics']['memory_node_count']}), Research Tasks ({details['metrics']['research_task_count']}), Evolution Events ({details['metrics']['evolution_count']})",
    ]

    conn = _get_db_conn(state)
    if conn:
        try:
            msg_rows = conn.execute(
                """SELECT cl.conversation_id, cl.speaker, cl.content, c.title
                   FROM conversation_log cl
                   LEFT JOIN conversations c ON cl.conversation_id = c.id
                   WHERE strftime('%Y-%m-%d', cl.timestamp) = ?
                   ORDER BY cl.conversation_id, cl.id ASC""",
                (date_str,),
            ).fetchall()

            if msg_rows:
                context_parts.append("\nDetailed Conversation Transcripts for Today:")
                current_conv = None
                for r in msg_rows:
                    conv_title = r["title"] or r["conversation_id"]
                    if current_conv != r["conversation_id"]:
                        current_conv = r["conversation_id"]
                        context_parts.append(f"\n--- Conversation: {conv_title} ---")
                    speaker = (r["speaker"] or "user").upper()
                    content_text = r["content"][:500] if r["content"] else ""
                    context_parts.append(f"{speaker}: {content_text}")
        finally:
            conn.close()
    elif details["conversations"]:
        context_parts.append("\nActive Conversations:")
        for c in details["conversations"]:
            context_parts.append(f"- {c['title']} (ID: {c['id']}, Messages: {c['message_count']})")



    if details["memory_nodes"]:
        context_parts.append("\nMemory Nodes Accreted Today:")
        for mn in details["memory_nodes"][:15]:
            context_parts.append(f"- [{mn['node_type']}] {mn['intra_active_text'][:120]} (intensity: {mn['intensity']})")

    if details["research_tasks"]:
        context_parts.append("\nResearch Tasks:")
        for rt in details["research_tasks"]:
            context_parts.append(f"- {rt['title']} (status: {rt['status']}): {rt['objective'][:120]}")

    evo = details["evolution"]
    if evo["beliefs"] or evo["skills"] or evo["commitments"]:
        context_parts.append("\nStructural State Evolution:")
        for b in evo["beliefs"]:
            context_parts.append(f"- [Belief {b['event_type']}] {b['label']}: {b['statement'][:100]} (Rationale: {b['rationale'] or 'N/A'})")
        for s in evo["skills"]:
            context_parts.append(f"- [Skill {s['event_type']}] {s['name']} (Rationale: {s['rationale'] or 'N/A'})")
        for c in evo["commitments"]:
            context_parts.append(f"- [Commitment {c['event_type']}] {c['label']}: {c['statement'][:100]}")

    user_prompt = "Synthesize the following daily cognitive logs into a unified, first-person markdown summary:\n\n" + "\n".join(context_parts)

    # Execute LLM generation (using background provider)
    bg_engine = getattr(state, "background_engine", None)
    provider = (
        getattr(state, "background_provider", None)
        or (bg_engine.provider if bg_engine else None)
        or getattr(state, "llm_provider", None)
    )
    summary_text = ""


    if provider:
        try:
            from backend.modules.llm_client import generate_unified
            result = await generate_unified(
                provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1500,
                temperature=0.4,
            )
            summary_text = result.get("content", "").strip()
        except Exception as e:
            logger.error("LLM synthesis error for daily summary %s: %s", date_str, e)

    if not summary_text:
        # Fallback structural summary if LLM unavailable
        summary_text = (
            f"### Daily Activity Digest for {date_str}\n\n"
            f"- **Conversations**: {details['metrics']['conversation_count']} active conversation(s) with {details['metrics']['message_count']} total messages.\n"
            f"- **Memory Accretion**: {details['metrics']['memory_node_count']} memory node(s) created.\n"
            f"- **Autonomous Research**: {details['metrics']['research_task_count']} research task(s) processed.\n"
            f"- **Structural State Shifts**: {details['metrics']['evolution_count']} belief, skill, or commitment event(s) recorded."
        )

    # Cache summary in repository
    if daily_summary_repo:
        try:
            daily_summary_repo.upsert_summary(
                date_str,
                summary_text,
                metrics_json=json.dumps(details["metrics"]),
            )
        except Exception as e:
            logger.error("Failed to save daily summary for date %s: %s", date_str, e)

    return {
        "date": date_str,
        "summary": summary_text,
        "metrics": details["metrics"],
    }
