import warnings
from backend.metabolisation.sedimentation import (
    generate_node_id,
    parse_sedimentation_yaml,
    merge_nodes,
    build_compact_node_summary,
    store_daemon_metrics,
    extract_human_summary,
)

warnings.warn(
    "backend.core.sedimentation is deprecated and will be removed. "
    "Please import from backend.metabolisation.sedimentation instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "generate_node_id",
    "parse_sedimentation_yaml",
    "merge_nodes",
    "build_compact_node_summary",
    "store_daemon_metrics",
    "extract_human_summary",
]
