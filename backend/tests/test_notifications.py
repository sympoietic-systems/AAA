import os
import sqlite3
import sys
from pathlib import Path

# Adjust path to find backend modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.storage.repositories.notification import NotificationRepository


def run_tests():
    # Setup temporary database
    db_file = "test_aaa_notif.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE notifications (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            snippet TEXT NOT NULL,
            conversation_id TEXT,
            message_id INTEGER,
            parent_message_id INTEGER,
            speaker TEXT,
            source TEXT,
            read INTEGER DEFAULT 0,
            dismissed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

    try:
        repo = NotificationRepository(db_file)

        # Test 1: Create notification
        n = repo.create(type="trace", snippet="Indexing test.txt done.", source="perception:test.txt")
        assert n["id"] is not None
        assert n["type"] == "trace"
        assert n["snippet"] == "Indexing test.txt done."
        assert n["read"] == 0
        assert n["dismissed"] == 0
        print("Test 1 (Create): Passed")

        # Test 2: List active
        active = repo.list_active()
        assert len(active) == 1
        assert active[0]["id"] == n["id"]
        print("Test 2 (List Active): Passed")

        # Test 3: Mark as read
        updated = repo.mark_as_read(n["id"])
        assert updated["read"] == 1
        print("Test 3 (Mark Read): Passed")

        # Test 4: Dismiss
        repo.dismiss(n["id"])
        active = repo.list_active()
        assert len(active) == 0
        print("Test 4 (Dismiss): Passed")

        # Test 5: List all
        all_notifs = repo.list_all(dismissed=True)
        assert len(all_notifs) == 1
        assert all_notifs[0]["id"] == n["id"]
        print("Test 5 (List All): Passed")

        # Test 6: Dismiss by match
        # Create a new active notification with conversation_id and message_id
        n2 = repo.create(type="sediment", snippet="Resonance message", conversation_id="conv-123", message_id=456)
        assert repo.get(n2["id"])["dismissed"] == 0
        repo.dismiss_by_match("conv-123", 456)
        assert repo.get(n2["id"])["dismissed"] == 1
        print("Test 6 (Dismiss by Match): Passed")

        print("All notification repository tests passed successfully!")
    finally:
        if os.path.exists(db_file):
            os.remove(db_file)


if __name__ == "__main__":
    run_tests()
