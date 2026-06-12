import warnings
from backend.metabolisation.context import PipelineResult

warnings.warn(
    "backend.core.context is deprecated and will be removed. "
    "Please import from backend.metabolisation.context instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["PipelineResult"]
