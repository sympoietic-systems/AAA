from pathlib import Path
import sys
import os
import asyncio

root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)
os.chdir(root_path)

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import PerceptionSedimentRepository

async def test_file_by_name():
    db_path = str(get_db_path("data/aaa_file_test.db"))
    conn = init_db(db_path)
    conn.execute("DELETE FROM perception_files")
    conn.execute("DELETE FROM perception_sediment")
    conn.execute("DELETE FROM conversations")
    conn.commit()

    repo = PerceptionSedimentRepository(db_path)

    # 0. Insert a mock conversation
    conn.execute(
        "INSERT INTO conversations (id, title, agent_id) VALUES (?, ?, ?)",
        ("conv-123", "Test Title", "symbia")
    )

    # 1. Insert a mock file
    conn.execute(
        """INSERT INTO perception_files 
           (conversation_id, file_name, file_type, status, summary, summary_model, token_count, chunk_count)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("conv-123", "Autopoiesis.pdf", "pdf", "ready", "An essay on autopoiesis", "model-a", 100, 2)
    )
    
    # 2. Insert mock chunks
    conn.execute(
        """INSERT INTO perception_sediment
           (conversation_id, file_name, file_type, chunk_index, chunk_text, token_count, opacity, opacity_meta, structural_signature, embedding, embedding_model)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("conv-123", "Autopoiesis.pdf", "pdf", 0, "First chunk text", 50, 0, None, b"", b"", "test-model")
    )
    conn.execute(
        """INSERT INTO perception_sediment
           (conversation_id, file_name, file_type, chunk_index, chunk_text, token_count, opacity, opacity_meta, structural_signature, embedding, embedding_model)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("conv-123", "Autopoiesis.pdf", "pdf", 1, "Second chunk text", 50, 0, None, b"", b"", "test-model")
    )
    conn.commit()

    # 3. Test find_file_by_name
    file_info = repo.find_file_by_name("Autopoiesis.pdf")
    assert file_info is not None
    assert file_info["conversation_id"] == "conv-123"
    assert file_info["file_type"] == "pdf"
    assert file_info["summary"] == "An essay on autopoiesis"

    # 4. Test get_chunks_by_file
    chunks = repo.get_chunks_by_file("conv-123", "Autopoiesis.pdf")
    assert len(chunks) == 2
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["chunk_text"] == "First chunk text"
    assert chunks[1]["chunk_index"] == 1
    assert chunks[1]["chunk_text"] == "Second chunk text"

    print("find_file_by_name and get_chunks_by_file: OK")

    conn.close()
    import time
    time.sleep(0.1)
    for p in [db_path, db_path + "-wal", db_path + "-shm"]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except PermissionError:
            pass
    print("All file lookup tests passed!")

asyncio.run(test_file_by_name())
