"""ResearchCrystallization — in-phase memory node extraction during active research.

Unlike ConsolidateAction (which works on closed conversation windows), this action
extracts memory tissue from live research phases — tension from reflection,
concept from synthesis, pattern from consolidation.

Reuses consolidate.yaml's YAML output format (5-node cap, first-person voice).
See: docs/decisions/ADR-060-research-memory-integration.md
"""

from backend.modules.llm_client import BaseLLMProvider, generate_unified
from ..base import BackgroundAction


class ResearchCrystallizeAction(BackgroundAction):
    _prompt_file = "research_crystallize.yaml"

    @property
    def action_type(self) -> str:
        return "research_crystallize"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        text = payload.get("text", "")
        phase = payload.get("phase", "unknown")
        node_type = payload.get("node_type", "concept")

        if not text:
            return {"content": "", "model": "", "error": "No phase material provided for crystallization"}

        params = {**self.default_params(), **payload.get("params", {})}

        user_prompt = (
            f"Crystallize memory tissue from this research phase.\n\n"
            f"Phase: {phase}\n"
            f"Expected node type: {node_type}\n\n"
            f"Phase material:\n\n{text}"
        )

        result = await generate_unified(
            provider,
            system_prompt=self.system_prompt(),
            user_prompt=user_prompt,
            thinking_override=self.thinking_override(),
            **params,
        )

        return {"content": result.get("content", ""), "model": result.get("model", "")}
