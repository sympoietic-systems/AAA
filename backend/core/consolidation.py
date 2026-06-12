import warnings
from backend.metabolisation.consolidation import ConsolidationMixin

warnings.warn(
    "backend.core.consolidation is deprecated and will be removed. "
    "Please import from backend.metabolisation.consolidation instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ConsolidationMixin"]
