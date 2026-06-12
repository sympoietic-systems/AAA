import warnings
from backend.metabolisation.dream_prompts import DreamPromptMixin

warnings.warn(
    "backend.core.dream_prompts is deprecated and will be removed. "
    "Please import from backend.metabolisation.dream_prompts instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["DreamPromptMixin"]
