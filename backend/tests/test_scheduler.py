import asyncio
import os
import shutil
import sys
from pathlib import Path

root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)
os.chdir(root_path)

from backend.metabolisation.scheduler import BackgroundStartupScheduler  # noqa: E402
from backend.storage.database import get_db_path, init_db  # noqa: E402
from backend.storage.repository import ConversationRepository, PerceptionSedimentRepository  # noqa: E402


class MockAppState:
    def __init__(self, perception_repo, conversation_repo):
        self.perception_repo = perception_repo
        self.conversation_repo = conversation_repo
        self.message_repo = None
        self.belief_metabolism = None
        self.config = {"perception": {"max_concurrent_indexing_jobs": 2}}


async def test_scheduler_resumption():
    db_path = str(get_db_path("data/aaa_scheduler_test.db"))
    conn = init_db(db_path)

    # Clean DB
    conn.execute("DELETE FROM perception_sediment")
    conn.execute("DELETE FROM perception_files")
    conn.execute("DELETE FROM conversations")
    conn.commit()

    repo = PerceptionSedimentRepository(db_path)
    conv_repo = ConversationRepository(db_path)

    conv_id = "test_scheduler_conv"
    file_name = "test_resumed_file.txt"

    # Create records
    conv_repo.create(conv_id, title="Test Scheduler")
    repo.create_file(conv_id, file_name, "text", "processing")

    # Write mock cache file
    cache_dir = os.path.join("backend", "data", "uploads", conv_id)
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, file_name)
    with open(cache_path, "wb") as f:
        f.write(b"Hello world from resumed task cache!")

    app_state = MockAppState(repo, conv_repo)

    calls = []

    async def mock_process_file_func(state, conversation_id, name, file_type, content):
        calls.append((conversation_id, name, file_type, content))
        # Update the file status to ready to simulate completion
        state.perception_repo.update_file(
            conversation_id=conversation_id, file_name=name, status="ready", summary="Processed successfully"
        )

    scheduler = BackgroundStartupScheduler(app_state, mock_process_file_func)

    # Run resumption manually
    await scheduler._resume_indexing_tasks()

    # Verify the callback was triggered
    assert len(calls) == 1
    assert calls[0][0] == conv_id
    assert calls[0][1] == file_name
    assert calls[0][2] == "text"
    assert calls[0][3] is None  # Should be None to indicate cache load

    # Verify database status is updated
    files = repo.get_files_by_conversation(conv_id)
    assert len(files) == 1
    assert files[0]["status"] == "ready"
    assert files[0]["summary"] == "Processed successfully"

    # Verify status report matches
    status = scheduler.get_status()
    assert status["indexing_tasks_found"] == 1
    assert status["indexing_tasks_completed"] == 1
    assert status["indexing_tasks_failed"] == 0

    print("Scheduler Resumption: OK")

    # Clean up
    conn.close()
    for p in [db_path, db_path + "-wal", db_path + "-shm"]:
        if os.path.exists(p):
            os.remove(p)

    # Clean up cache files
    shutil.rmtree(os.path.join("backend", "data", "uploads", conv_id), ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(test_scheduler_resumption())
    print("All scheduler tests passed!")
