"""Security utilities for endpoint hardening, file upload validation, and path traversal protection."""

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Default maximum upload size per file (100 MB)
DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024

# Explicitly blocked executable extensions (native binaries, system scripts, installers)
BLOCKED_EXTENSIONS = {
    # Windows native executables and libraries
    "exe",
    "dll",
    "sys",
    "scr",
    "pif",
    "com",
    "cpl",
    "drv",
    "ocx",
    "msi",
    "msp",
    "hta",
    # Shell and scripting languages executed by OS shells
    "bat",
    "cmd",
    "ps1",
    "psm1",
    "psd1",
    "sh",
    "bash",
    "zsh",
    "fish",
    "ksh",
    "csh",
    "vbs",
    "vbe",
    "wsf",
    "wsh",
    # Unix native binaries and libraries
    "bin",
    "elf",
    "so",
    "dylib",
    "app",
    "pkg",
    "deb",
    "rpm",
    "jar",
}

# Whitelist of allowed extensions for document/data ingestion and visual perception
ALLOWED_EXTENSIONS = {
    # Images
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "bmp",
    "svg",
    # Documents
    "pdf",
    "docx",
    "md",
    "epub",
    "mobi",
    "txt",
    "rtf",
    # Data & configuration
    "json",
    "yaml",
    "yml",
    "csv",
    "xml",
    "toml",
    "ini",
    "cfg",
    "log",
    # Safe text source code for semantic analysis
    "py",
    "ts",
    "tsx",
    "js",
    "jsx",
    "rs",
    "go",
    "java",
    "c",
    "h",
    "cpp",
    "hpp",
    "html",
    "css",
    "sql",
}

# Dangerous binary signatures (magic numbers) to detect disguised executables
DANGEROUS_MAGIC_HEADERS: list[tuple[bytes, str]] = [
    (b"MZ", "Windows PE executable/DLL"),
    (b"\x7fELF", "Linux ELF binary"),
    (b"\xca\xfe\xba\xbe", "Mach-O Universal / Java class binary"),
    (b"\xfe\xed\xfa\xce", "Mach-O 32-bit binary"),
    (b"\xfe\xed\xfa\xcf", "Mach-O 64-bit binary"),
    (b"\xce\xfa\xed\xfe", "Mach-O 32-bit (reverse) binary"),
    (b"\xcf\xfa\xed\xfe", "Mach-O 64-bit (reverse) binary"),
    (b"\x4c\x00\x00\x00\x01\x14\x02\x00", "Windows Shell Shortcut (.lnk)"),
]


def sanitize_identifier(identifier: str, field_name: str = "Identifier") -> str:
    """Validate and sanitize an identifier (e.g., conversation_id).

    Ensures the identifier only contains safe characters: letters, digits, underscores, hyphens.
    Rejects path traversal tokens such as '..' or slashes.
    """
    if not identifier or not isinstance(identifier, str):
        raise ValueError(f"{field_name} must be a non-empty string")

    cleaned = identifier.strip()
    if not re.fullmatch(r"^[a-zA-Z0-9_-]+$", cleaned):
        raise ValueError(f"Invalid {field_name}: contains illegal characters or path traversal elements")

    return cleaned


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent directory traversal and injection.

    - Strips directory paths (e.g. '../../')
    - Removes null bytes and control characters
    - Strips leading hyphens/dots (preventing CLI option injection)
    - Constrains characters to [a-zA-Z0-9._-]
    """
    if not filename or not isinstance(filename, str):
        return "unnamed_file.txt"

    # Remove any directory components (both Unix / and Windows \)
    name = os.path.basename(filename.replace("\\", "/"))

    # Remove null bytes and control chars
    name = "".join(c for c in name if c.isprintable() and c != "\0")

    # Split name and extension
    if "." in name:
        base, ext = name.rsplit(".", 1)
        ext = re.sub(r"[^a-zA-Z0-9]", "", ext).lower()
    else:
        base, ext = name, ""

    # Sanitize base: allow alphanumeric, underscore, hyphen
    clean_base = re.sub(r"[^a-zA-Z0-9_-]", "_", base)
    clean_base = clean_base.strip("._- ")

    if not clean_base:
        clean_base = "upload"

    # Prevent CLI option injection (leading hyphens)
    clean_base = clean_base.lstrip("-")
    if not clean_base:
        clean_base = "upload"

    return f"{clean_base}.{ext}" if ext else clean_base


def safe_resolve_path(base_dir: str | Path, *subpaths: str) -> Path:
    """Safely resolve a target path within base_dir, strictly preventing path traversal.

    Raises PermissionError if target path resolves outside base_dir.
    """
    base = Path(base_dir).resolve()
    target = base.joinpath(*subpaths).resolve()

    try:
        target.relative_to(base)
    except ValueError as e:
        logger.error("Path traversal attempt detected: %s outside base %s", target, base)
        raise PermissionError(f"Access denied: target path escapes designated directory {base}") from e

    return target


def check_magic_bytes(file_bytes: bytes) -> tuple[bool, str | None]:
    """Inspect the first bytes of file content for known executable signatures.

    Returns (is_dangerous, reason).
    """
    if not file_bytes:
        return False, None

    header = file_bytes[:16]
    for magic, description in DANGEROUS_MAGIC_HEADERS:
        if header.startswith(magic):
            return True, description

    return False, None


def validate_file_upload(
    filename: str,
    file_bytes: bytes,
    max_bytes: int = DEFAULT_MAX_FILE_SIZE,
) -> tuple[str, str]:
    """Perform comprehensive validation on an uploaded file.

    1. Checks file size against max_bytes (default 100MB).
    2. Sanitizes filename against directory traversal and CLI injection.
    3. Verifies extension against BLOCKED_EXTENSIONS and ALLOWED_EXTENSIONS.
    4. Performs magic bytes analysis to catch disguised executables.
    5. Returns (safe_filename, mapped_file_type).

    Raises ValueError on any violation.
    """
    # 1. Size check
    if len(file_bytes) > max_bytes:
        raise ValueError(f"File size ({len(file_bytes)} bytes) exceeds maximum limit ({max_bytes} bytes / {max_bytes // (1024 * 1024)}MB)")

    if len(file_bytes) == 0:
        raise ValueError("Uploaded file is empty (0 bytes)")

    # 2. Sanitize filename
    safe_name = sanitize_filename(filename)
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""

    if not ext:
        raise ValueError("File must have an extension")

    # 3. Check blocked extensions
    if ext in BLOCKED_EXTENSIONS:
        raise ValueError(f"File type '.{ext}' is blocked for security reasons (executable/script files are forbidden)")

    # 4. Check allowed extensions
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '.{ext}'. Allowed types: documents, data files, and images")

    # 5. Magic bytes inspection
    is_dangerous, reason = check_magic_bytes(file_bytes)
    if is_dangerous:
        raise ValueError(f"Uploaded file disguised as '.{ext}' contains dangerous binary header ({reason})")

    # 6. Map to high-level category
    from backend.services.file import FileService

    file_type = FileService.map_extension_to_type(safe_name)

    return safe_name, file_type
