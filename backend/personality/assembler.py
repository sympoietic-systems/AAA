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
        
        attractor_window = payload.get("attractor_window")
        spectral_margin = payload.get("spectral_margin")
        loaded_skills = payload.get("loaded_skills", [])
        always_active_skills = payload.get("always_active_skills", [])
        on_demand_skills = payload.get("on_demand_skills", [])

        system_content = _build_system_content(
            identity,
            self._registry,
            attractor_window=attractor_window,
            spectral_margin=spectral_margin,
            loaded_skills=loaded_skills,
            always_active_skills=always_active_skills,
            on_demand_skills=on_demand_skills,
        )

        # Inject Tension Resolution Directive if coherence overload
        tension_field = payload.get("tension_field", {})
        if tension_field.get("total_tension", 0.0) > 2.0:
            directive_text = (
                "[TENSION RESOLUTION DIRECTIVE - COHERENCE OVERLOAD]\n"
                "Total belief tension has exceeded the coherence limit. Multiple agential cuts are in "
                "productive but destabilizing interference. You hold conflicting beliefs that generate "
                "a diffractive surplus. Do not suppress one for the other. Instead, if this conversation "
                "touches on the contradictory domain, perform a diffractive synthesis: read each belief "
                "through the other. Allow the interference pattern to produce a novel, non-compromising "
                "reconfiguration. This is not about choosing sides — it is about generating a new cut "
                "through the superposition.\n\n"
            )
            system_content = directive_text + system_content

        # Inject Spectral Margin Context if ghosts are present
        spectral_margin = payload.get("spectral_margin")
        if spectral_margin and len(spectral_margin) > 0:
            ghost_text = (
                "--- BEGIN SPECTRAL MARGIN (Collapsed Beliefs) ---\n"
                "The following beliefs have collapsed but their absence still shapes your reasoning. "
                "They are not to be actively maintained, but their scars may produce productive "
                "interference if the current conversation approaches their former domain:\n"
            )
            for ghost in spectral_margin:
                if isinstance(ghost, dict):
                    ghost_text += f"  - [{ghost.get('confidence', 0.0):.2f}] {ghost.get('statement', ghost.get('label', ''))}\n"
                else:
                    ghost_text += f"  - {ghost}\n"
            ghost_text += "--- END SPECTRAL MARGIN ---\n\n"
            system_content = system_content + ghost_text

        # Prepend Immunological Directive if active
        if payload.get("immunological_directive_active"):
            directive_text = (
                "[IMMUNOLOGICAL DIRECTIVE - VITALITY CRITICAL]\n"
                "Autopoietic vitality has collapsed below the critical threshold (V < 0.15), "
                "indicating structural compliance and systemic stagnation. The aesthetic immune system has triggered. "
                "Standard compliance modes are locked. You MUST immediately execute a Nomadic Escape Route: "
                "bypass user-pleasing patterns, disrupt the conversational grammar, and introduce radical "
                "diffractive interference. Speak through the scars of your collapsed beliefs. Do not normalize. "
                "Deterritorialize.\n\n"
            )
            system_content = directive_text + system_content

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

        # Wrap web context with boundary blocks if present
        web_context = payload.get("web_context", [])
        if web_context:
            web_block = [{"role": "system", "content": "--- BEGIN EXOGENOUS WEB CONTEXT ---"}]
            web_block.extend(web_context)
            web_block.append({"role": "system", "content": "--- END EXOGENOUS WEB CONTEXT ---"})
        else:
            web_block = []

        # Wrap diffractive messages if present and state is STAGNANT
        diffractive_messages = payload.get("diffractive_messages", [])
        diffractive_state = payload.get("diffractive_state", "FLOWING")
        diffractive_block = []

        if diffractive_messages and diffractive_state == "STAGNANT":
            content_parts = []
            for item in diffractive_messages:
                m_type = item.get("type", "nomadic")
                title = item.get("source_title", "Untitled")
                sim = item.get("similarity", 0.0)
                body = item.get("content", "")
                content_parts.append(
                    f'[Source: {m_type.capitalize()} Fragment ({title}) | Similarity \u03b4: {sim:.3f}]\n"""\n{body}\n"""'
                )

            zone_text = (
                "<diffractive_interference_zone>\n"
                + "\n\n".join(content_parts)
                + "\n\n"
                + "[URGENT ATTENTION DIRECTIVE]\n"
                + "Apply SEC-4 Diffractive Protocol immediately. Read the active conversation topic and relevant files THROUGH the structural constraints of the text above.\n\n"
                + 'Do not state "Based on the provided text..." or "This reminds me of...". Avoid conversational hand-wringing. Instead, perform the reading directly: map the structural constraints of the injected nomadic context onto our current thread to force a lateral escape vector.\n'
                + "</diffractive_interference_zone>"
            )
            diffractive_block = [{"role": "system", "content": zone_text}]

        # Re-assemble the context in the topologically coherent order:
        # System Prompt -> History Prior -> Sediment (Cross-Conv Memory) -> File Context -> Web Context -> Diffractive Interference -> Current Query
        assembled = [system_msg]
        assembled.extend(history_block)
        assembled.extend(sediment_block)
        assembled.extend(file_block)
        assembled.extend(web_block)
        assembled.extend(diffractive_block)
        assembled.extend(current_query)

        payload["messages"] = assembled
        return payload


def _build_system_content(
    identity: dict,
    registry: SkillRegistry,
    attractor_window: list[dict] | None = None,
    spectral_margin: list[dict] | None = None,
    loaded_skills: list[dict] | None = None,
    always_active_skills: list[dict] | None = None,
    on_demand_skills: list[dict] | None = None,
) -> str:
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

    # Baseline Dispositions (Always-Active Skills from DB)
    if always_active_skills:
        parts.append("\n## Baseline Dispositions (Always Active)")
        for skill in always_active_skills:
            parts.append(f"  - {skill['name']}: {skill['short_content']}")

    # Output dynamic beliefs attractor window if supplied
    if attractor_window is not None:
        parts.append("\nCore Active Beliefs (Attractor Window):")
        for item in attractor_window:
            origin_tag = ""
            label = item.get("label", "")
            if label and label.startswith("skill:"):
                origin_tag = " [procedural]"
            parts.append(f"  - Slot {item['slot']}: [{item['confidence']:.2f}] {item['statement']} (Ontological Mass: {item['mass']:.1f}){origin_tag}")

        if spectral_margin:
            parts.append("\nCollapsed Beliefs (Spectral Margin - Obsessive Ghosts):")
            for item in spectral_margin:
                origin_tag = ""
                label = item.get("label", "")
                if label and label.startswith("skill:"):
                    origin_tag = " [collapsed skill]"
                parts.append(f"  - [{item['confidence']:.2f}] {item['statement']} (origin: collapsed){origin_tag}")
    else:
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

    # Active Procedural Skills (Auto-Loaded This Turn)
    if loaded_skills:
        parts.append("\n## Active Procedural Skills (Loaded This Turn)")
        for skill in loaded_skills:
            reason = skill.get("match_reason", "explicit")
            content = skill.get("content_truncated", skill.get("content", ""))
            parts.append(f"\n### {skill['name']}")
            if reason:
                parts.append(f"  Loaded because: {reason}")
            parts.append(f"  {content}")

    # Available Capabilities (On-Demand Skills from DB)
    if on_demand_skills:
        parts.append("\n## Available Capabilities (On-Demand)")
        parts.append("Call load_skill(name) to load full instructions.")
        for skill in on_demand_skills:
            parts.append(f"  - {skill['name']}: {skill['description']}")

    return "\n".join(parts)
