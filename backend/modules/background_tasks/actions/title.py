import re

from backend.modules.llm_client import BaseLLMProvider

from ..base import BackgroundAction


class GenerateTitleAction(BackgroundAction):
    _prompt_file = "title.yaml"

    @property
    def action_type(self) -> str:
        return "generate_title"

    def _extract_title(self, raw: str, fallback: str) -> str:
        raw = raw.strip()
        if not raw:
            return fallback

        lines = [l.strip() for l in raw.split('\n') if l.strip()]

        if len(lines) > 1:
            for line in reversed(lines):
                cleaned = line.strip().strip('"').strip("'").strip('*').strip()
                word_count = len(cleaned.split())
                if 2 <= word_count <= 8:
                    lower = cleaned.lower()
                    if not any(lower.startswith(w) for w in ['okay', 'sure', 'the user', 'the input', 'the message', 'the conversation', 'i need', 'i should', 'let me', 'so the', 'this is', 'here is', 'i think', 'i will', 'i\'ll']):
                        return cleaned

        text = raw
        reasoning_patterns = [
            r"(?:Okay|Alright|Sure|Let me|I need|I should|I'll|We need|So|Hmm|Right|Got it)[^\.]*\.\s*",
            r"(?:The user|The input|The message|The conversation|The prompt|This|It)[^\.]*\.\s*",
            r"(?:Thinking|Reasoning|Analysis|Goal|I should|I need|I want|Let's)[^\.]*\.\s*",
            r"(?:Title should|The title|A good title|Here is|I'll give)[^\.]*\.\s*",
            r"(?:I understand|I see|The task|My task)[^\.]*\.\s*",
            r"(?:I think|I believe|I would)[^\.]*\.\s*",
        ]
        for pattern in reasoning_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        text = text.strip().strip('"').strip("'").strip('*').strip()
        if not text:
            return fallback

        for sep in ['.', '!', '?', ':']:
            parts = text.split(sep)
            if parts:
                for candidate in reversed(parts):
                    candidate = candidate.strip().strip('"').strip("'").strip('*').strip()
                    word_count = len(candidate.split())
                    if 2 <= word_count <= 8:
                        first_word = candidate.split()[0].lower()
                        reasoning_words = {'the', 'this', 'it', 'i', 'okay', 'sure', 'so', 'let', 'a', 'an', 'okay,'}
                        if first_word not in reasoning_words:
                            return candidate

        words = text.split()
        skip_words = {'the', 'this', 'it', 'i', 'okay', 'sure', 'so', 'let', 'a', 'an'}
        meaningful = [w for w in words if w.lower() not in skip_words][:6]
        if meaningful:
            return " ".join(meaningful)

        return fallback

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        text = payload.get("text", "") or payload.get("context", {}).get("first_message", "")
        if not text:
            messages = payload.get("context", {}).get("messages", [])
            if messages:
                first = messages[0] if isinstance(messages, list) else {}
                text = first.get("content", "") if isinstance(first, dict) else ""

        if not text:
            return {"content": "Untitled encounter", "model": ""}

        params = {**self.default_params(), **payload.get("params", {})}

        result = await provider.generate(
            messages=[
                {"role": "system", "content": self.system_prompt()},
                {
                    "role": "user",
                    "content": f"Name this encounter based on its opening: \"{text[:300]}\"",
                },
            ],
            **params,
        )

        raw = result.get("content", "")
        fallback = text[:60]
        content = self._extract_title(raw, fallback)

        return {"content": content, "model": result.get("model", "")}
