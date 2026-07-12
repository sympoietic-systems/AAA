import asyncio
import logging
import sys

from backend.utils.filesystem import ensure_upload_dir, get_upload_path

logger = logging.getLogger(__name__)


class FileService:
    @staticmethod
    def map_extension_to_type(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
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
        ensure_upload_dir(conversation_id)
        cached_filepath = get_upload_path(conversation_id, filename)
        with open(cached_filepath, "wb") as f:
            f.write(file_bytes)
        return cached_filepath

    @staticmethod
    async def run_digest_worker(conversation_id: str, file_name: str, file_type: str, reprocess: bool = False):
        cmd = [
            sys.executable,
            "-m",
            "backend.workers.digest_worker",
            "--conversation_id",
            conversation_id,
            "--file_name",
            file_name,
            "--file_type",
            file_type,
        ]
        if reprocess:
            cmd.append("--reprocess")

        logger.info("Spawning async digest worker subprocess: %s", " ".join(cmd))
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="replace").strip()
                logger.error(
                    "Digest worker failed with code %d for %s. Stderr:\n%s", proc.returncode, file_name, err_msg
                )
            else:
                out_msg = stdout.decode("utf-8", errors="replace").strip()
                logger.info("Digest worker completed successfully for %s. Output:\n%s", file_name, out_msg)
        except Exception:
            logger.exception("Failed to run digest worker subprocess for %s", file_name)

    @staticmethod
    async def process_and_summarize(app_state, conversation_id: str, file_name: str, file_type: str, file_content=None):
        await FileService.run_digest_worker(conversation_id, file_name, file_type, reprocess=False)

    @staticmethod
    async def reprocess_and_summarize(app_state, conversation_id: str, file_name: str, file_type: str):
        await FileService.run_digest_worker(conversation_id, file_name, file_type, reprocess=True)
