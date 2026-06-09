import json
import logging
from backend.modules.llm_client import BaseLLMProvider
from ..base import BackgroundAction

logger = logging.getLogger(__name__)


class DreamTopicDecisionAction(BackgroundAction):
    """Decide whether to reuse an existing dream conversation or create a new one based on conceptual theme."""

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
            f"Proposed Dream Prompt: \"{prompt_text}\"\n\n"
            f"Currently available dream conversations:\n"
            f"{convo_list_str}\n\n"
            f"Choose the target conversation and decision."
        )

        params = {**self.default_params(), **payload.get("params", {})}

        result = await provider.generate(
            messages=[
                {"role": "system", "content": self.system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            **params,
        )

        content = result.get("content", "").strip()
        return {"content": content, "model": result.get("model", "")}
