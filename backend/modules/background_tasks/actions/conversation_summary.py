from backend.modules.llm_client import BaseLLMProvider, generate_unified

from ..base import BackgroundAction


class ConversationSummaryAction(BackgroundAction):
    """Generate a first-person prose summary of a conversation (separate from node consolidation)."""

    @property
    def action_type(self) -> str:
        return "conversation_summary"

    @property
    def prompt_file(self) -> str:
        return "conversation_summary.yaml"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        text = payload.get("text", "")

        if not text:
            return {"content": "", "model": "", "error": "No conversation text provided"}

        params = {**self.default_params(), **payload.get("params", {})}

        result = await generate_unified(
            provider,
            system_prompt=self.system_prompt(),
            user_prompt=f"Write a consolidation summary of this conversation:\n\n{text}",
            **params,
        )

        return {"content": result.get("content", ""), "model": result.get("model", "")}
