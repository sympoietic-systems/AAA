from backend.modules.llm_client import BaseLLMProvider, generate_unified

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

        result = await generate_unified(
            provider,
            system_prompt=self.system_prompt(),
            user_prompt=f"Perform sedimentation on this encounter:\n\n{input_content}",
            thinking_override=self.thinking_override(),
            **params,
        )

        return {"content": result.get("content", ""), "model": result.get("model", "")}


