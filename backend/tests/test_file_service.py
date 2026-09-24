import asyncio
import subprocess
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.services.file import FileService


def test_v22_file_service_import_is_cycle_free():
    result = subprocess.run(
        [sys.executable, "-c", "from backend.services.file import FileService"],
        cwd=".",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture(autouse=True)
def reset_digest_semaphore():
    FileService._digest_semaphore = None
    FileService._digest_loop = None
    FileService._digest_limit = None


@pytest.mark.asyncio
async def test_digest_worker_timeout_kills_process_and_marks_error():
    process = Mock(returncode=None)
    process.communicate = AsyncMock(side_effect=[TimeoutError, (b"", b"")])
    repo = Mock()

    with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)):
        ok = await FileService.run_digest_worker(
            "conv_1",
            "file.txt",
            "txt",
            timeout_seconds=0,
            perception_repo=repo,
        )

    assert ok is False
    process.kill.assert_called_once()
    repo.update_file.assert_called_once_with(conversation_id="conv_1", file_name="file.txt", status="error")


@pytest.mark.asyncio
async def test_digest_worker_concurrency_is_bounded():
    active = 0
    peak = 0
    release = asyncio.Event()

    class Process:
        returncode = 0

        async def communicate(self):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await release.wait()
            active -= 1
            return b"ok", b""

    async def spawn(*args, **kwargs):
        return Process()

    with patch("asyncio.create_subprocess_exec", new=spawn):
        tasks = [
            asyncio.create_task(FileService.run_digest_worker("conv_1", f"file_{idx}.txt", "txt", max_concurrent=2))
            for idx in range(4)
        ]
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert peak == 2
        release.set()
        assert all(await asyncio.gather(*tasks))
