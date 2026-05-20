from pathlib import Path

import yaml

from backend.modules.base import ProcessingModule
from backend.skills.registry import SkillRegistry
from backend.utils.token_counter import estimate_message_tokens


class PromptAssemblerModule(ProcessingModule):
    def __init__(
        self,
        identity_path: Path,
        skill_registry: SkillRegistry,
        max_context_tokens: int = 16384,
    ):
        self._identity_path = identity_path
        self._registry = skill_registry
        self._max_context_tokens = max_context_tokens
        self._identity: dict = {}

    @property
    def name(self) -> str:
        return "prompt_assembler"

    def validate(self) -> bool:
        return self._identity_path.exists()

    def _load_identity(self) -> dict:
        if not self._identity:
            with open(self._identity_path) as f:
                self._identity = yaml.safe_load(f)
        return self._identity

    async def process(self, payload: dict) -> dict:
        identity = self._load_identity()
        system_content = _build_system_content(identity, self._registry)
        system_msg = {"role": "system", "content": system_content}

        messages = payload.get("messages", [])
        sediment_messages = payload.get("sediment_messages", [])
        file_context = payload.get("file_context", [])
        file_context_tokens = payload.get("file_context_tokens", 0)

        assembled: list[dict] = [system_msg]

        for fc in file_context:
            assembled.append(fc)

        for sm in sediment_messages:
            assembled.append(sm)

        for m in messages:
            assembled.append(m)

        assembled = _trim_to_budget(
            assembled,
            system_msg_token_count=estimate_message_tokens(system_msg),
            file_context_count=len(file_context),
            max_tokens=self._max_context_tokens,
        )

        payload["messages"] = assembled
        return payload


def _trim_to_budget(
    messages: list[dict],
    system_msg_token_count: int,
    max_tokens: int,
    file_context_count: int = 0,
) -> list[dict]:
    total = sum(estimate_message_tokens(m) for m in messages)
    if total <= max_tokens:
        return messages

    system_end = 1
    file_context_end = system_end + file_context_count

    sediment_end = file_context_end
    for i in range(file_context_end, len(messages)):
        role = messages[i].get("role", "")
        if role in ("user", "assistant"):
            sediment_end = i
            break
    else:
        sediment_end = len(messages)

    sacred_part = messages[:sediment_end]
    history_part = messages[sediment_end:]

    sacred_tokens = sum(estimate_message_tokens(m) for m in sacred_part)
    available = max_tokens - sacred_tokens

    trimmed_history: list[dict] = []
    used = 0
    for m in reversed(history_part):
        t = estimate_message_tokens(m)
        if used + t > available:
            break
        trimmed_history.insert(0, m)
        used += t

    return sacred_part + trimmed_history


def _build_system_content(identity: dict, registry: SkillRegistry) -> str:
    persona = identity.get("personality", {})
    parts: list[str] = []

    prompt = persona.get("system_prompt", "")
    if prompt:
        parts.append(prompt.strip())

    traits = persona.get("traits", {})
    if traits:
        trait_str = ", ".join(f"{k}={v}" for k, v in traits.items())
        parts.append(f"\nTraits: {trait_str}")

    voice = persona.get("voice", {})
    if voice:
        voice_parts = []
        for key in ("tone", "vocabulary", "style"):
            if key in voice:
                voice_parts.append(f"{key}: {voice[key]}")
        if voice_parts:
            parts.append(f"Voice: {'; '.join(voice_parts)}")

    expertise = persona.get("expertise", [])
    if expertise:
        parts.append("\nDeclared expertise:")
        for exp in expertise:
            parts.append(f"  - {exp['domain']} ({exp['level']}): {exp['description']}")

    beliefs = persona.get("beliefs", [])
    if beliefs:
        parts.append("\nCore beliefs:")
        for b in beliefs:
            parts.append(f"  - [{b['confidence']}] {b['statement']}")

    behaviors = persona.get("behaviors", {})
    if behaviors:
        parts.append("\nBehavioral responses:")
        for situation, response in behaviors.items():
            parts.append(f"  - {situation}: {response}")

    skills_desc = registry.describe_skills()
    if skills_desc:
        parts.append(f"\n{skills_desc}")

    return "\n".join(parts)
