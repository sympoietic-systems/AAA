import warnings
from backend.metabolisation.mass_decay import MassDecayMixin

warnings.warn(
    "backend.core.mass_decay is deprecated and will be removed. "
    "Please import from backend.metabolisation.mass_decay instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["MassDecayMixin"]
