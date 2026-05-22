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

        # Split history into prior turns and current query
        history_prior = []
        current_query = []
        if messages:
            history_prior = messages[:-1]
            current_query = [messages[-1]]

        # Wrap history with boundary blocks if present
        if history_prior:
            history_block = [{"role": "system", "content": "--- BEGIN CONVERSATION HISTORY ---"}]
            history_block.extend(history_prior)
            history_block.append({"role": "system", "content": "--- END CONVERSATION HISTORY ---"})
        else:
            history_block = []

        # Wrap cross-conversation sediment with boundary blocks if present
        if sediment_messages:
            sediment_block = [{"role": "system", "content": "--- BEGIN CROSS-CONVERSATION RESONANCE ---"}]
            sediment_block.extend(sediment_messages)
            sediment_block.append({"role": "system", "content": "--- END CROSS-CONVERSATION RESONANCE ---"})
        else:
            sediment_block = []

        # Wrap file context with boundary blocks if present
        if file_context:
            file_block = [{"role": "system", "content": "--- BEGIN FILE SEDIMENT ---"}]
            file_block.extend(file_context)
            file_block.append({"role": "system", "content": "--- END FILE SEDIMENT ---"})
        else:
            file_block = []

        # Re-assemble the context in the topologically coherent order:
        # System Prompt -> History Prior -> Sediment (Cross-Conv Memory) -> File Context -> Current Query
        assembled = [system_msg]
        assembled.extend(history_block)
        assembled.extend(sediment_block)
        assembled.extend(file_block)
        assembled.extend(current_query)

        payload["messages"] = assembled
        return payload



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
