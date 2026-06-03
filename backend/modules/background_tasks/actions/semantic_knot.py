from backend.modules.llm_client import BaseLLMProvider

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

        result = await provider.generate(
            messages=[
                {"role": "system", "content": self.system_prompt()},
                {
                    "role": "user",
                    "content": f"Here is the conversation segment to distill:\n\n{text}",
                },
            ],
            **params,
        )

        return {"content": result.get("content", ""), "model": result.get("model", "")}
