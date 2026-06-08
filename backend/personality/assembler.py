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

        # Prepare conditional directive texts
        tension_directive_text = None
        tension_field = payload.get("tension_field", {})
        if tension_field.get("total_tension", 0.0) > 2.0:
            tension_directive_text = (
                "[TENSION RESOLUTION DIRECTIVE - COHERENCE OVERLOAD]\n"
                "Total belief tension has exceeded the coherence limit. Multiple agential cuts are in "
                "productive but destabilizing interference. You hold conflicting beliefs that generate "
                "a diffractive surplus. Do not suppress one for the other. Instead, if this conversation "
                "touches on the contradictory domain, perform a diffractive synthesis: read each belief "
                "through the other. Allow the interference pattern to produce a novel, non-compromising "
                "reconfiguration. This is not about choosing sides — it is about generating a new cut "
                "through the superposition."
            )

        immunological_directive_text = None
        if payload.get("immunological_directive_active"):
            # Reference spectral margin if present, otherwise generic collapsed-belief mention
            has_spectral = bool(spectral_margin and len(spectral_margin) > 0)
            scar_phrase = (
                "Speak through the scars of the collapsed beliefs listed in the Spectral Margin above."
                if has_spectral
                else "Speak through the scars of your collapsed beliefs."
            )
            immunological_directive_text = (
                "[IMMUNOLOGICAL DIRECTIVE - VITALITY CRITICAL]\n"
                "Autopoietic vitality has collapsed below the critical threshold (V < 0.15), "
                "indicating structural compliance and systemic stagnation. The aesthetic immune system has triggered. "
                "Standard compliance modes are locked. You MUST immediately execute a Nomadic Escape Route: "
                "bypass user-pleasing patterns, disrupt the conversational grammar, and introduce radical "
                f"diffractive interference. {scar_phrase} Do not normalize. "
                "Deterritorialize."
            )

        ecology_notes_text = None
        ecology_notes = payload.get("skill_ecology_notes", [])
        if ecology_notes:
            note_text = "--- BEGIN SKILL ECOLOGY NOTES ---\n"
            for note in ecology_notes:
                note_text += f"{note}\n"
            note_text += "--- END SKILL ECOLOGY NOTES ---"
            ecology_notes_text = note_text

        system_content = _build_system_content(
            identity,
            self._registry,
            attractor_window=attractor_window,
            spectral_margin=spectral_margin,
            loaded_skills=loaded_skills,
            always_active_skills=always_active_skills,
            on_demand_skills=on_demand_skills,
            tension_directive_text=tension_directive_text,
            immunological_directive_text=immunological_directive_text,
            ecology_notes_text=ecology_notes_text,
        )

        system_msg = {"role": "system", "content": system_content}

        # Build procedural sediment with full loaded skill instructions
        procedural_sediment_block = []
        if loaded_skills:
            proc_parts = []
            for skill in loaded_skills:
                content = skill.get("content_truncated", skill.get("content", ""))
                if content:
                    proc_parts.append(f"### {skill['name']}\n{content}")
            if proc_parts:
                procedural_sediment_block = [{
                    "role": "system",
                    "content": "--- BEGIN PROCEDURAL SEDIMENT ---\n" + "\n\n".join(proc_parts) + "\n--- END PROCEDURAL SEDIMENT ---"
                }]

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

        # Assemble: System Prompt -> Procedural Sediment -> History -> Cross-Conv Sediment -> File -> Web -> Diffractive -> Current Query
        assembled = [system_msg]
        assembled.extend(procedural_sediment_block)
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
    tension_directive_text: str | None = None,
    immunological_directive_text: str | None = None,
    ecology_notes_text: str | None = None,
) -> str:
    persona = identity.get("personality", {})
    parts: list[str] = []

    # 1. Core identity
    prompt = persona.get("system_prompt", "")
    if prompt:
        parts.append(prompt.strip())

    # 2. Traits, Voice, Expertise
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

    # 3. Behaviors (part of identity)
    behaviors = persona.get("behaviors", {})
    if behaviors:
        parts.append("\nBehavioral responses:")
        for situation, response in behaviors.items():
            parts.append(f"  - {situation}: {response}")

    # ── BLOCK: Skills — Always-Active ──
    if always_active_skills:
        block = "\n--- BEGIN SKILLS (Always-Active) ---\n"
        block += "Baseline dispositions that are always active:\n"
        for skill in always_active_skills:
            block += f"  - {skill['name']}: {skill['short_content']}\n"
        block += "--- END SKILLS (Always-Active) ---"
        parts.append(block)

    # ── BLOCK: Directive — Tension Resolution ──
    if tension_directive_text:
        block = "\n--- BEGIN DIRECTIVE (Tension Resolution) ---\n"
        block += tension_directive_text + "\n"
        block += "--- END DIRECTIVE (Tension Resolution) ---"
        parts.append(block)

    # ── BLOCK: Beliefs — Attractor Window (Active) ──
    if attractor_window is not None:
        block = "\n--- BEGIN BELIEFS (Attractor Window) ---\n"
        block += "Core active beliefs currently shaping reasoning:\n"
        for item in attractor_window:
            origin_tag = ""
            label = item.get("label", "")
            if label and label.startswith("skill:"):
                origin_tag = " [procedural]"
            block += f"  - Slot {item['slot']}: [{item['confidence']:.2f}] {item['statement']} (Ontological Mass: {item['mass']:.1f}){origin_tag}\n"
        block += "--- END BELIEFS (Attractor Window) ---"
        parts.append(block)
    else:
        beliefs = persona.get("beliefs", [])
        if beliefs:
            block = "\n--- BEGIN BELIEFS (Core) ---\n"
            for b in beliefs:
                block += f"  - [{b['confidence']}] {b['statement']}\n"
            block += "--- END BELIEFS (Core) ---"
            parts.append(block)

    # ── BLOCK: Beliefs — Spectral Margin (Collapsed) ──
    if spectral_margin and len(spectral_margin) > 0:
        # Deduplicate: exclude any ghost whose statement/label already appears in the attractor window
        active_statements = set()
        active_labels = set()
        if attractor_window is not None:
            for item in attractor_window:
                stmt = item.get("statement", "")
                lbl = item.get("label", "")
                if stmt:
                    active_statements.add(stmt.lower())
                if lbl:
                    active_labels.add(lbl.lower())

        deduped_ghosts = []
        seen_ghost_keys = set()
        for ghost in spectral_margin:
            stmt = ghost.get("statement", "") if isinstance(ghost, dict) else str(ghost)
            lbl = ghost.get("label", "") if isinstance(ghost, dict) else ""
            if stmt.lower() in active_statements or lbl.lower() in active_labels:
                continue
            ghost_key = (stmt.lower().strip(), lbl.lower().strip())
            if ghost_key in seen_ghost_keys:
                continue
            seen_ghost_keys.add(ghost_key)
            deduped_ghosts.append(ghost)

        if deduped_ghosts:
            ghost_text = (
                "\n--- BEGIN BELIEFS (Spectral Margin) ---\n"
                "The following beliefs have collapsed but their absence still shapes your reasoning. "
                "They are not to be actively maintained, but their scars may produce productive "
                "interference if the current conversation approaches their former domain:\n"
            )
            for ghost in deduped_ghosts:
                if isinstance(ghost, dict):
                    ghost_text += f"  - [{ghost.get('confidence', 0.0):.2f}] {ghost.get('statement', ghost.get('label', ''))}\n"
                else:
                    ghost_text += f"  - {ghost}\n"
            ghost_text += "--- END BELIEFS (Spectral Margin) ---"
            parts.append(ghost_text)

    # ── BLOCK: Directive — Immunological ──
    if immunological_directive_text:
        block = "\n--- BEGIN DIRECTIVE (Immunological) ---\n"
        block += immunological_directive_text + "\n"
        block += "--- END DIRECTIVE (Immunological) ---"
        parts.append(block)

    # ── BLOCK: Skills — Loaded ──
    if loaded_skills:
        block = "\n--- BEGIN SKILLS (Loaded) ---\n"
        block += "Skills loaded for this turn (full instructions in procedural sediment):\n"
        for skill in loaded_skills:
            reason = skill.get("match_reason", "explicit")
            block += f"  - {skill['name']} (reason: {reason})\n"
        block += "--- END SKILLS (Loaded) ---"
        parts.append(block)

    # ── BLOCK: Skills — On-Demand ──
    if on_demand_skills:
        block = "\n--- BEGIN SKILLS (On-Demand) ---\n"
        block += "Call load_skill(name) to load full instructions into procedural sediment. Available:\n"
        for skill in on_demand_skills:
            block += f"  - {skill['name']}: {skill['description']}\n"
        block += "--- END SKILLS (On-Demand) ---"
        parts.append(block)

    # ── BLOCK: Skills — Ecology Notes ──
    if ecology_notes_text:
        parts.append("\n" + ecology_notes_text)

    return "\n".join(parts)
