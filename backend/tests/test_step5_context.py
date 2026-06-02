from pathlib import Path
import sys
import os
import asyncio

root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)
os.chdir(root_path)

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import ErrorLogRepository, MessageRepository
from backend.modules.context_collector import ContextCollectorModule
from backend.core.pipeline import ProcessingPipeline
from backend.core.registry import ModuleRegistry


async def test_context_collector():
    db_path = str(get_db_path("data/aaa_ctx_test.db"))
    conn = init_db(db_path)
    conn.execute("DELETE FROM conversation_metrics")
    conn.execute("DELETE FROM conversation_log")
    conn.commit()
    repo = MessageRepository(db_path)

    import numpy as np

    emb = np.zeros(384, dtype="float32").tobytes()

    repo.insert("human", "What is the weather?", emb, "test", 384)
    repo.insert("apparatus", "It is sunny today.", emb, "test", 384)
    repo.insert("human", "Tell me more.", emb, "test", 384)

    mod = ContextCollectorModule(message_repo=repo, max_history=20)
    assert mod.validate()
    assert mod.name == "context_collector"

    result = await mod.process({"content": "What about tomorrow?", "speaker": "human"})
    messages = result.get("messages", [])

    print(f"Messages collected: {len(messages)}")
    for m in messages:
        print(f"  [{m['role']}] {m['content'][:50]}")

    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    assert messages[-1]["content"] == "What about tomorrow?"
    print("Context collector: OK")

    conn.close()
    import time
    time.sleep(0.1)
    for p in [db_path, db_path + "-wal", db_path + "-shm"]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except PermissionError:
            pass
    print("All context collector tests passed!")


asyncio.run(test_context_collector())

