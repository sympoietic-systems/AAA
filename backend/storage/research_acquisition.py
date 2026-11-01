"""Acquisition intent and cache access provenance, without content duplication.

Note: Canonical location is backend.storage.models.research.acquisition.
"""

from backend.storage.models.research.acquisition import *  # noqa: F403
from backend.storage.models.research.acquisition import AcquisitionReceipt

__all__ = ["AcquisitionReceipt"]
