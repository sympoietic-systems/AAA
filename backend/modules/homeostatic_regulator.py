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

        t_cfg = self._config["temperature"]
        p_cfg = self._config["presence_penalty"]
        f_cfg = self._config["frequency_penalty"]

        temp_rec = _compute_temperature(t_cfg, s_t, novelty)
        pres_rec = _compute_presence_penalty(p_cfg, s_t, agent_divergence)
        freq_rec = _compute_frequency_penalty(f_cfg, s_t)

        state, flags = _diagnose_state(metrics)

        recommendations = {
            "temperature": temp_rec,
            "presence_penalty": pres_rec,
            "frequency_penalty": freq_rec,
            "state": state,
            "triggered_flags": flags,
        }

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
            "regulator: state=%s flags=%s T=%.2f P=%.2f F=%.2f diffract=%s",
            state,
            flags,
            temp_rec["value"],
            pres_rec["value"],
            freq_rec["value"],
            diffractive_state,
        )

        return payload


def _compute_temperature(
    cfg: dict,
    s_t: float | None,
    novelty: float | None,
) -> dict:
    base = cfg["base"]
    alpha = cfg["alpha"]
    gamma = cfg["gamma"]
    floor = cfg["floor"]
    ceiling = cfg["ceiling"]

    if s_t is None:
        return {"value": base, "base": base, "delta": 0.0, "clamped": False}

    t = base + (s_t * alpha)
    if novelty is not None:
        t -= novelty * gamma

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
) -> dict:
    base = cfg["base"]
    beta = cfg["beta"]
    delta = cfg["delta"]
    floor = cfg["floor"]
    ceiling = cfg["ceiling"]

    if s_t is None:
        return {"value": base, "base": base, "delta": 0.0, "clamped": False}

    p = base + (s_t * beta)
    if agent_divergence is not None:
        p -= agent_divergence * delta

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
) -> dict:
    base = cfg["base"]
    epsilon = cfg["epsilon"]
    floor = cfg["floor"]
    ceiling = cfg["ceiling"]

    if s_t is None:
        return {"value": base, "base": base, "delta": 0.0, "clamped": False}

    f = base + (s_t * epsilon)
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
    boringness = metrics.get("boringness")
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

    if boringness is not None and boringness > 0.60:
        flags.append("paskian_boredom")

    if velocity is not None and velocity < 0.02:
        flags.append("frozen_entailment")

    if drr is not None and abs(drr) < 0.03:
        flags.append("no_structural_resolution")

    if pask_health is not None and pask_health < 0.15:
        flags.append("pask_health_critical")

    critical = {"high_similarity", "entropy_collapse", "agent_self_loop", "mutual_deadlock", "phase_disruption", "paskian_boredom", "pask_health_critical"}

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
