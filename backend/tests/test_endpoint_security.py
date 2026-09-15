"""Security tests for endpoint hardening, anti-executable upload, and path traversal prevention."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure backend package can be imported
sys.path.insert(0, ".")

from backend.main import app
from backend.utils.security import (
    DEFAULT_MAX_FILE_SIZE,
    check_magic_bytes,
    safe_resolve_path,
    sanitize_filename,
    sanitize_identifier,
    validate_file_upload,
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        password = os.environ.get("AAA_PASSWORD", "").strip()
        if password:
            test_client.headers.update({"Authorization": f"Bearer {password}"})
        yield test_client


def test_sanitize_identifier():
    assert sanitize_identifier("conv_123") == "conv_123"
    assert sanitize_identifier("a-b-c") == "a-b-c"

    # Traversal attempts must raise ValueError
    with pytest.raises(ValueError):
        sanitize_identifier("../../../etc")

    with pytest.raises(ValueError):
        sanitize_identifier("conv/with/slash")

    with pytest.raises(ValueError):
        sanitize_identifier("")


def test_sanitize_filename():
    assert sanitize_filename("test.txt") == "test.txt"
    # Strips path traversal
    assert sanitize_filename("../../secret.txt") == "secret.txt"
    assert sanitize_filename("..\\..\\windows.sys") == "windows.sys"
    # Strips leading hyphens (CLI injection protection)
    assert sanitize_filename("--flag.txt") == "flag.txt"
    # Strips null bytes
    assert sanitize_filename("test\0bad.txt") == "testbad.txt"


def test_safe_resolve_path(tmp_path):
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()

    # Normal child path works
    resolved = safe_resolve_path(base_dir, "conv1", "file.txt")
    assert resolved == base_dir / "conv1" / "file.txt"

    # Traversal escaping base_dir raises PermissionError
    with pytest.raises(PermissionError):
        safe_resolve_path(base_dir, "..", "outside.txt")

    with pytest.raises(PermissionError):
        safe_resolve_path(base_dir, "conv1", "..", "..", "outside.txt")


def test_validate_file_upload_blocked_extensions():
    # Executable extensions must be rejected
    blocked = ["payload.exe", "trojan.dll", "script.bat", "run.cmd", "exploit.sh", "install.msi", "hack.ps1"]
    for name in blocked:
        with pytest.raises(ValueError, match="blocked for security reasons"):
            validate_file_upload(name, b"echo hello")


def test_validate_file_upload_disguised_executable():
    # Disguised Windows PE file named .txt
    pe_header = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    with pytest.raises(ValueError, match="dangerous binary header"):
        validate_file_upload("innocent.txt", pe_header)

    # Disguised Linux ELF file named .png
    elf_header = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    with pytest.raises(ValueError, match="dangerous binary header"):
        validate_file_upload("picture.png", elf_header)


def test_validate_file_upload_size_limit():
    small_limit = 1024  # 1 KB
    oversized = b"A" * 2048
    with pytest.raises(ValueError, match="exceeds maximum limit"):
        validate_file_upload("data.txt", oversized, max_bytes=small_limit)


def test_validate_file_upload_valid():
    safe_name, file_type = validate_file_upload("report.md", b"# Safe Markdown Document\nContent")
    assert safe_name == "report.md"
    assert file_type == "md"

    safe_img, img_type = validate_file_upload("photo.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01")
    assert safe_img == "photo.jpg"
    assert img_type == "image"


# ── Integration API Tests ───────────────────────────────────────────────


def test_api_upload_blocked_executable(client):
    """Uploading an executable must be rejected with HTTP 400."""
    exe_content = b"echo hacked"
    files = {"files": ("malware.exe", exe_content, "application/octet-stream")}

    response = client.post("/api/conversations/new/files", files=files)
    assert response.status_code == 400
    assert "blocked for security reasons" in response.json()["detail"]


def test_api_upload_disguised_pe_binary(client):
    """Uploading an executable disguised as .txt must be detected via magic bytes and rejected."""
    pe_header = b"MZ" + b"\x00" * 30
    files = {"files": ("disguised.txt", pe_header, "text/plain")}

    response = client.post("/api/conversations/new/files", files=files)
    assert response.status_code == 400
    assert "dangerous binary header" in response.json()["detail"]


def test_api_upload_path_traversal_filename(client):
    """Uploading with path traversal filename must be sanitized so it does not escape upload directory."""
    content = b"This is safe content."
    files = {"files": ("../../escape.txt", content, "text/plain")}

    response = client.post("/api/conversations/new/files", files=files)
    assert response.status_code == 200
    data = response.json()
    # The filename must be sanitized to escape.txt without any traversal tokens
    assert data["files"][0]["file_name"] == "escape.txt"


def test_api_upload_invalid_conversation_id(client):
    """Path traversal in conversation_id must be rejected with HTTP 400."""
    files = {"files": ("test.txt", b"Safe content", "text/plain")}
    response = client.post("/api/conversations/..%2F..%2Fetc/files", files=files)
    assert response.status_code in (400, 404)


def test_api_upload_valid_document(client):
    """Legitimate text/markdown upload works properly."""
    content = b"# Architecture Overview\nThis is valid document content."
    files = {"files": ("architecture.md", content, "text/markdown")}

    response = client.post("/api/conversations/new/files", files=files)
    assert response.status_code == 200
    data = response.json()
    conv_id = data["conversation_id"]
    assert len(data["files"]) == 1
    assert data["files"][0]["file_name"] == "architecture.md"
    assert data["files"][0]["file_type"] == "md"

    # Cleanup
    client.delete(f"/api/conversations/{conv_id}/files/architecture.md")
