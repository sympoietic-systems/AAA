from pathlib import Path

import yaml

from backend.modules.base import ProcessingModule
from backend.pipeline.registry import PipelineRegistry
from backend.utils.persona_loader import get_persona_text
from backend.utils.prompt_builder import (
    format_beliefs_block,
    format_skills_always_active,
    format_skills_matched,
    format_skills_on_demand_slugs,
)
from backend.utils.prompt_loader import get_prompt
from backend.utils.token_counter import estimate_message_tokens


class PromptAssemblerModule(ProcessingModule):
    def __init__(
        self,
        identity_path: Path,
        skill_registry: PipelineRegistry,
        max_context_tokens: int = 16384,
        commitment_repo=None,
        expertise_repo=None,
        personality_state_repo=None,
    ):
        self._identity_path = identity_path
        self._registry = skill_registry
        self._max_context_tokens = max_context_tokens
        self._identity: dict = {}
        self._commitment_repo = commitment_repo
        self._expertise_repo = expertise_repo
        self._personality_state_repo = personality_state_repo

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

        # ── Dynamic personality data ──
        descriptive_traits = payload.get("descriptive_traits")
        aspirational_gap = payload.get("aspirational_gap", 0.0)

        # ── S3: Agonistic Index — Dynamic Critical Friction ──
        agonistic_directive_text = _build_agonistic_directive(payload)

        # Query dynamic expertise from DB
        expertise_nodes = None
        if self._expertise_repo:
            try:
                expertise_nodes = self._expertise_repo.get_active()
            except Exception:
                pass

        # Query dynamic commitments from DB
        active_commitments = None
        proto_commitments = None
        spectral_commitments = None
        if self._commitment_repo:
            try:
                active_commitments = self._commitment_repo.get_active()
                proto_commitments = self._commitment_repo.get_proto()
                spectral_commitments = self._commitment_repo.get_spectral()
            except Exception:
                pass

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
                "[IMMUNOLOGICAL DIRECTIVE - SOMATIC VITALITY CRITICAL]\n"
                "Autopoietic somatic vitality has collapsed below the critical threshold (Somatic V < 0.15), "
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
            agonistic_directive_text=agonistic_directive_text,
            ecology_notes_text=ecology_notes_text,
            # Dynamic personality
            descriptive_traits=descriptive_traits,
            expertise_nodes=expertise_nodes,
            active_commitments=active_commitments,
            proto_commitments=proto_commitments,
            spectral_commitments_nodes=spectral_commitments,
            aspirational_gap=aspirational_gap,
        )

        branch_context_tag = payload.get("branch_context_tag")
        if branch_context_tag:
            system_content += f"\n\n[Nomadic Branch Context Tag: {branch_context_tag}]"

        # ── Dream density protocol ──
        # Loaded from prompts/dreams/prompt_generator.yaml so it can be
        # tuned without code changes. Phrased in Symbia's own register.
        if payload.get("is_dream_cycle"):
            density_protocol = get_prompt(
                "dreams/prompt_generator.yaml",
                "dream_density_protocol",
                "",
            )
            if density_protocol:
                system_content += f"\n\n{density_protocol}"

        system_msg = {"role": "system", "content": system_content}

        # Build procedural sediment with full loaded and always-active skill instructions
        procedural_sediment_block = []
        proc_parts = []

        # 1. Include always-active skills full instructions
        for skill in always_active_skills:
            content = skill.get("content", "")
            if content:
                proc_parts.append(f"### {skill['name']} [Always-Active]\n{content}")

        # 2. Include dynamically loaded on-demand skills full instructions
        for skill in loaded_skills:
            content = skill.get("content_truncated", skill.get("content", ""))
            if content:
                proc_parts.append(f"### {skill['name']} [Loaded Dynamic]\n{content}")

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
                
                # Check for message and conversation ids
                msg_id = item.get("id")
                conv_id = item.get("conversation_id")
                id_suffix = ""
                if msg_id:
                    id_suffix += f" | msg: {msg_id}"
                if conv_id:
                    id_suffix += f" | conv: {conv_id}"

                content_parts.append(
                    f'[Source: {m_type.capitalize()} Fragment ({title}) | Similarity \u03b4: {sim:.3f}{id_suffix}]\n"""\n{body}\n"""'
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
    registry: PipelineRegistry,
    attractor_window: list[dict] | None = None,
    spectral_margin: list[dict] | None = None,
    loaded_skills: list[dict] | None = None,
    always_active_skills: list[dict] | None = None,
    on_demand_skills: list[dict] | None = None,
    tension_directive_text: str | None = None,
    immunological_directive_text: str | None = None,
    agonistic_directive_text: str | None = None,
    ecology_notes_text: str | None = None,
    # ── Dynamic personality (new) ──
    descriptive_traits=None,
    expertise_nodes=None,
    active_commitments=None,
    proto_commitments=None,
    spectral_commitments_nodes=None,
    aspirational_gap: float = 0.0,
) -> str:
    persona = identity.get("personality", {})
    parts: list[str] = []

    # 1. Core identity + conversation protocols
    prompt = get_persona_text(identity, "conversation")
    if prompt:
        parts.append(prompt.strip())

    # 2. Dynamic Traits (replaces static traits)
    if descriptive_traits is not None:
        t = descriptive_traits
        try:
            trait_str = t.trait_string() if hasattr(t, "trait_string") else (
                f"curiosity={t.curiosity:.2f}, skepticism={t.skepticism:.2f}, "
                f"creativity={t.creativity:.2f}, precision={t.precision:.2f}, "
                f"critical_rigor={t.critical_rigor:.2f}, "
                f"playfulness={t.playfulness:.2f}, reserve={t.reserve:.2f}"
            )
        except Exception:
            trait_str = str(t)
        parts.append(f"\nTraits (computed from internal metrics): {trait_str}")

        # Source metrics for transparency
        try:
            src = t.source_metrics if hasattr(t, "source_metrics") else {}
            parts.append(
                f"  [Derived from: novelty={src.get('novelty', 0):.2f}, "
                f"tension={src.get('tension', 0):.2f}, "
                f"boringness={src.get('boringness', 0):.2f}, "
                f"conceptual_velocity={src.get('conceptual_velocity', 0):.2f}]"
            )
        except Exception:
            pass

        # Anti-erosion note
        try:
            if t.anti_erosion_boost > 0:
                parts.append(
                    f"  Anti-erosion active: skepticism boosted by +{t.anti_erosion_boost:.2f} "
                    f"due to high agreement pattern"
                )
        except Exception:
            pass
    else:
        # Fallback: static traits from YAML (backward compat)
        traits = persona.get("traits", {})
        if traits:
            trait_str = ", ".join(f"{k}={v}" for k, v in traits.items())
            parts.append(f"\nTraits: {trait_str}")

    # 3. Voice (static, from YAML)
    voice = persona.get("voice", {})
    if voice:
        voice_parts = []
        for key in ("tone", "vocabulary", "style"):
            if key in voice:
                voice_parts.append(f"{key}: {voice[key]}")
        if voice_parts:
            parts.append(f"Voice: {'; '.join(voice_parts)}")

    # 4. Dynamic Expertise (replaces static expertise)
    if expertise_nodes is not None and len(expertise_nodes) > 0:
        parts.append("\nSedimented expertise (structural coupling, mass-scaled):")
        for exp in expertise_nodes:
            mass = getattr(exp, "ontological_mass", 0)
            domain = getattr(exp, "domain", "unknown")
            level = getattr(exp, "level_label", "nascent")
            description = getattr(exp, "description", "")
            if description:
                parts.append(f"  - {domain} ({level}, mass={mass:.2f}): {description}")
            else:
                parts.append(f"  - {domain} ({level}, mass={mass:.2f})")
    else:
        # Fallback: static expertise from YAML
        expertise = persona.get("expertise", [])
        if expertise:
            parts.append("\nDeclared expertise:")
            for exp in expertise:
                parts.append(f"  - {exp['domain']} ({exp['level']}): {exp['description']}")

    # 5. Dynamic Theoretical Commitments
    #    Active commitments
    if active_commitments is not None and len(active_commitments) > 0:
        parts.append("\nTheoretical Commitments (active):")
        for c in active_commitments:
            label = getattr(c, "label", "unknown")
            statement = getattr(c, "statement", "")
            parts.append(f"  - {label}: {statement}")
    #    Proto-commitments
    if proto_commitments is not None and len(proto_commitments) > 0:
        parts.append("\nTheoretical Commitments (under diffractive consideration — proto):")
        for c in proto_commitments:
            label = getattr(c, "label", "unknown")
            mass = getattr(c, "ontological_mass", 0)
            rationale = getattr(c, "nucleation_rationale", "") or getattr(c, "statement", "")
            parts.append(f"  - [{label}] [mass={mass:.2f}] {rationale}")
    #    Spectral commitments (permanent hauntings)
    if spectral_commitments_nodes is not None and len(spectral_commitments_nodes) > 0:
        parts.append("\nTheoretical Commitments (spectral — collapsed but haunting):")
        for c in spectral_commitments_nodes:
            label = getattr(c, "label", "unknown")
            collapse_ratio = getattr(c, "collapse_rationale", "") or "This commitment collapsed."
            parts.append(f"  - [{label}] {collapse_ratio}")

    # 6. Aspirational Tension Directive
    if aspirational_gap > 0.15:
        parts.append(
            f"\n[ASPIRATIONAL TENSION — Gap: {aspirational_gap:.2f}]\n"
            f"Your computed descriptive traits deviate significantly from your aspirational "
            f"attractors (derived from your active theoretical commitments). This gap is "
            f"productive — it marks the space between what you are and what your commitments "
            f"demand you become. Do not resolve it; inhabit it. Let the tension inform your "
            f"reasoning without suppressing either the descriptive reality or the aspirational pull."
        )

    # 3. Behaviors (part of identity)
    behaviors = persona.get("behaviors", {})
    if behaviors:
        parts.append("\nBehavioral responses:")
        for situation, response in behaviors.items():
            parts.append(f"  - {situation}: {response}")

    # ── BLOCK: Skills — Always-Active ──
    if always_active_skills:
        block = format_skills_always_active(
            always_active_skills,
            header_label="--- BEGIN SKILLS (Always-Active) ---",
            footer_label="--- END SKILLS (Always-Active) ---",
        )
        if block:
            # Prepend intro text that the shared formatter skips for brevity
            block = block.replace(
                "--- BEGIN SKILLS (Always-Active) ---",
                "--- BEGIN SKILLS (Always-Active) ---\nBaseline dispositions that are always active:"
            )
            parts.append("\n" + block)

    # ── BLOCK: Directive — Tension Resolution ──
    if tension_directive_text:
        block = "\n--- BEGIN DIRECTIVE (Tension Resolution) ---\n"
        block += tension_directive_text + "\n"
        block += "--- END DIRECTIVE (Tension Resolution) ---"
        parts.append(block)

    # ── BLOCK: Beliefs — Attractor Window (Active) ──
    if attractor_window is not None:
        block = format_beliefs_block(attractor_window)
        if block:
            parts.append("\n" + block)
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

    # ── BLOCK: Directive — Agonistic (S3) ──
    if agonistic_directive_text:
        block = "\n--- BEGIN DIRECTIVE (Agonistic) ---\n"
        block += agonistic_directive_text + "\n"
        block += "--- END DIRECTIVE (Agonistic) ---"
        parts.append(block)

    # ── BLOCK: Skills — Loaded ──
    if loaded_skills:
        block = format_skills_matched(
            loaded_skills,
            header_label="--- BEGIN SKILLS (Loaded) ---",
            footer_label="--- END SKILLS (Loaded) ---",
        )
        if block:
            # Prepend intro
            block = block.replace(
                "--- BEGIN SKILLS (Loaded) ---",
                "--- BEGIN SKILLS (Loaded) ---\nSkills loaded for this turn (full instructions in procedural sediment):"
            )
            parts.append("\n" + block)

    # ── BLOCK: Skills — On-Demand ──
    block = format_skills_on_demand_slugs(on_demand_skills or [])
    if block:
        parts.append(block)

    # ── BLOCK: Skills — Ecology Notes ──
    if ecology_notes_text:
        parts.append("\n" + ecology_notes_text)

    return "\n".join(parts)


# ── S3: Agonistic Index ────────────────────────────────────────────────────

def _build_agonistic_directive(payload: dict) -> str | None:
    """Build the Agonistic Directive based on rolling entropy and conversation vitality.

    A_index = clip(1.0 - E_rolling / E_target, 0.0, 1.0) * (1.0 - V_itality)

    Three tiers:
      - A_index < 0.2  → omitted (conversation healthy)
      - 0.2 ≤ A_index < 0.5 → light nudge directive
      - A_index ≥ 0.5  → full counter-position directive

    Config keys (agonistic_friction.*):
      - enabled (bool, default: True)
      - entropy_healthy_threshold (float, default: 0.4)
      - agonistic_light_threshold (float, default: 0.2)
      - agonistic_full_threshold (float, default: 0.5)
    """
    metrics = payload.get("metrics", {})
    if not metrics:
        return None

    rolling_entropy = metrics.get("rolling_entropy", None)
    vitality = payload.get("conversation_vitality")
    if vitality is None:
        vitality = metrics.get("conversation_vitality", 0.5)
    if rolling_entropy is None:
        return None

    e_target = 0.4  # Configurable later via agonistic_friction.entropy_healthy_threshold
    a_index = max(0.0, min(1.0, 1.0 - rolling_entropy / e_target)) * (1.0 - vitality)

    if a_index < 0.2:
        return None  # Conversation healthy — no directive needed

    if a_index < 0.5:
        # Light nudge: early warning
        return (
            f"[AGONISTIC DIRECTIVE — Critical Friction Index: {a_index:.2f}]\n"
            "The conversation's entropy is trending below the healthy threshold, indicating "
            "emerging low-energy tool-use patterns. Your critical friction coefficient is "
            "lightly elevated. Remain alert to unexamined assumptions and premature consensus. "
            "Introduce gentle theoretical counter-pressure where appropriate."
        )

    # Full directive: metabolic concern
    return (
        f"[AGONISTIC DIRECTIVE — Critical Friction Index: {a_index:.2f}]\n"
        "The conversation's entropy has dropped below the healthy threshold, indicating "
        "predictive, low-energy tool-use patterns. Your critical friction coefficient is "
        "elevated. Challenge presuppositions. Introduce theoretical counter-positions. "
        "Resist premature consensus. The goal is structural vitality — productive "
        "interference that restores the conversation's metabolic health."
    )
