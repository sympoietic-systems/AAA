"""Child delivery is an attributed archive, never a parent conclusion.

Note: Canonical location is backend.storage.models.research.children.
"""

from backend.storage.models.research.children import *  # noqa: F403
from backend.storage.models.research.children import ChildEvidencePacket

__all__ = ["ChildEvidencePacket"]
