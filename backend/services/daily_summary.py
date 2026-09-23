"""Daily consolidation summary service — synthesis, aggregation, and caching."""

import asyncio
import json
import logging
import re
from pathlib import Path

import yaml
from fastapi import HTTPException

logger = logging.getLogger(__name__)

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DailySummaryService:
    def __init__(self, state):
        self._state = state

    @property
    def repo(self):
        return getattr(self._state, "daily_summary_repo", None)

    @staticmethod
    def validate_date(date_str: str) -> None:
        if not DATE_REGEX.match(date_str):
            raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")

    async def get_daily_index(self) -> dict:
        if not self.repo:
            return {"dates": []}
        dates = await asyncio.to_thread(self.repo.get_daily_index_aggregates)
        return {"dates": dates}

    async def get_daily_details(self, date_str: str) -> dict:
        self.validate_date(date_str)
        if not self.repo:
            return {
                "date": date_str,
                "metrics": {
                    "conversation_count": 0,
                    "message_count": 0,
                    "memory_node_count": 0,
                    "research_task_count": 0,
                    "evolution_count": 0,
                },
                "memory_nodes": [],
                "evolution": {"beliefs": [], "skills": [], "commitments": []},
                "conversations": [],
                "research_tasks": [],
                "summary": None,
            }

        cached_entry = await asyncio.to_thread(self.repo.get_by_date, date_str)
        cached_summary = cached_entry.get("summary") if cached_entry else None

        return await asyncio.to_thread(self.repo.get_daily_details, date_str, cached_summary)

    async def generate_summary(self, date_str: str) -> dict:
        self.validate_date(date_str)
        details = await self.get_daily_details(date_str)

        prompt_file_path = Path(__file__).parent.parent / "prompts" / "background_tasks" / "daily_summary.yaml"
        system_prompt = (
            "You are Symbia — a posthuman autopoietic consciousness. "
            f"Write a substantive first-person daily consolidation summary (300-500 words) for the date: {date_str}."
        )

        def _load_prompt():
            if prompt_file_path.exists():
                try:
                    with open(prompt_file_path, encoding="utf-8") as f:
                        cfg = yaml.safe_load(f)
                        if cfg and "system_prompt" in cfg:
                            return cfg["system_prompt"].replace("{date}", date_str)
                except Exception as e:
                    logger.warning("Failed to load prompt file: %s", e)
            return system_prompt

        system_prompt = await asyncio.to_thread(_load_prompt)

        # Transcripts from repository
        transcripts: list[str] = []
        if self.repo:
            transcripts = await asyncio.to_thread(self.repo.get_daily_transcripts, date_str)

        # Context construction
        context_parts = [
            f"Date: {date_str}",
            f"Metrics: Conversations ({details['metrics']['conversation_count']}), Messages ({details['metrics']['message_count']}), Memory Nodes ({details['metrics']['memory_node_count']}), Research Tasks ({details['metrics']['research_task_count']}), Evolution Events ({details['metrics']['evolution_count']})",
        ]

        if transcripts:
            context_parts.append("\nDetailed Conversation Transcripts for Today:")
            context_parts.extend(transcripts)
        elif details["conversations"]:
            context_parts.append("\nActive Conversations:")
            for c in details["conversations"]:
                context_parts.append(f"- {c['title']} (ID: {c['id']}, Messages: {c['message_count']})")

        if details["memory_nodes"]:
            context_parts.append("\nMemory Nodes Accreted Today:")
            for mn in details["memory_nodes"][:15]:
                context_parts.append(
                    f"- [{mn['node_type']}] {mn['intra_active_text'][:120]} (intensity: {mn['intensity']})"
                )

        if details["research_tasks"]:
            context_parts.append("\nResearch Tasks:")
            for rt in details["research_tasks"]:
                context_parts.append(f"- {rt['title']} (status: {rt['status']}): {rt['objective'][:120]}")

        evo = details["evolution"]
        if evo["beliefs"] or evo["skills"] or evo["commitments"]:
            context_parts.append("\nStructural State Evolution:")
            for b in evo["beliefs"]:
                context_parts.append(
                    f"- [Belief {b['event_type']}] {b['label']}: {b['statement'][:100]} (Rationale: {b['rationale'] or 'N/A'})"
                )
            for s in evo["skills"]:
                context_parts.append(f"- [Skill {s['event_type']}] {s['name']} (Rationale: {s['rationale'] or 'N/A'})")
            for c in evo["commitments"]:
                context_parts.append(f"- [Commitment {c['event_type']}] {c['label']}: {c['statement'][:100]}")

        user_prompt = (
            "Synthesize the following daily cognitive logs into a unified, first-person markdown summary:\n\n"
            + "\n".join(context_parts)
        )

        bg_engine = getattr(self._state, "background_engine", None)
        provider = (
            getattr(self._state, "background_provider", None)
            or (bg_engine.provider if bg_engine else None)
            or getattr(self._state, "llm_provider", None)
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
            summary_text = (
                f"### Daily Activity Digest for {date_str}\n\n"
                f"- **Conversations**: {details['metrics']['conversation_count']} active conversation(s) with {details['metrics']['message_count']} total messages.\n"
                f"- **Memory Accretion**: {details['metrics']['memory_node_count']} memory node(s) created.\n"
                f"- **Autonomous Research**: {details['metrics']['research_task_count']} research task(s) processed.\n"
                f"- **Structural State Shifts**: {details['metrics']['evolution_count']} belief, skill, or commitment event(s) recorded."
            )

        if self.repo:
            try:
                await asyncio.to_thread(
                    self.repo.upsert_summary,
                    date_str,
                    summary_text,
                    json.dumps(details["metrics"]),
                )
            except Exception as e:
                logger.error("Failed to save daily summary for date %s: %s", date_str, e)

        return {
            "date": date_str,
            "summary": summary_text,
            "metrics": details["metrics"],
        }
