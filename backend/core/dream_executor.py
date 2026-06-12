import warnings
from backend.metabolisation.dream_executor import DreamExecutorMixin

warnings.warn(
    "backend.core.dream_executor is deprecated and will be removed. "
    "Please import from backend.metabolisation.dream_executor instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["DreamExecutorMixin"]
