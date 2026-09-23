import ipaddress
import logging
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Default maximum upload size per file (100 MB)
DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024
DEFAULT_MAX_IMAGE_SIZE = 5 * 1024 * 1024

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
    # Browser-active content can execute script when served or previewed.
    "svg",
    "html",
    "htm",
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
        raise ValueError(
            f"File size ({len(file_bytes)} bytes) exceeds maximum limit ({max_bytes} bytes / {max_bytes // (1024 * 1024)}MB)"
        )

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


def validate_file_upload_metadata(
    filename: str,
    file_header: bytes,
    file_size: int,
    *,
    max_bytes: int = DEFAULT_MAX_FILE_SIZE,
) -> tuple[str, str]:
    """Validate a streamed upload from its final size and leading bytes."""
    if file_size > max_bytes:
        raise ValueError(
            f"File size ({file_size} bytes) exceeds maximum limit ({max_bytes} bytes / {max_bytes // (1024 * 1024)}MB)"
        )
    if file_size == 0:
        raise ValueError("Uploaded file is empty (0 bytes)")

    safe_name = sanitize_filename(filename)
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if not ext:
        raise ValueError("File must have an extension")
    if ext in BLOCKED_EXTENSIONS:
        raise ValueError(f"File type '.{ext}' is blocked for security reasons (executable/script files are forbidden)")
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '.{ext}'. Allowed types: documents, data files, and images")

    is_dangerous, reason = check_magic_bytes(file_header)
    if is_dangerous:
        raise ValueError(f"Uploaded file disguised as '.{ext}' contains dangerous binary header ({reason})")

    from backend.services.file import FileService

    return safe_name, FileService.map_extension_to_type(safe_name)


def validate_safe_url(
    url: str,
    allowed_schemes: tuple[str, ...] = ("http", "https"),
    allow_private: bool = False,
) -> str:
    """Validate a URL against SSRF (Server-Side Request Forgery) attacks.

    - Verifies URL scheme is within allowed_schemes (default: http, https).
    - Checks that hostname is present.
    - Blocks localhost, loopback addresses (127.0.0.0/8, ::1).
    - Blocks private network ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7).
    - Blocks link-local addresses (169.254.0.0/16, fe80::/10) including cloud metadata targets.
    - Blocks reserved, multicast, and unspecified addresses.

    Raises ValueError on unsafe or malformed URLs. Returns the validated URL string.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    parsed = urlparse(url.strip())
    if not parsed.scheme or parsed.scheme.lower() not in allowed_schemes:
        raise ValueError(f"URL scheme '{parsed.scheme}' is not allowed (must be one of: {', '.join(allowed_schemes)})")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL is missing a valid hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL-embedded credentials are forbidden")

    cleaned_host = hostname.lower().strip("[]")
    if not allow_private and (
        cleaned_host in ("localhost", "0.0.0.0")
        or cleaned_host.endswith(".localhost")
        or cleaned_host.endswith(".local")
    ):
        raise ValueError(f"Access to local hostname '{hostname}' is forbidden")

    if not allow_private:
        # Check if the hostname is a direct IP literal
        try:
            ip = ipaddress.ip_address(cleaned_host)
            if (
                ip.is_loopback
                or ip.is_private
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise ValueError(f"Access to private or restricted IP address '{ip}' is forbidden")
        except ValueError as e:
            if "Access to private or restricted" in str(e):
                raise
            # Not a raw IP literal, resolve via DNS
            try:
                addr_infos = socket.getaddrinfo(cleaned_host, None)
                for _family, _, _, _, sockaddr in addr_infos:
                    ip_str = sockaddr[0]
                    resolved_ip = ipaddress.ip_address(ip_str)
                    if (
                        resolved_ip.is_loopback
                        or resolved_ip.is_private
                        or resolved_ip.is_link_local
                        or resolved_ip.is_multicast
                        or resolved_ip.is_reserved
                        or resolved_ip.is_unspecified
                    ):
                        raise ValueError(
                            f"URL destination '{hostname}' resolves to restricted IP address '{resolved_ip}'"
                        )
            except socket.gaierror as dns_err:
                raise ValueError(f"Failed to resolve hostname '{hostname}': {dns_err}") from dns_err

    return url.strip()
