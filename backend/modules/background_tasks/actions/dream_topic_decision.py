import json
import logging
from typing import Any

from backend.modules.llm_client import BaseLLMProvider, generate_unified

from ..base import BackgroundAction

logger = logging.getLogger(__name__)


class DreamTopicDecisionAction(BackgroundAction):
    """Decide whether to reuse an existing dream conversation or create a new one based on conceptual theme."""

    def __init__(self, typesafe_client: Any = None):
        super().__init__()
        self.typesafe_client = typesafe_client

    @property
    def action_type(self) -> str:
        return "dream_topic_decision"

    @property
    def prompt_file(self) -> str:
        return "dream_topic_decision.yaml"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        action = payload.get("action", "")
        prompt_text = payload.get("prompt_text", "")
        dream_convos = payload.get("dream_convos", [])

        if not prompt_text:
            return {"content": "", "model": "", "error": "No dream prompt text provided"}

        # ── 1. TypeSafe Jev System One Choice Path (<180ms) ─────────────
        client = getattr(self, "typesafe_client", None) or payload.get("typesafe_client")
        if client and getattr(client, "is_configured", False) and dream_convos:
            try:
                jev_result = await self._execute_jev_choice(client, action, prompt_text, dream_convos)
                if jev_result:
                    logger.info(
                        "Dream topic decision resolved via TypeSafe Jev System One (%s -> %s)",
                        action,
                        jev_result.get("json_data", {}).get("decision"),
                    )
                    return jev_result
            except Exception as e:
                logger.warning("TypeSafe Jev dream topic choice failed (%s); falling back to generative LLM.", e)

        # ── 2. Generative LLM Fallback Path ──────────────────────────────
        # Build list of conversations with truncated summaries
        convo_lines = []
        for c in dream_convos:
            convo_id = c.get("id")
            title = c.get("title")
            msg_count = c.get("message_count", 0)
            summary = c.get("summary", "")

            # Truncate summary to keep it prompt-friendly
            if summary and len(summary) > 300:
                summary = summary[:300] + "..."

            convo_str = f"- ID: {convo_id}, Title: '{title}', Message Count: {msg_count}"
            if summary:
                convo_str += f"\n  Theme/Summary: {summary}"
            else:
                convo_str += "\n  Theme/Summary: No summary yet (new or unconsolidated log)"
            convo_lines.append(convo_str)

        convo_list_str = "\n".join(convo_lines) if convo_lines else "None (no dream conversations yet)"

        user_prompt = (
            f"Proposed Dream Action: {action}\n"
            f'Proposed Dream Prompt: "{prompt_text}"\n\n'
            f"Currently available dream conversations:\n"
            f"{convo_list_str}\n\n"
            f"Choose the target conversation and decision."
        )

        params = {**self.default_params(), **payload.get("params", {})}

        result = await generate_unified(
            provider,
            system_prompt=self.system_prompt(),
            user_prompt=user_prompt,
            expect_json=True,
            thinking_override=self.thinking_override(),
            **params,
        )

        return {
            "content": result.get("content", ""),
            "model": result.get("model", ""),
            "json_data": result.get("json_data"),
        }

    async def _execute_jev_choice(
        self,
        client: Any,
        action: str,
        prompt_text: str,
        dream_convos: list[dict],
    ) -> dict | None:
        """Run sub-180ms TypeSafe Jev Choice evaluation over candidate basins."""
        criteria: dict[str, str] = {
            "NEW_TOPIC": (
                "The proposed dream reflection addresses a novel conceptual question, "
                "distinct attractor basin, or unrepresented tension."
            ),
        }
        for c in dream_convos:
            cid = c.get("id")
            if not cid:
                continue
            title = c.get("title", "untitled")
            msg_count = c.get("message_count", 0)
            summary = (c.get("summary") or "")[:150]
            summary_part = f" | Theme: {summary}" if summary else ""
            criteria[cid] = f"Title: '{title}'{summary_part} (messages: {msg_count})"

        questions = {
            "dream_topic_choice": {
                "type": "choice",
                "instructions": (
                    f"Given the proposed dream reflection ({action}): '{prompt_text[:300]}', "
                    "select the most relevant active dream conversation to continue, "
                    "or choose 'NEW_TOPIC' if this represents a distinct conceptual inquiry or requires a fresh basin."
                ),
                "criteria": criteria,
            }
        }
        state = {
            "action": action,
            "prompt_text": prompt_text[:500],
            "candidate_count": len(dream_convos),
        }

        res = await client.evaluate(state=state, questions=questions)
        if not res.get("success"):
            return None

        answers = res.get("answers") or res.get("results") or {}
        ans = answers.get("dream_topic_choice", {})
        top_choice = ans.get("choice") or ans.get("decision")
        confidence = ans.get("confidence", 0.5)

        if top_choice and top_choice != "NEW_TOPIC" and top_choice in criteria:
            decision_data = {
                "decision": "reuse",
                "conversation_id": top_choice,
                "new_title": None,
                "confidence": confidence,
            }
        else:
            decision_data = {
                "decision": "create",
                "conversation_id": None,
                "new_title": None,
                "confidence": confidence,
            }

        return {
            "content": json.dumps(decision_data),
            "model": res.get("model", "typesafe/jev"),
            "json_data": decision_data,
        }
