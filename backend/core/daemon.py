import warnings
from backend.metabolisation.daemon import AutopoieticDreamDaemon

warnings.warn(
    "backend.core.daemon is deprecated and will be removed. "
    "Please import from backend.metabolisation.daemon instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["AutopoieticDreamDaemon"]
