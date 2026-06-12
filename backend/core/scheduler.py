import warnings
from backend.metabolisation.scheduler import BackgroundStartupScheduler

warnings.warn(
    "backend.core.scheduler is deprecated and will be removed. "
    "Please import from backend.metabolisation.scheduler instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["BackgroundStartupScheduler"]
