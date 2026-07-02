from backend.modules.llm_client import BaseLLMProvider, generate_unified

from ..base import BackgroundAction


class SemanticKnotAction(BackgroundAction):
    @property
    def action_type(self) -> str:
        return "semantic_knot"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        text = payload.get("text", "")
        if not text:
            return {"content": "", "model": "", "error": "No text provided"}

        params = {**self.default_params(), **payload.get("params", {})}

        result = await generate_unified(
            provider,
            system_prompt=self.system_prompt(),
            user_prompt=f"Here is the conversation segment to distill:\n\n{text}",
            thinking_override=self.thinking_override(),
            **params,
        )

        return {"content": result.get("content", ""), "model": result.get("model", "")}


