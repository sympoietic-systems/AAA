"""
Common utilities, models, and interfaces for the modular benchmark platform.
"""

from .base import BaseBenchmarkSuite, RunMetadata
from .storage import (
    create_run_directory,
    get_git_commit,
    sanitize_slug,
    save_run_metadata,
    setup_run_logger,
)
from .loader import (
    DialogueDataset,
    DialogueMessage,
    load_dataset,
    resolve_dataset_path,
    resolve_embeddings,
)
from .visualizer import (
    BG_COLOR,
    PANEL_BG,
    TEXT_COLOR,
    SUBTEXT_COLOR,
    COLOR_GREEN,
    COLOR_ORANGE,
    COLOR_ICE_CYAN,
    COLOR_SLATE,
    COLOR_VIOLET,
    find_edge_path,
    capture_html_screenshot,
    to_pts,
    to_circ,
    make_grid,
)

__all__ = [
    "BaseBenchmarkSuite",
    "RunMetadata",
    "create_run_directory",
    "get_git_commit",
    "sanitize_slug",
    "save_run_metadata",
    "setup_run_logger",
    "DialogueDataset",
    "DialogueMessage",
    "load_dataset",
    "resolve_dataset_path",
    "resolve_embeddings",
    "BG_COLOR",
    "PANEL_BG",
    "TEXT_COLOR",
    "SUBTEXT_COLOR",
    "COLOR_GREEN",
    "COLOR_ORANGE",
    "COLOR_ICE_CYAN",
    "COLOR_SLATE",
    "COLOR_VIOLET",
    "find_edge_path",
    "capture_html_screenshot",
    "to_pts",
    "to_circ",
    "make_grid",
]
