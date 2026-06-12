from pathlib import Path
import sys
import os
import asyncio

root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)
os.chdir(root_path)

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import ErrorLogRepository, MessageRepository, NoteRepository
from backend.modules.context_collector import ContextCollectorModule
from backend.metabolisation.pipeline import ProcessingPipeline
from backend.core.registry import ModuleRegistry


async def test_context_collector():
    db_path = str(get_db_path("data/aaa_ctx_test.db"))
    conn = init_db(db_path)
    conn.execute("DELETE FROM conversation_metrics")
    conn.execute("DELETE FROM conversation_log")
    conn.commit()
    repo = MessageRepository(db_path)
    note_repo = NoteRepository(db_path)

    import numpy as np

    emb = np.zeros(384, dtype="float32").tobytes()

    repo.insert("human", "What is the weather?", emb, "test", 384)
    repo.insert("apparatus", "It is sunny today.", emb, "test", 384)
    repo.insert("human", "Tell me more.", emb, "test", 384)

    mod = ContextCollectorModule(message_repo=repo, note_repo=note_repo, max_history=20)
    assert mod.validate()
    assert mod.name == "context_collector"

    result = await mod.process({"content": "What about tomorrow?", "speaker": "human"})
    messages = result.get("messages", [])

    print(f"Messages collected: {len(messages)}")
    for m in messages:
        print(f"  [{m['role']}] {m['content'][:50]}")

    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    print("Context collector: OK")

    # Directly test process_inline_notes for different tag formats and visibility levels
    from backend.modules.context_collector import process_inline_notes

    test_notes = {
        "note-1": {"id": "note-1", "visibility": "personal", "comment": "my comment", "selected_text": "text 1"},
        "note-2": {"id": "note-2", "visibility": "shared", "comment": "shared comment", "selected_text": "text 2"},
        "note-3": {"id": "note-3", "visibility": "agent", "comment": "agent comment", "selected_text": "text 3"},
    }

    # Case A: Legacy format personal note
    assert process_inline_notes('<mark id="note-1">text 1</mark>', test_notes) == "text 1"
    
    # Case B: Legacy format shared note
    assert process_inline_notes('<mark id="note-2">text 2</mark>', test_notes) == '<note_entanglement note_id="note-2" comment="shared comment">text 2</note_entanglement>'

    # Case C: New format personal note
    assert process_inline_notes('<mark id="note-highlight-note-1" data-note-id="note-1">text 1</mark>', test_notes) == "text 1"

    # Case D: New format shared note
    assert process_inline_notes('<mark id="note-highlight-note-2" data-note-id="note-2">text 2</mark>', test_notes) == '<note_entanglement note_id="note-2" comment="shared comment">text 2</note_entanglement>'

    # Case E: New format agent note
    assert process_inline_notes('<mark id="note-highlight-note-3" data-note-id="note-3">text 3</mark>', test_notes) == '<note_entanglement note_id="note-3" comment="agent comment">text 3</note_entanglement>'

    # Case F: Hallucinated/unknown note format (should strip tags but keep inner text)
    assert process_inline_notes('<mark id="note-highlight-fake" data-note-id="fake">fake text</mark>', test_notes) == "fake text"

    # Case G: Multi-segment inline/block boundary split note formats
    text_g = '<mark id="note-highlight-note-2" data-note-id="note-2">segment 1</mark> normal <mark data-note-id="note-2">segment 2</mark>'
    expected_g = '<note_entanglement note_id="note-2" comment="shared comment">segment 1</note_entanglement> normal <note_entanglement note_id="note-2" comment="shared comment">segment 2</note_entanglement>'
    assert process_inline_notes(text_g, test_notes) == expected_g

    # Case H: Scar fold passthrough
    assert process_inline_notes('<scar-fold>my trace</scar-fold>', test_notes) == '<scar-fold>my trace</scar-fold>'

    print("process_inline_notes filtration assertions: OK")

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

