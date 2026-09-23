import asyncio
import contextlib
import logging
import os
import sys
from pathlib import Path
from typing import BinaryIO

from backend.utils.filesystem import ensure_upload_dir, get_upload_path
from backend.utils.security import (
    ALLOWED_EXTENSIONS,
    BLOCKED_EXTENSIONS,
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_MAX_IMAGE_SIZE,
    sanitize_filename,
    sanitize_identifier,
    validate_file_upload_metadata,
)

logger = logging.getLogger(__name__)


class FileService:
    _digest_semaphore: asyncio.Semaphore | None = None
    _digest_loop: asyncio.AbstractEventLoop | None = None
    _digest_limit: int | None = None

    @classmethod
    def _get_digest_semaphore(cls, limit: int) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        bounded_limit = max(1, min(limit, 8))
        if cls._digest_semaphore is None or cls._digest_loop is not loop or cls._digest_limit != bounded_limit:
            cls._digest_semaphore = asyncio.Semaphore(bounded_limit)
            cls._digest_loop = loop
            cls._digest_limit = bounded_limit
        return cls._digest_semaphore

    @staticmethod
    def map_extension_to_type(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if not ext:
            raise ValueError("Filename must have an extension")

        if ext in BLOCKED_EXTENSIONS:
            raise ValueError(
                f"File type '.{ext}' is blocked for security reasons (executable/script files are forbidden)"
            )

        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type '.{ext}'")

        mapping = {
            "jpg": "image",
            "jpeg": "image",
            "png": "image",
            "gif": "image",
            "webp": "image",
            "bmp": "image",
            "svg": "image",
            "pdf": "pdf",
            "docx": "docx",
            "md": "md",
            "epub": "epub",
            "mobi": "mobi",
        }
        return mapping.get(ext, "txt")

    @staticmethod
    def cache_file(conversation_id: str, filename: str, file_bytes: bytes) -> str:
        safe_conv_id = sanitize_identifier(conversation_id, field_name="conversation_id")
        safe_name = sanitize_filename(filename)
        ensure_upload_dir(safe_conv_id)
        cached_filepath = get_upload_path(safe_conv_id, safe_name)
        with open(cached_filepath, "wb") as f:
            f.write(file_bytes)
        return cached_filepath

    @staticmethod
    def cache_upload_stream(
        conversation_id: str,
        filename: str,
        source: BinaryIO,
        *,
        max_file_bytes: int = DEFAULT_MAX_FILE_SIZE,
        max_image_bytes: int = DEFAULT_MAX_IMAGE_SIZE,
    ) -> tuple[str, str, int, str]:
        """Validate and atomically cache one spooled upload without duplicating it in memory."""
        safe_conv_id = sanitize_identifier(conversation_id, field_name="conversation_id")
        safe_name = sanitize_filename(filename)
        file_type = FileService.map_extension_to_type(safe_name)
        size_limit = min(max_file_bytes, max_image_bytes) if file_type == "image" else max_file_bytes
        ensure_upload_dir(safe_conv_id)
        target = Path(get_upload_path(safe_conv_id, safe_name))
        partial = target.with_name(f".{target.name}.part")
        if target.exists():
            raise ValueError(f"File '{safe_name}' already exists in this conversation")

        total_size = 0
        header = bytearray()
        try:
            source.seek(0)
            with partial.open("xb") as destination:
                while chunk := source.read(64 * 1024):
                    total_size += len(chunk)
                    if total_size > size_limit:
                        raise ValueError(
                            f"File size ({total_size} bytes) exceeds maximum limit "
                            f"({size_limit} bytes / {size_limit // (1024 * 1024)}MB)"
                        )
                    if len(header) < 64:
                        header.extend(chunk[: 64 - len(header)])
                    destination.write(chunk)

            safe_name, file_type = validate_file_upload_metadata(
                safe_name,
                bytes(header),
                total_size,
                max_bytes=size_limit,
            )
            os.replace(partial, target)
            return safe_name, file_type, total_size, str(target)
        except Exception:
            partial.unlink(missing_ok=True)
            raise

    @staticmethod
    def remove_cached_files(paths: list[str]) -> None:
        for raw_path in paths:
            path = Path(raw_path)
            path.unlink(missing_ok=True)
            with contextlib.suppress(OSError):
                path.parent.rmdir()

    @classmethod
    async def run_digest_worker(
        cls,
        conversation_id: str,
        file_name: str,
        file_type: str,
        *,
        reprocess: bool = False,
        max_concurrent: int = 3,
        timeout_seconds: float = 1800.0,
        perception_repo=None,
    ) -> bool:
        safe_conv_id = sanitize_identifier(conversation_id, field_name="conversation_id")
        safe_file_name = sanitize_filename(file_name)
        safe_file_type = sanitize_identifier(file_type, field_name="file_type")

        cmd = [
            sys.executable,
            "-m",
            "backend.workers.digest_worker",
            "--conversation_id",
            safe_conv_id,
            "--file_name",
            safe_file_name,
            "--file_type",
            safe_file_type,
        ]
        if reprocess:
            cmd.append("--reprocess")

        async def set_status(status: str) -> None:
            if perception_repo is not None:
                await asyncio.to_thread(
                    perception_repo.update_file,
                    conversation_id=conversation_id,
                    file_name=safe_file_name,
                    status=status,
                )

        semaphore = cls._get_digest_semaphore(max_concurrent)
        async with semaphore:
            logger.info("Spawning async digest worker subprocess: %s", " ".join(cmd))
            proc = None
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=max(1.0, timeout_seconds))
                if proc.returncode != 0:
                    err_msg = stderr.decode("utf-8", errors="replace").strip()
                    logger.error(
                        "Digest worker failed with code %d for %s. Stderr:\n%s", proc.returncode, file_name, err_msg
                    )
                    await set_status("error")
                    return False

                out_msg = stdout.decode("utf-8", errors="replace").strip()
                logger.info("Digest worker completed successfully for %s. Output:\n%s", file_name, out_msg)
                return True
            except TimeoutError:
                if proc is not None:
                    proc.kill()
                    await proc.communicate()
                logger.error("Digest worker timed out after %.1fs for %s", timeout_seconds, file_name)
                await set_status("error")
                return False
            except asyncio.CancelledError:
                if proc is not None:
                    proc.kill()
                    await proc.communicate()
                await set_status("cancelled")
                raise
            except Exception:
                logger.exception("Failed to run digest worker subprocess for %s", file_name)
                await set_status("error")
                return False

    @staticmethod
    async def process_and_summarize(app_state, conversation_id: str, file_name: str, file_type: str, file_content=None):
        config = getattr(app_state, "config", {}).get("uploads", {})
        await FileService.run_digest_worker(
            conversation_id,
            file_name,
            file_type,
            reprocess=False,
            max_concurrent=int(config.get("max_concurrent_workers", 3)),
            timeout_seconds=float(config.get("worker_timeout_seconds", 1800)),
            perception_repo=getattr(app_state, "perception_repo", None),
        )

    @staticmethod
    async def reprocess_and_summarize(app_state, conversation_id: str, file_name: str, file_type: str):
        config = getattr(app_state, "config", {}).get("uploads", {})
        await FileService.run_digest_worker(
            conversation_id,
            file_name,
            file_type,
            reprocess=True,
            max_concurrent=int(config.get("max_concurrent_workers", 3)),
            timeout_seconds=float(config.get("worker_timeout_seconds", 1800)),
            perception_repo=getattr(app_state, "perception_repo", None),
        )
