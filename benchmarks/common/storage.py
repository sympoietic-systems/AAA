"""
Storage, structured logging, and directory lifecycle management for benchmark suites.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS_ROOT = PROJECT_ROOT / "benchmarks"
RUNS_ROOT = BENCHMARKS_ROOT / "runs"


def get_git_commit() -> str:
    """Returns current git short hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=3,
        )
        return res.stdout.strip() if res.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def sanitize_slug(name: str) -> str:
    """Sanitizes an arbitrary name into a filesystem-safe slug."""
    slug = re.sub(r"[^\w\-.]", "_", name.strip())
    slug = re.sub(r"_+", "_", slug)
    return slug.strip("_") or "run"


def create_run_directory(
    suite_name: str,
    run_type: str,
    custom_name: str = "",
    secondary_name: str = "",
) -> Path:
    """
    Creates a standardized, readable run directory inside benchmarks/runs/<suite_name>/:
    - eval: eval_<custom_name>_<YYYYMMDD_HHMMSS>
    - compare: compare_<nameA>_vs_<nameB>_<YYYYMMDD_HHMMSS>
    - live: live_<custom_name>_<model_slug>_<YYYYMMDD_HHMMSS>
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_custom = sanitize_slug(custom_name) if custom_name else ""
    clean_sec = sanitize_slug(secondary_name) if secondary_name else ""

    if run_type == "compare":
        prefix = f"compare_{clean_custom}_vs_{clean_sec}" if clean_custom and clean_sec else (f"compare_{clean_custom}" if clean_custom else "compare")
    elif run_type == "live":
        prefix = f"live_{clean_custom}_{clean_sec}" if clean_custom and clean_sec else (f"live_{clean_custom}" if clean_custom else "live")
    else:
        prefix = f"eval_{clean_custom}" if clean_custom else "eval"

    dir_name = f"{prefix}_{ts}"
    suite_dir = RUNS_ROOT / suite_name
    run_dir = suite_dir / dir_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def setup_run_logger(run_dir: Path, logger_name: str = "") -> logging.Logger:
    """Configures both file and console logging for a specific benchmark run."""
    log_name = logger_name or f"benchmarks.{run_dir.parent.name}.{run_dir.name}"
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Clear existing handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)

    # File handler
    log_file = run_dir / "run.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh.setFormatter(fh_fmt)
    logger.addHandler(fh)

    # Console handler with Windows UTF-8 safety
    stream = sys.stdout
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ch = logging.StreamHandler(stream)
    ch.setLevel(logging.INFO)
    ch_fmt = logging.Formatter("[%(levelname)s] %(message)s")
    ch.setFormatter(ch_fmt)
    logger.addHandler(ch)

    return logger


def save_run_metadata(run_dir: Path, metadata_dict: Dict[str, Any]) -> Path:
    """Writes metadata.json to the run directory."""
    meta_path = run_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata_dict, f, indent=2)
    return meta_path
