"""Centralized logging configuration for AAA backend.

Provides:
- Rotating file handlers for error.log (WARNING+) and server.log (INFO+)
- SecretMaskingFilter conforming to protocols/SECURITY.md
- ANSI color formatter for interactive console streams
- Memory-efficient reverse block tailing for log inspection
- Integration with Uvicorn and FastAPI application lifecycle
"""

import contextlib
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# Default configuration constants
DEFAULT_LOG_DIR = "data/logs"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5


_SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Bearer tokens
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", re.IGNORECASE), r"\1[REDACTED]"),
    # OpenRouter keys (more specific than generic sk-)
    (re.compile(r"\bsk-or-v1-[a-zA-Z0-9]{64}\b"), "sk-or-v1-[REDACTED]"),
    # OpenAI / Anthropic / Generic sk- keys
    (re.compile(r"\bsk-[a-zA-Z0-9_\-]{20,}\b"), "sk-[REDACTED]"),
    # Google API keys
    (re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"), "AIza[REDACTED]"),
    # Key/Password query or assignment parameters
    (
        re.compile(
            r"""((?:api[_-]?key|password|secret|token|access_token|auth_token)\s*[:=]\s*["']?)[^"'\s,;&]+""",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]",
    ),
]


def mask_secrets(text: str) -> str:
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class SecretMaskingFilter(logging.Filter):
    """Redacts secrets from records before formatter interpolation."""

    def _mask_text(self, text: str) -> str:
        return mask_secrets(text)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._mask_text(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: (self._mask_text(v) if isinstance(v, str) else v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._mask_text(arg) if isinstance(arg, str) else arg for arg in record.args)

        if record.exc_text and isinstance(record.exc_text, str):
            record.exc_text = self._mask_text(record.exc_text)

        return True


class SecretMaskingFormatter(logging.Formatter):
    """Redact the final rendered message, including generated tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        return mask_secrets(super().format(record))


class _ColorFormatter(SecretMaskingFormatter):
    """ANSI color-coded log formatter for terminal output."""

    _COLORS = {
        "DEBUG": "\033[36m",  # cyan
        "INFO": "\033[32m",  # green
        "WARNING": "\033[33;1m",  # bold yellow
        "ERROR": "\033[31;1m",  # bold red
        "CRITICAL": "\033[41;97m",  # white on red background
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self._COLORS.get(record.levelname, "")
        orig_levelname = record.levelname
        orig_msg = record.msg
        if color:
            record.levelname = f"{color}{orig_levelname}{self._RESET}"
            record.msg = f"{color}{orig_msg}{self._RESET}"
        formatted = super().format(record)
        record.levelname = orig_levelname
        record.msg = orig_msg
        return formatted


def get_log_dir(config: dict[str, Any] | None = None) -> Path:
    """Resolve and ensure the logging directory exists."""
    log_dir_str = (
        (config.get("logging", {}).get("dir") if config else None) or os.environ.get("AAA_LOG_DIR") or DEFAULT_LOG_DIR
    )
    log_dir = Path(log_dir_str).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(config: dict[str, Any] | None = None) -> None:
    """Initialize system-wide logging with rotating files, console stream, and secret masking."""
    log_cfg = (config or {}).get("logging", {})
    if not log_cfg.get("enabled", True):
        return

    log_dir = get_log_dir(config)

    root_level_name = os.environ.get("AAA_LOG_LEVEL") or log_cfg.get("level", "INFO")
    root_level = getattr(logging, str(root_level_name).upper(), logging.INFO)

    error_level_name = os.environ.get("AAA_LOG_ERROR_LEVEL") or log_cfg.get("error_level", "WARNING")
    error_level = getattr(logging, str(error_level_name).upper(), logging.WARNING)

    max_bytes = int(os.environ.get("AAA_LOG_MAX_BYTES") or log_cfg.get("max_bytes", DEFAULT_MAX_BYTES))
    backup_count = int(os.environ.get("AAA_LOG_BACKUP_COUNT") or log_cfg.get("backup_count", DEFAULT_BACKUP_COUNT))

    root_logger = logging.getLogger()
    root_logger.setLevel(min(root_level, logging.INFO))

    # Remove previously installed AAA handlers to prevent duplication
    for h in list(root_logger.handlers):
        if getattr(h, "_aaa_handler", False):
            root_logger.removeHandler(h)
            with contextlib.suppress(Exception):
                h.close()

    masking_filter = SecretMaskingFilter()
    plain_formatter = SecretMaskingFormatter(
        "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = _ColorFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Error & Warning Rotating File Handler
    error_path = log_dir / "error.log"
    error_handler = RotatingFileHandler(
        error_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(error_level)
    error_handler.setFormatter(plain_formatter)
    error_handler.addFilter(masking_filter)
    error_handler._aaa_handler = True  # type: ignore[attr-defined]
    root_logger.addHandler(error_handler)

    # 2. Server Operational Rotating File Handler (All events INFO+)
    server_path = log_dir / "server.log"
    server_handler = RotatingFileHandler(
        server_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    server_handler.setLevel(logging.INFO)
    server_handler.setFormatter(plain_formatter)
    server_handler.addFilter(masking_filter)
    server_handler._aaa_handler = True  # type: ignore[attr-defined]
    root_logger.addHandler(server_handler)

    # 3. Console Stream Handler (if not already attached)
    has_console = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root_logger.handlers
    )
    if not has_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(root_level)
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(masking_filter)
        console_handler._aaa_handler = True  # type: ignore[attr-defined]
        root_logger.addHandler(console_handler)

    # Bridge Uvicorn loggers so internal ASGI crashes feed into file handlers
    for uvicorn_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        u_logger = logging.getLogger(uvicorn_name)
        u_logger.propagate = True


def tail_log_file(file_path: Path, max_lines: int = 100) -> list[str]:
    """Read the last `max_lines` from a file without loading the whole file into RAM.

    Uses a reverse seek block approach.
    """
    if not file_path.exists() or not file_path.is_file():
        return []

    lines: list[str] = []
    block_size = 8192

    with open(file_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        if file_size == 0:
            return []

        remaining_size = file_size
        buffer = bytearray()

        while remaining_size > 0 and len(lines) <= max_lines:
            read_size = min(block_size, remaining_size)
            remaining_size -= read_size
            f.seek(remaining_size, os.SEEK_SET)
            chunk = f.read(read_size)
            buffer = bytearray(chunk) + buffer

            # Split buffer into lines
            split_lines = buffer.split(b"\n")
            if remaining_size > 0:
                # First element might be incomplete; keep it in buffer
                buffer = split_lines[0]
                lines = [
                    line_bytes.decode("utf-8", errors="replace").strip("\r")
                    for line_bytes in split_lines[1:]
                    if line_bytes
                ] + lines
            else:
                lines = [
                    line_bytes.decode("utf-8", errors="replace").strip("\r") for line_bytes in split_lines if line_bytes
                ] + lines

    return lines[-max_lines:]
