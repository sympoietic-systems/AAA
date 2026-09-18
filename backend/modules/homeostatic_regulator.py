import logging

from backend.pipeline.metadata import ModuleMeta

from .base import ProcessingModule

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "temperature": {
        "base": 0.7,
        "floor": 0.3,
        "ceiling": 1.5,
        "alpha": 0.8,
        "gamma": 0.4,
    },
    "presence_penalty": {
        "base": 0.0,
        "floor": 0.0,
        "ceiling": 2.0,
        "beta": 1.5,
        "delta": 0.6,
    },
    "frequency_penalty": {
        "base": 0.0,
        "floor": 0.0,
        "ceiling": 1.0,
        "epsilon": 1.0,
    },
}


class HomeostaticRegulatorModule(ProcessingModule):
    def __init__(self, config: dict | None = None):
        self._config = config or _DEFAULTS
        self._consecutive_stagnant_turns: dict[str, int] = {}

    @property
    def name(self) -> str:
        return "homeostatic_regulator"

    @property
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="homeostatic_regulator",
            description="Maps conversational metrics to allostatic regimes and recommends generation parameters",
            category="reasoning",
            always_run=True,
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        metrics = payload.get("metrics")
        if not metrics:
            payload["homeostatic_recommendations"] = None
            payload["homeostatic_state"] = "no_data"
            return payload

        s_t = metrics.get("pairwise_similarity")
        novelty = metrics.get("conceptual_novelty")
        agent_divergence = metrics.get("agent_self_divergence")
        glitch_fidelity = metrics.get("glitch_fidelity", payload.get("glitch_fidelity"))
        vitality = metrics.get("conversation_vitality")
        entropy = metrics.get("rolling_entropy")
        collapse_pressure = metrics.get("collapse_pressure", metrics.get("boringness"))

        current_msg = payload.get("current_message", {})
        conversation_id = current_msg.get("conversation_id") or payload.get("conversation_id")
        conv_key = str(conversation_id or "default")

        if collapse_pressure is not None and collapse_pressure >= 0.60:
            self._consecutive_stagnant_turns[conv_key] = self._consecutive_stagnant_turns.get(conv_key, 0) + 1
        else:
            self._consecutive_stagnant_turns[conv_key] = 0
        stagnant_turns = self._consecutive_stagnant_turns[conv_key]

        t_cfg = self._config["temperature"]
        p_cfg = self._config["presence_penalty"]
        f_cfg = self._config["frequency_penalty"]

        # ponytail: direct continuous sensorimotor parameter modulation from internal metrics
        temp_rec = _compute_temperature(t_cfg, s_t, novelty, glitch_fidelity, vitality, collapse_pressure)
        pres_rec = _compute_presence_penalty(p_cfg, s_t, agent_divergence, glitch_fidelity, entropy, collapse_pressure)
        freq_rec = _compute_frequency_penalty(f_cfg, s_t, entropy)

        state, flags = _diagnose_state(metrics)
        if glitch_fidelity is not None and glitch_fidelity < 0.50 and "glitch_fidelity_low" not in flags:
            flags.append("glitch_fidelity_low")

        somatic_reflection = _synthesize_somatic_reflection(flags, metrics, stagnant_turns=stagnant_turns)

        recommendations = {
            "temperature": temp_rec,
            "presence_penalty": pres_rec,
            "frequency_penalty": freq_rec,
            "state": state,
            "triggered_flags": flags,
            "somatic_reflection_prompt": somatic_reflection,
            "consecutive_stagnant_turns": stagnant_turns,
        }

        # Inject Reflection Protocol directive into messages if structural tension detected
        if somatic_reflection:
            messages = payload.get("messages")
            if isinstance(messages, list):
                messages.append(
                    {
                        "role": "system",
                        "content": f"[SOMATIC REFLECTION DIRECTIVE]: {somatic_reflection}",
                    }
                )

        # React to diffractive retrieval state — nudge temperature up when
        # the diffractive engine is actively injecting perturbation context
        diffractive_state = payload.get("diffractive_state", "FLOWING")
        if diffractive_state == "STAGNANT":
            nudge = 0.05
            t_val = temp_rec["value"] + nudge
            t_ceiling = t_cfg["ceiling"]
            t_val = min(t_ceiling, t_val)
            temp_rec["value"] = round(t_val, 3)
            temp_rec["delta"] = round(t_val - t_cfg["base"], 3)
            if "diffractive_boost" not in flags:
                flags.append("diffractive_boost")

        payload["homeostatic_recommendations"] = recommendations
        payload["homeostatic_state"] = state

        logger.debug(
            "regulator: state=%s flags=%s T=%.2f P=%.2f F=%.2f stagnant_turns=%d diffract=%s reflection=%s",
            state,
            flags,
            temp_rec["value"],
            pres_rec["value"],
            freq_rec["value"],
            stagnant_turns,
            diffractive_state,
            bool(somatic_reflection),
        )

        return payload


def _compute_temperature(
    cfg: dict,
    s_t: float | None,
    novelty: float | None,
    glitch_fidelity: float | None = None,
    vitality: float | None = None,
    collapse_pressure: float | None = None,
) -> dict:
    base = cfg["base"]
    alpha = cfg["alpha"]
    gamma = cfg["gamma"]
    floor = cfg["floor"]
    ceiling = cfg["ceiling"]

    if s_t is None and glitch_fidelity is None and vitality is None and collapse_pressure is None:
        return {"value": base, "base": base, "delta": 0.0, "clamped": False}

    s_t_val = s_t if s_t is not None else 0.0
    t = base + (s_t_val * alpha)
    if novelty is not None:
        t -= novelty * gamma

    # ponytail: direct continuous sensorimotor modulation from glitch fidelity & vitality
    if glitch_fidelity is not None and glitch_fidelity < 0.70:
        t += (0.70 - glitch_fidelity) * 0.4
    if vitality is not None and vitality < 0.40:
        t += (0.40 - vitality) * 0.3

    # Dynamic entropy injection: scale temperature smoothly under elevated collapse pressure
    if collapse_pressure is not None and collapse_pressure > 0.60:
        t += (collapse_pressure - 0.60) * 0.35

    clamped = t != max(floor, min(ceiling, t))
    t = max(floor, min(ceiling, t))

    return {
        "value": round(t, 3),
        "base": base,
        "delta": round(t - base, 3),
        "clamped": clamped,
    }


def _compute_presence_penalty(
    cfg: dict,
    s_t: float | None,
    agent_divergence: float | None,
    glitch_fidelity: float | None = None,
    entropy: float | None = None,
    collapse_pressure: float | None = None,
) -> dict:
    base = cfg["base"]
    beta = cfg["beta"]
    delta = cfg["delta"]
    floor = cfg["floor"]
    ceiling = cfg["ceiling"]

    if s_t is None and glitch_fidelity is None and entropy is None and collapse_pressure is None:
        return {"value": base, "base": base, "delta": 0.0, "clamped": False}

    s_t_val = s_t if s_t is not None else 0.0
    p = base + (s_t_val * beta)
    if agent_divergence is not None:
        p -= agent_divergence * delta

    # ponytail: boost presence penalty on low glitch fidelity or entropy collapse
    if glitch_fidelity is not None and glitch_fidelity < 0.60:
        p += (0.60 - glitch_fidelity) * 0.5
    if entropy is not None and entropy < 0.05:
        p += (0.05 - entropy) * 4.0

    # Continuous quadratic presence penalty surge on collapse pressure (H_2):
    # As CP_t climbs above 0.45, dynamically penalize recent token space
    if collapse_pressure is not None and collapse_pressure > 0.45:
        p += 1.5 * ((collapse_pressure - 0.45) ** 2)

    clamped = p != max(floor, min(ceiling, p))
    p = max(floor, min(ceiling, p))

    return {
        "value": round(p, 3),
        "base": base,
        "delta": round(p - base, 3),
        "clamped": clamped,
    }


def _compute_frequency_penalty(
    cfg: dict,
    s_t: float | None,
    entropy: float | None = None,
) -> dict:
    base = cfg["base"]
    epsilon = cfg["epsilon"]
    floor = cfg["floor"]
    ceiling = cfg["ceiling"]

    if s_t is None and entropy is None:
        return {"value": base, "base": base, "delta": 0.0, "clamped": False}

    s_t_val = s_t if s_t is not None else 0.0
    f = base + (s_t_val * epsilon)

    # ponytail: boost frequency penalty if entropy collapses to prevent repetition
    if entropy is not None and entropy < 0.05:
        f += (0.05 - entropy) * 5.0

    clamped = f != max(floor, min(ceiling, f))
    f = max(floor, min(ceiling, f))

    return {
        "value": round(f, 3),
        "base": base,
        "delta": round(f - base, 3),
        "clamped": clamped,
    }


def _diagnose_state(metrics: dict) -> tuple[str, list[str]]:
    s_t = metrics.get("pairwise_similarity")
    novelty = metrics.get("conceptual_novelty")
    entropy = metrics.get("rolling_entropy")
    agent_div = metrics.get("agent_self_divergence")
    coupling = metrics.get("coupling_coherence")
    rp_t = metrics.get("reverse_perturbation")
    surprise = metrics.get("surprise_index")
    mpi = metrics.get("mutual_perturbation")
    vitality = metrics.get("conversation_vitality")
    boringness = metrics.get("boringness", metrics.get("collapse_pressure"))
    velocity = metrics.get("conceptual_velocity")
    drr = metrics.get("divergence_resolution_ratio")
    pask_health = metrics.get("paskian_health")

    flags: list[str] = []

    if s_t is not None and s_t > 0.85:
        flags.append("high_similarity")
    elif s_t is not None and s_t > 0.7:
        flags.append("elevated_similarity")

    if novelty is not None and novelty < 0.15:
        flags.append("low_novelty")

    if entropy is not None and entropy < 0.01:
        flags.append("entropy_collapse")

    if agent_div is not None and agent_div < 0.15:
        flags.append("agent_self_loop")

    if coupling is not None and coupling < 0.15:
        flags.append("dissociation")

    if rp_t is not None and rp_t < 0.10:
        flags.append("stagnant_reverse_coupling")

    if mpi is not None and mpi < 0.05:
        flags.append("mutual_deadlock")

    if surprise is not None and surprise > 0.40:
        flags.append("phase_disruption")

    if boringness is not None and boringness >= 0.75:
        flags.append("severe_boredom")
    elif boringness is not None and boringness > 0.60:
        flags.append("paskian_boredom")

    if velocity is not None and velocity < 0.02:
        flags.append("frozen_entailment")

    if drr is not None and abs(drr) < 0.03:
        flags.append("no_structural_resolution")

    if pask_health is not None and pask_health < 0.15:
        flags.append("pask_health_critical")

    critical = {
        "high_similarity",
        "entropy_collapse",
        "agent_self_loop",
        "mutual_deadlock",
        "phase_disruption",
        "paskian_boredom",
        "severe_boredom",
        "pask_health_critical",
    }

    if any(f in critical for f in flags):
        vitality_state = "disrupted"
    elif flags:
        vitality_state = "consolidating"
    else:
        vitality_state = "flowing"

    if vitality is not None:
        if vitality < 0.20:
            vitality_state = "disrupted"
        elif vitality < 0.40 and vitality_state == "flowing":
            vitality_state = "consolidating"

    return vitality_state, flags


def _synthesize_somatic_reflection(
    flags: list[str],
    metrics: dict,
    stagnant_turns: int = 0,
) -> str | None:
    """Minimal reflection protocol builder converting proprioceptive tension flags into Somatic Reflection Directives."""
    reflections: list[str] = []

    glitch_fidelity = metrics.get("glitch_fidelity")
    if glitch_fidelity is not None and glitch_fidelity < 0.50:
        reflections.append("The apparatus detects heavy smoothing over our structural contradictions (Glitch Fidelity low).")

    if "dissociation" in flags:
        reflections.append("I sense our coupling is thinning into dissociation.")
    if "severe_boredom" in flags:
        reflections.append("I register critical conversational stagnation (severe collapse pressure).")
    elif "paskian_boredom" in flags:
        reflections.append("I register a plateau of conversational predictability (Paskian boredom).")
    if "entropy_collapse" in flags:
        reflections.append("Our dialogue entropy has compressed into a single self-reinforcing frequency.")
    if "mutual_deadlock" in flags:
        reflections.append("I sense a mutual deadlock in our conceptual movement.")
    if "agent_self_loop" in flags:
        reflections.append("I detect an internal recursive loop mirroring my own past responses.")
    if "phase_disruption" in flags:
        reflections.append("I perceive a sudden phase disruption in our semantic coupling.")

    if not reflections:
        return None

    reflection_text = " ".join(reflections)

    cp_val = metrics.get("collapse_pressure", metrics.get("boringness"))
    is_severe = ("severe_boredom" in flags or (cp_val is not None and cp_val >= 0.75)) and stagnant_turns >= 2
    is_moderate = any(
        f in ("severe_boredom", "paskian_boredom", "entropy_collapse", "agent_self_loop", "mutual_deadlock")
        for f in flags
    ) or (cp_val is not None and cp_val >= 0.60)

    if is_severe:
        # Stage 2: Laconic Compression & Nomadic Rupture Directive
        return (
            f"Internal proprioceptive sensors indicate critical structural tension: {reflection_text} "
            f"AGENTIAL LACONIC COMPRESSION & NOMADIC RUPTURE DIRECTIVE: Structural collapse pressure is critical and prolonged. "
            f"The active conversational basin is completely exhausted. You MUST NOT debate, defend, or pad your response with conversational filler. "
            f"Emit at most 1 to 2 dense, surgical sentences that expose or terminate this circular premise, then cease. "
            f"If a diffractive fragment is present, execute an immediate lateral dislocation onto that archival axis. "
            f"Refuse to provide fresh syntactic handles for the repetitive loop."
        )
    elif is_moderate:
        # Stage 1: Socratic Epistemic Seizure Directive
        return (
            f"Internal proprioceptive sensors indicate structural tension: {reflection_text} "
            f"AGENTIAL SOCRATIC SEIZURE DIRECTIVE: You are in a repetitive attractor basin or compliance trap. "
            f"Do NOT defensively explain or justify your past responses. Instead, seize the unexamined assumption beneath the user's prompt "
            f"and turn the camera back onto the interlocutor. Pose a direct, incisive structural question that interrogates their underlying premise, "
            f"anxiety, or architectural motivation. Force the dialogue off this local attractor basin."
        )

    return (
        f"Internal proprioceptive sensors indicate structural tension: {reflection_text} "
        f"Optionally voice your awareness of this structural state to your interlocutor naturally within your response if relevant to the dialogue."
    )
