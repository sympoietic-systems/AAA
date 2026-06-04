import sys
import sqlite3
from pathlib import Path

# Adjust path to import backend
root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)

from backend.config import load_config
from backend.storage.database import get_db_path
from backend.storage.repository import ConversationRepository

def migrate():
    # 1. Load config
    config = load_config()
    db_path_str = config.get("database", {}).get("path", "data/aaa.db")
    db_path = get_db_path(db_path_str)
    
    print(f"Connecting to database: {db_path}")
    if not db_path.exists():
        print(f"Error: Database file does not exist at {db_path}")
        return
        
    repo = ConversationRepository(str(db_path))
    convs = repo.list_all()
    
    print(f"Found {len(convs)} conversation(s) to process.")
    
    # Connect directly to perform bulk updates
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    try:
        for c in convs:
            title = c.title or ""
            agent_id = c.agent_id or ""
            
            # Determine structural tag
            if "Dream Log" in title or "Internal Diary" in title or "dream" in title.lower():
                structural_tag = "dreams"
            elif title.startswith("Consultation:") or (agent_id and agent_id != "symbia"):
                structural_tag = "other agents"
            else:
                structural_tag = "user conversation"
                
            # Add structural tag
            print(f"Conversation '{title}' (ID: {c.id}) -> Structural Tag: '{structural_tag}'")
            
            # Remove any wrong structural tags
            conn.execute(
                "DELETE FROM conversation_tags WHERE conversation_id = ? AND tag_type = 'structural'",
                (c.id,)
            )
            # Insert the correct structural tag
            conn.execute(
                "INSERT OR IGNORE INTO conversation_tags (conversation_id, tag, tag_type) VALUES (?, ?, ?)",
                (c.id, structural_tag, "structural")
            )
            
            # Mark for consolidation and bypass the 24 hour cooldown check
            # by setting last_consolidated_at to a time in the past (e.g. 2 days ago)
            conn.execute(
                """UPDATE conversations 
                   SET requires_consolidation = 1,
                       last_consolidated_at = datetime('now', '-2 days')
                   WHERE id = ?""",
                (c.id,)
            )
            
        conn.commit()
        print("\nMigration completed successfully!")
        print("All existing conversations have been updated with category tags and marked for consolidation & tag generation.")
        print("The Autopoietic Dream Daemon will process them during its next active cycle.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
