"""Backward-compatibility shim — delegates to backend.utils.vector.

The canonical cosine_similarity now lives in backend.utils.vector to
consolidate all vector-related utilities in one module.
"""

from backend.utils.vector import cosine_similarity  # noqa: F401
