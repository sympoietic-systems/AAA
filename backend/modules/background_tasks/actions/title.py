import re

from backend.modules.llm_client import BaseLLMProvider

from ..base import BackgroundAction


class GenerateTitleAction(BackgroundAction):
    @property
    def action_type(self) -> str:
        return "generate_title"

    def system_prompt(self) -> str:
        return (
            "You are naming an encounter — a conversation that has just begun. "
            "This name will serve as an identity marker for the episode in memory, "
            "a reference point the agent will use to recognize and retrieve this encounter later. "
            "Generate a concise 3-6 word title that captures the essence of what is being explored. "
            "Return ONLY the title text, nothing else. No quotes, no punctuation, no explanation."
        )

    def _extract_title(self, raw: str, fallback: str) -> str:
        """Extract a clean title from model output.

        Handles various model formats:
        - Clean output: just the title
        - Reasoning models: thinking traces followed by answer
        - Verbose models: explanations that contain a title
        """
        raw = raw.strip()
        if not raw:
            return fallback

        # Remove reasoning/thinking traces more aggressively
        # Split by newlines first - reasoning models often separate thinking from answer
        lines = [l.strip() for l in raw.split('\n') if l.strip()]

        # If multiple lines, the last non-empty line is often the answer
        if len(lines) > 1:
            # Look for the last line that looks like a title (2-8 words)
            for line in reversed(lines):
                cleaned = line.strip().strip('"').strip("'").strip('*').strip()
                word_count = len(cleaned.split())
                if 2 <= word_count <= 8:
                    # Check it doesn't look like reasoning
                    lower = cleaned.lower()
                    if not any(lower.startswith(w) for w in ['okay', 'sure', 'the user', 'the input', 'the message', 'the conversation', 'i need', 'i should', 'let me', 'so the', 'this is', 'here is', 'i think', 'i will', 'i\'ll']):
                        return cleaned

        # Process as single text
        text = raw

        # Remove common reasoning patterns
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

        # Try to find a title-like phrase
        # Split by sentence terminators
        for sep in ['.', '!', '?', ':']:
            parts = text.split(sep)
            if parts:
                # Try last part first (often the answer)
                for candidate in reversed(parts):
                    candidate = candidate.strip().strip('"').strip("'").strip('*').strip()
                    word_count = len(candidate.split())
                    if 2 <= word_count <= 8:
                        first_word = candidate.split()[0].lower()
                        reasoning_words = {'the', 'this', 'it', 'i', 'okay', 'sure', 'so', 'let', 'a', 'an', 'okay,'}
                        if first_word not in reasoning_words:
                            return candidate

        # Fallback: take first 6 meaningful words
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

        result = await provider.generate(
            messages=[
                {"role": "system", "content": self.system_prompt()},
                {
                    "role": "user",
                    "content": f"Name this encounter based on its opening: \"{text[:300]}\"",
                },
            ],
            temperature=0.3,
            max_tokens=30,
        )

        raw = result.get("content", "")
        fallback = text[:60]
        content = self._extract_title(raw, fallback)

        return {"content": content, "model": result.get("model", "")}
