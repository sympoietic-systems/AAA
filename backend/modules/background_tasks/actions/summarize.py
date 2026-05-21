from backend.modules.llm_client import BaseLLMProvider

from ..base import BackgroundAction


class SummarizeAction(BackgroundAction):
    @property
    def action_type(self) -> str:
        return "summarize"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        text = payload.get("text", "")
        if not text:
            return {"content": "", "model": "", "error": "No text provided to summarize"}

        params = {**self.default_params(), **payload.get("params", {})}

        result = await provider.generate(
            messages=[
                {"role": "system", "content": self.system_prompt()},
                {
                    "role": "user",
                    "content": f"Distill the structural residue from this trace:\n\n{text}",
                },
            ],
            **params,
        )

        return {"content": result.get("content", ""), "model": result.get("model", "")}
