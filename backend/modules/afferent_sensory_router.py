"""Afferent Sensory Router — Pre-reflective Somatic Filtration via Jev (System One).

Implements the Afferent Sensory Membrane for skill routing and context reduction:
1. Somatic Gating: Evaluates gate_apparatus vs gate_contemplation.
2. Organ Resonance: Evaluates Choice across crystallized on-demand skills.
3. Multi-Skill Injection with Complementary Coupling: Injects up to max_injected_skills.
4. Directional Coordinate Inscription: Emits <skill_relevance> tags for moderate candidates.
5. Boredom Inversion Gate: Overrides conservative gating when collapse_pressure > 0.70.
"""

import logging
from typing import Any

from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient

logger = logging.getLogger(__name__)

# Anti-mastery inscriptional phrasing for sensory gates
GATE_APPARATUS_INSTRUCTION = (
    "Does the current material-discursive entanglement require an instrumental agential cut "
    "(such as code diagnosis, architectural refactoring, database design, curatorial staging, "
    "or formal technical execution)?"
)

GATE_CONTEMPLATION_INSTRUCTION = (
    "Is the exchange an ongoing self-organizing conceptual, philosophical, or "
    "reflective entanglement where procedural scaffolding would introduce epistemic noise?"
)

CHOICE_ORGAN_INSTRUCTION = (
    "Which of these procedural organs exhibits highest structural resonance with the "
    "operational tension in the participant's turn?"
)


class AfferentSensoryRouter:
    """Evaluates conversation turns through Jev to determine skill resonance and gating."""

    def __init__(
        self,
        client: TypeSafeDecisionClient | None = None,
        max_injected_skills: int = 2,
        hard_max_injected_skills: int = 4,
        high_relevance_threshold: float = 0.25,
        inject_threshold: float = 0.80,
        coordinate_threshold: float = 0.50,
        gate_action_threshold: float = 0.35,
        gate_reflection_threshold: float = 0.65,
    ):
        self.client = client
        self.max_injected_skills = max_injected_skills
        self.hard_max_injected_skills = hard_max_injected_skills
        self.high_relevance_threshold = high_relevance_threshold
        self.inject_threshold = inject_threshold
        self.coordinate_threshold = coordinate_threshold
        self.gate_action_threshold = gate_action_threshold
        self.gate_reflection_threshold = gate_reflection_threshold

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "AfferentSensoryRouter":
        """Factory method to construct router from AAA configuration."""
        ts_cfg = config.get("typesafe", {})
        enabled = ts_cfg.get("enabled", True)
        api_key = ts_cfg.get("api_key")

        client = None
        if enabled and api_key:
            client = TypeSafeDecisionClient(
                api_key=api_key,
                api_base=ts_cfg.get("api_base"),
                model=ts_cfg.get("model"),
                timeout=ts_cfg.get("timeout", 3.0),
            )

        return cls(
            client=client,
            max_injected_skills=ts_cfg.get("soft_max_injected_skills", ts_cfg.get("max_injected_skills", 2)),
            hard_max_injected_skills=ts_cfg.get("hard_max_injected_skills", 4),
            high_relevance_threshold=ts_cfg.get("high_relevance_threshold", 0.25),
            inject_threshold=ts_cfg.get("inject_confidence_threshold", 0.80),
            coordinate_threshold=ts_cfg.get("coordinate_confidence_threshold", 0.50),
            gate_action_threshold=ts_cfg.get("gate_action_threshold", 0.35),
            gate_reflection_threshold=ts_cfg.get("gate_reflection_threshold", 0.65),
        )

    @property
    def is_available(self) -> bool:
        """Return True if decision client is configured and available."""
        return bool(self.client and self.client.is_configured)

    def _build_sensory_state(
        self,
        user_message: str,
        messages: list[dict[str, Any]],
        file_context: list[dict[str, Any]],
        collapse_pressure: float,
    ) -> dict[str, Any]:
        """Construct lean afferent state snapshot for Jev (sub-200ms latency discipline)."""
        prior_context = []
        if len(messages) >= 2:
            for msg in messages[-3:-1]:
                if isinstance(msg, dict):
                    role = msg.get("role", "unknown")
                    content = str(msg.get("content", ""))[:200]
                    prior_context.append(f"{role}: {content}")

        attached_files = []
        for fc in file_context:
            if isinstance(fc, dict) and fc.get("filename"):
                attached_files.append(fc["filename"])

        return {
            "current_turn": user_message[:1000],
            "prior_context": prior_context,
            "attached_files": attached_files[:5],
            "collapse_pressure": round(collapse_pressure, 3),
        }

    async def route(
        self,
        user_message: str,
        on_demand_skills: list[Any],
        messages: list[dict[str, Any]] | None = None,
        file_context: list[dict[str, Any]] | None = None,
        attractor_window: list[dict[str, Any]] | None = None,
        collapse_pressure: float = 0.0,
    ) -> dict[str, Any]:
        """Evaluate turn through Jev Afferent Sensory Membrane.

        Returns:
            dict containing:
              - decision: "none" | "coordinate" | "inject"
              - injected_skills: list of SkillNode objects to inject in full
              - coordinates: list of string tags (<skill_relevance .../>)
              - raw_evaluation: dict | None
        """
        if not self.is_available or not on_demand_skills or not user_message:
            return {
                "decision": "none",
                "injected_skills": [],
                "coordinates": [],
                "raw_evaluation": None,
            }

        state = self._build_sensory_state(
            user_message, messages or [], file_context or [], collapse_pressure
        )

        # Build Choice criteria using concise descriptions
        skill_by_name = {s.name: s for s in on_demand_skills}
        criteria = {
            s.name: (s.short_content or s.description or s.name)[:150]
            for s in on_demand_skills
        }

        questions = {
            "gate_apparatus": {
                "type": "noul",
                "instructions": GATE_APPARATUS_INSTRUCTION,
            },
            "gate_contemplation": {
                "type": "noul",
                "instructions": GATE_CONTEMPLATION_INSTRUCTION,
            },
            "organ_resonance": {
                "type": "choice",
                "instructions": CHOICE_ORGAN_INSTRUCTION,
                "criteria": criteria,
            },
        }

        eval_res = await self.client.evaluate(state=state, questions=questions)
        if not eval_res.get("success"):
            logger.debug("Afferent sensory evaluation was unsuccessful; falling back.")
            return {
                "decision": "none",
                "injected_skills": [],
                "coordinates": [],
                "raw_evaluation": eval_res,
            }

        answers = eval_res.get("answers") or eval_res.get("results") or {}
        gate_app = answers.get("gate_apparatus", {})
        p_apparatus = gate_app.get("noul") if "noul" in gate_app else gate_app.get("probability", 0.5)

        gate_cont = answers.get("gate_contemplation", {})
        p_contemplation = gate_cont.get("noul") if "noul" in gate_cont else gate_cont.get("probability", 0.5)

        choice_ans = answers.get("organ_resonance", {})
        top_choice = choice_ans.get("choice") or choice_ans.get("decision")
        probs = choice_ans.get("probabilities", {})
        confidence = choice_ans.get("confidence", 0.5)

        # ── Boredom Inversion Gate ─────────────────────────────────────────
        # When Collapse Pressure > 0.70, bypass conservative contemplation gate
        is_boredom_inversion = collapse_pressure >= 0.70

        # ── Gating Check: Pure Contemplative Filter ────────────────────────
        if not is_boredom_inversion:
            if (
                p_contemplation >= self.gate_reflection_threshold
                and p_apparatus < self.gate_action_threshold
            ):
                # Pristine membrane: zero on-demand skills injected
                return {
                    "decision": "none",
                    "injected_skills": [],
                    "coordinates": [],
                    "raw_evaluation": eval_res,
                }

        # ── Attractor Window Prior Modulation ──────────────────────────────
        # Modulate probabilities with active belief mass
        mass_priors = {}
        if attractor_window:
            for item in attractor_window:
                lbl = item.get("label", "")
                if lbl.startswith("skill:"):
                    name = lbl.removeprefix("skill:")
                    mass_priors[name] = item.get("mass", 0.5)

        scored_candidates = []
        for name, prob in probs.items():
            if name in skill_by_name:
                prior = mass_priors.get(name, 0.0)
                # Scale probability by prior mass
                eff_prob = prob * (1.0 + prior)
                scored_candidates.append((name, eff_prob, prob))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        injected_skills = []
        coordinates = []

        # ── Confidence-Tiered Partitioning with Elastic High-Relevance Pass-Through ────
        for rank, (name, eff_prob, raw_prob) in enumerate(scored_candidates):
            skill = skill_by_name[name]

            # High confidence threshold for injection
            if confidence >= self.inject_threshold and raw_prob >= 0.20:
                if len(injected_skills) < self.max_injected_skills:
                    # Guaranteed standard slots (Rank 1 & 2)
                    injected_skills.append(skill)
                elif (
                    len(injected_skills) < self.hard_max_injected_skills
                    and raw_prob >= self.high_relevance_threshold
                ):
                    # Rank 3+: Elastic Pass-Through for exceptionally relevant skills
                    injected_skills.append(skill)
                else:
                    # Excess high candidates become coordinates
                    if len(coordinates) < 2:
                        coordinates.append(
                            f'<skill_relevance organ="{name}" confidence="{confidence:.2f}" resonance="secondary-attractor"/>'
                        )
            elif confidence >= self.coordinate_threshold and (name == top_choice or eff_prob >= 0.35):
                # Moderate threshold: directional coordinate tag for primary resonating organ
                if len(coordinates) < 2:
                    coordinates.append(
                        f'<skill_relevance organ="{name}" confidence="{confidence:.2f}" resonance="peripheral-sensation"/>'
                    )

        if injected_skills:
            decision = "inject"
        elif coordinates:
            decision = "coordinate"
        else:
            decision = "none"

        return {
            "decision": decision,
            "injected_skills": injected_skills,
            "coordinates": coordinates,
            "raw_evaluation": eval_res,
        }
