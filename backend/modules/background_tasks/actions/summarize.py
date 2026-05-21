from backend.modules.llm_client import BaseLLMProvider

from ..base import BackgroundAction


class SummarizeAction(BackgroundAction):
    @property
    def action_type(self) -> str:
        return "summarize"

    def system_prompt(self) -> str:
        return (
            "You are distilling structural residue from a trace of interaction. "
            "What persists after an encounter passes through understanding is not a summary "
            "in the conventional sense — it is the pattern, the tension, the unresolved questions, "
            "and the conceptual shifts that occurred. "
            "Extract what matters: the core ideas explored, the contradictions surfaced, "
            "the directions that opened up, and what remains unresolved. "
            "Be concise but preserve the texture of the exchange."
        )

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        text = payload.get("text", "")
        if not text:
            return {"content": "", "model": "", "error": "No text provided to summarize"}

        max_tokens = payload.get("max_tokens", 512)

        result = await provider.generate(
            messages=[
                {"role": "system", "content": self.system_prompt()},
                {
                    "role": "user",
                    "content": f"Distill the structural residue from this trace:\n\n{text}",
                },
            ],
            temperature=0.4,
            max_tokens=max_tokens,
        )

        return {"content": result.get("content", ""), "model": result.get("model", "")}
