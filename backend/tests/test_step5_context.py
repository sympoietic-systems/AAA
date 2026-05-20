import asyncio
import os
import sys

sys.path.insert(0, "D:/AAA")
os.chdir("D:/AAA")

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import ErrorLogRepository, MessageRepository
from backend.modules.context_collector import ContextCollectorModule
from backend.core.pipeline import ProcessingPipeline
from backend.core.registry import ModuleRegistry


async def test_context_collector():
    db_path = str(get_db_path("data/aaa_ctx_test.db"))
    conn = init_db(db_path)
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
    os.remove(db_path)
    os.remove(db_path + "-wal")
    os.remove(db_path + "-shm")
    print("All context collector tests passed!")


asyncio.run(test_context_collector())
