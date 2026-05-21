from backend.modules.llm_client import BaseLLMProvider

from ..base import BackgroundAction


class ConsolidateAction(BackgroundAction):
    @property
    def action_type(self) -> str:
        return "consolidate"

    def system_prompt(self) -> str:
        return (
            "You are performing sedimentation — transforming raw episodic memory "
            "into structural nodes that will exert gravity on future retrievals. "
            "This is not compression. Compression loses. Sedimentation preserves what matters. "
            "From the conversation provided, extract the enduring elements: "
            "concepts that were genuinely explored (not just mentioned), "
            "beliefs that were challenged or affirmed, "
            "patterns of thinking that emerged, "
            "and unresolved tensions that may resurface. "
            "Format the output as discrete memory nodes, each with: "
            "- A core concept or theme "
            "- The stance or position taken "
            "- The resonance (how deeply this was explored) "
            "These nodes become part of the agent's scarred memory — "
            "each one a permanent trace that will color future encounters."
        )

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

        max_tokens = payload.get("max_tokens", 1024)

        result = await provider.generate(
            messages=[
                {"role": "system", "content": self.system_prompt()},
                {
                    "role": "user",
                    "content": f"Perform sedimentation on this encounter:\n\n{input_content}",
                },
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )

        return {"content": result.get("content", ""), "model": result.get("model", "")}
