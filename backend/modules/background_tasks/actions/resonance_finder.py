from backend.modules.llm_client import BaseLLMProvider, generate_unified
from ..base import BackgroundAction
import logging
from .document_collision import parse_json_safely

logger = logging.getLogger(__name__)


class ResonanceFinderAction(BackgroundAction):
    @property
    def action_type(self) -> str:
        return "resonance_finder"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        msg_a = payload.get("message_a", "")
        msg_b = payload.get("message_b", "")
        speaker_a = payload.get("speaker_a", "unknown")
        speaker_b = payload.get("speaker_b", "unknown")

        if not msg_a or not msg_b:
            return {"has_resonance": False, "error": "Missing message content"}

        prompt_data = self._load_prompt()
        system_prompt = self.system_prompt()
        user_tmpl = prompt_data.get("user_prompt_template", "")

        user_prompt = user_tmpl.format(
            speaker_a=speaker_a,
            content_a=msg_a,
            speaker_b=speaker_b,
            content_b=msg_b
        )

        params = {**self.default_params(), **payload.get("params", {})}

        try:
            res = await generate_unified(
                provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                expect_json=True,
                thinking_override=self.thinking_override(),
                **params
            )
            data = res.get("json_data") or {}

            # Fallback parsing if JSON wasn't fully structured by generate_unified
            if not data and res.get("content"):
                try:
                    data = parse_json_safely(res["content"])
                except Exception:
                    pass

            return {
                "has_resonance": bool(data.get("has_resonance", False)),
                "reason": data.get("reason", ""),
                "model": res.get("model", "")
            }

        except Exception as e:
            logger.error(f"Failed to execute ResonanceFinderAction: {e}")
            return {"has_resonance": False, "error": str(e)}
