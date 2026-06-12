import warnings
from backend.metabolisation.pipeline import ProcessingPipeline

warnings.warn(
    "backend.core.pipeline is deprecated and will be removed. "
    "Please import from backend.metabolisation.pipeline instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ProcessingPipeline"]
