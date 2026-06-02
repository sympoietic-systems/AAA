import logging
import re
import json
from backend.modules.llm_client import BaseLLMProvider
from ..base import BackgroundAction

logger = logging.getLogger(__name__)


def parse_json_safely(text: str) -> dict:
    text = text.strip()
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = text[first_brace:last_brace + 1]
    else:
        json_str = text
    return json.loads(json_str)


class DocumentCollisionAction(BackgroundAction):
    @property
    def action_type(self) -> str:
        return "document_collision"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        text = payload.get("text", "")
        file_name = payload.get("file_name", "unknown")
        active_beliefs_list = payload.get("active_beliefs_list", [])

        if not text:
            return {
                "interference_score": 0.0,
                "implicated_nodes": [],
                "state_vector_impact": [0.0] * 16,
                "error": "No text provided for collision analysis"
            }

        # Truncate text to fit prompt constraints
        truncated_text = text[:6000]
        beliefs_str = "\n".join([f"- {b}" for b in active_beliefs_list]) if active_beliefs_list else "None"

        prompt_data = self._load_prompt()
        system_prompt = self.system_prompt()
        user_tmpl = prompt_data.get("user_prompt_template", "")

        user_prompt = user_tmpl.format(
            file_name=file_name,
            active_beliefs_list=beliefs_str,
            text=truncated_text
        )

        params = {**self.default_params(), **payload.get("params", {})}

        try:
            res = await provider.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **params
            )
            content = res.get("content", "").strip()
            
            data = parse_json_safely(content)
            
            interference_score = float(data.get("interference_score", 0.0))
            implicated_nodes = data.get("implicated_nodes", [])
            state_vector_impact = data.get("state_vector_impact", [])
            
            if isinstance(state_vector_impact, list):
                while len(state_vector_impact) < 16:
                    state_vector_impact.append(0.0)
                state_vector_impact = [float(v) for v in state_vector_impact[:16]]
            else:
                state_vector_impact = [0.0] * 16

            return {
                "interference_score": interference_score,
                "implicated_nodes": implicated_nodes,
                "state_vector_impact": state_vector_impact,
                "model": res.get("model", "")
            }
        except Exception as e:
            logger.error(f"Failed to execute DocumentCollisionAction for {file_name}: {e}")
            return {
                "interference_score": 0.0,
                "implicated_nodes": [],
                "state_vector_impact": [0.0] * 16,
                "error": str(e)
            }
