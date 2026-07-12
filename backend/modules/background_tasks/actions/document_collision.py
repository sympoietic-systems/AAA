import json
import logging
import re

from backend.modules.llm_client import BaseLLMProvider, generate_unified

from ..base import BackgroundAction

logger = logging.getLogger(__name__)


def parse_json_safely(text: str) -> dict:

    # 1. Clean think tags
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # 2. Extract starting from first {
    first_brace = cleaned.find("{")
    if first_brace == -1:
        return json.loads(cleaned)

    json_part = cleaned[first_brace:]

    # 3. Helper to clean control characters and commas inside string
    def sanitize(s: str) -> str:
        s = re.sub(r",\s*([\]\}])", r"\1", s)
        chars = []
        in_string = False
        escape = False
        for char in s:
            if char == '"' and not escape:
                in_string = not in_string
                chars.append(char)
            elif in_string:
                if char == "\n":
                    chars.append("\\n")
                elif char == "\t":
                    chars.append("\\t")
                elif char == "\r":
                    chars.append("\\r")
                else:
                    chars.append(char)
            else:
                chars.append(char)

            escape = not escape if (char == "\\" and in_string) else False
        return "".join(chars)

    # 4. Helper to auto-close open structures in truncated string
    def auto_close(s: str) -> str:
        stack = []
        in_string = False
        escape = False
        for char in s:
            if char == '"' and not escape:
                in_string = not in_string
            elif in_string:
                escape = not escape if char == "\\" else False
            else:
                if char in ("{", "["):
                    stack.append(char)
                elif char in ("}", "]") and stack:
                    top = stack[-1]
                    if (char == "}" and top == "{") or (char == "]" and top == "["):
                        stack.pop()

        repaired = s
        if in_string:
            repaired += '"'
        for item in reversed(stack):
            if item == "{":
                repaired += "}"
            elif item == "[":
                repaired += "]"
        return repaired

    # Try standard sanitize and parse
    sanitized = sanitize(json_part)
    try:
        return json.loads(sanitized)
    except Exception:
        pass

    # Try auto-closing and parsing
    try:
        closed = auto_close(sanitized)
        return json.loads(closed)
    except Exception:
        pass

    # Try finding last brace if any and slice/parse
    last_brace = sanitized.rfind("}")
    if last_brace != -1:
        try:
            return json.loads(sanitized[: last_brace + 1])
        except Exception:
            pass

    return json.loads(cleaned)


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
                "error": "No text provided for collision analysis",
            }

        # Truncate text to fit prompt constraints
        truncated_text = text[:6000]
        beliefs_str = "\n".join([f"- {b}" for b in active_beliefs_list]) if active_beliefs_list else "None"

        prompt_data = self._load_prompt()
        system_prompt = self.system_prompt()
        user_tmpl = prompt_data.get("user_prompt_template", "")

        user_prompt = user_tmpl.format(file_name=file_name, active_beliefs_list=beliefs_str, text=truncated_text)

        params = {**self.default_params(), **payload.get("params", {})}

        try:
            res = await generate_unified(
                provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                expect_json=True,
                thinking_override=self.thinking_override(),
                **params,
            )
            data = res.get("json_data") or {}

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
                "model": res.get("model", ""),
            }

        except Exception as e:
            logger.error(f"Failed to execute DocumentCollisionAction for {file_name}: {e}")
            return {
                "interference_score": 0.0,
                "implicated_nodes": [],
                "state_vector_impact": [0.0] * 16,
                "error": str(e),
            }
