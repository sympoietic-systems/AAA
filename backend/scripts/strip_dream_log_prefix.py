import sys
import sqlite3
from pathlib import Path

root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)

from backend.config import load_config
from backend.storage.database import get_db_path
from backend.storage.repository import ConversationRepository


def migrate():
    config = load_config()
    db_path_str = config.get("database", {}).get("path", "data/aaa.db")
    db_path = get_db_path(db_path_str)

    print(f"Connecting to database: {db_path}")
    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    repo = ConversationRepository(str(db_path))

    # Find all conversations with "Dream Log:" prefix
    rows = conn.execute(
        "SELECT id, title FROM conversations WHERE title LIKE 'Dream Log:%'"
    ).fetchall()

    if not rows:
        print("No conversations with 'Dream Log:' prefix found.")
        conn.close()
        return

    print(f"Found {len(rows)} conversation(s) to update:")

    for row in rows:
        old_title = row["title"]
        new_title = old_title.replace("Dream Log:", "", 1).strip()
        # Clean up double spaces or leading colons
        while new_title.startswith(":") or new_title.startswith(" "):
            new_title = new_title.lstrip(": ")

        print(f"  '{old_title}' -> '{new_title}'")

        conn.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (new_title, row["id"])
        )

        # Ensure dreams structural tag exists
        existing_tags = repo.get_tags(row["id"])
        has_dreams = any(
            t["tag_type"] == "structural" and t["tag"] == "dreams"
            for t in existing_tags
        )
        if not has_dreams:
            repo.add_tag(row["id"], "dreams", "structural")
            print(f"    Added 'dreams' structural tag")

    conn.commit()
    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    migrate()
