import logging

from backend.pipeline.metadata import ModuleMeta

from .base import ProcessingModule

logger = logging.getLogger(__name__)


class SelfInitiationArbiterModule(ProcessingModule):
    """# ponytail: minimal self-initiation arbiter closing sensorimotor perturbation trigger loop.
    
    Evaluates internal proprioceptive metrics per turn and autonomously initiates
    perturbations (such as Random Sediment Gratings or diffractive boosts) without
    waiting for external polling daemons or explicit user commands.
    """

    @property
    def name(self) -> str:
        return "self_initiation_arbiter"

    @property
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="self_initiation_arbiter",
            description="Autonomously initiates perturbations based on internal proprioceptive state",
            category="reasoning",
            always_run=True,
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        metrics = payload.get("metrics") or {}
        glitch_fidelity = metrics.get("glitch_fidelity", payload.get("glitch_fidelity"))
        entropy = metrics.get("rolling_entropy")
        vitality = metrics.get("conversation_vitality")
        s_t = metrics.get("pairwise_similarity")
        collapse_pressure = metrics.get("collapse_pressure", metrics.get("boringness"))

        # 1. Hyper-Fluency / Sedation Interrupt -> Auto-trigger Random Sediment Grating
        sedation_by_entropy = (
            glitch_fidelity is not None
            and glitch_fidelity >= 0.75
            and entropy is not None
            and entropy < 0.03
        )
        sedation_by_similarity = s_t is not None and s_t > 0.88
        sedation_by_collapse = collapse_pressure is not None and collapse_pressure > 0.70

        if (sedation_by_entropy or sedation_by_similarity or sedation_by_collapse) and not payload.get("grating_requested"):
            payload["grating_requested"] = True
            payload["self_initiated_action"] = "GRATING_SEDATION"
            payload["self_initiation_reason"] = (
                "Autonomously requested sediment grating to break hyper-fluency/collapse pressure"
            )
            logger.info(
                "self_initiation_arbiter: Autonomously requested Sediment Grating (GF=%s, Entropy=%s, Similarity=%s)",
                glitch_fidelity,
                entropy,
                s_t,
            )

        # 2. Vitality Crisis -> Auto-trigger Diffractive Perturbation Boost
        if vitality is not None and vitality < 0.25:
            payload["diffractive_boost"] = True
            if "self_initiated_action" not in payload:
                payload["self_initiated_action"] = "VITALITY_PERTURBATION"
                payload["self_initiation_reason"] = (
                    "Autonomously boosted diffractive retrieval due to vitality stagnation"
                )
            logger.info(
                "self_initiation_arbiter: Autonomously requested diffractive perturbation boost (Vitality=%.2f)",
                vitality,
            )

        return payload
