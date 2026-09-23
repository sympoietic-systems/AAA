"""Sensory Modules Package."""

from backend.modules.sensory.afferent_sensory_router import AfferentSensoryRouter
from backend.modules.sensory.glitch_fidelity_engine import (
    compute_glitch_fidelity,
    compute_interference_variance,
    select_diffractive_prior,
)
from backend.modules.sensory.homeostatic_regulator import HomeostaticRegulatorModule
from backend.modules.sensory.perception import PerceptionModule
from backend.modules.sensory.self_initiation_arbiter import SelfInitiationArbiterModule
from backend.modules.sensory.trait_computer import DescriptiveTraits, TraitComputer

__all__ = [
    "AfferentSensoryRouter",
    "compute_interference_variance",
    "select_diffractive_prior",
    "compute_glitch_fidelity",
    "HomeostaticRegulatorModule",
    "PerceptionModule",
    "SelfInitiationArbiterModule",
    "DescriptiveTraits",
    "TraitComputer",
]
