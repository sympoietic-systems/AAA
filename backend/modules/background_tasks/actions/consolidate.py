from backend.modules.llm_client import BaseLLMProvider

from ..base import BackgroundAction


class ConsolidateAction(BackgroundAction):
    @property
    def action_type(self) -> str:
        return "consolidate"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        messages = payload.get("context", {}).get("messages", [])
        text = payload.get("text", "")

        if not messages and not text:
            return {"content": "", "model": "", "error": "No conversation data provided"}

        if text:
            input_content = text
        else:
            formatted = []
            for msg in messages:
                speaker = msg.get("speaker", msg.get("role", "unknown"))
                content = msg.get("content", "")
                formatted.append(f"{speaker}: {content}")
            input_content = "\n".join(formatted)

        params = {**self.default_params(), **payload.get("params", {})}

        result = await provider.generate(
            messages=[
                {"role": "system", "content": self.system_prompt()},
                {
                    "role": "user",
                    "content": f"Perform sedimentation on this encounter:\n\n{input_content}",
                },
            ],
            **params,
        )

        return {"content": result.get("content", ""), "model": result.get("model", "")}
