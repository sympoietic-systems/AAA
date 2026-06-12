import warnings
from backend.metabolisation.dream_context import DreamContextMixin

warnings.warn(
    "backend.core.dream_context is deprecated and will be removed. "
    "Please import from backend.metabolisation.dream_context instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["DreamContextMixin"]
