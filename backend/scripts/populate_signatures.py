import os
import sys
import sqlite3
import numpy as np

# Adjust path to find backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.database import get_db_path
from backend.modules.structural_engine import CompositeStructuralScorer


def populate():
    db_path = str(get_db_path("data/aaa.db"))
    print(f"Opening database: {db_path}")
    if not os.path.exists(db_path):
        print("Database file does not exist!")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Initialize CompositeScorer without LLM to score quickly via lexicon/topology
    scorer = CompositeStructuralScorer(llm_provider=None)

    # 1. Update conversation_log
    rows = conn.execute(
        "SELECT id, content FROM conversation_log WHERE structural_signature IS NULL"
    ).fetchall()
    print(f"Found {len(rows)} messages in conversation_log lacking structural signatures.")
    
    updated_msg = 0
    for r in rows:
        msg_id = r["id"]
        content = r["content"] or ""
        sig = scorer.score(content)
        conn.execute(
            "UPDATE conversation_log SET structural_signature = ? WHERE id = ?",
            (sig.tobytes(), msg_id)
        )
        updated_msg += 1

    # 2. Update perception_sediment
    rows_sed = conn.execute(
        "SELECT id, chunk_text FROM perception_sediment WHERE structural_signature IS NULL"
    ).fetchall()
    print(f"Found {len(rows_sed)} items in perception_sediment lacking structural signatures.")
    
    updated_sed = 0
    for r in rows_sed:
        sed_id = r["id"]
        content = r["chunk_text"] or ""
        sig = scorer.score(content)
        conn.execute(
            "UPDATE perception_sediment SET structural_signature = ? WHERE id = ?",
            (sig.tobytes(), sed_id)
        )
        updated_sed += 1

    conn.commit()
    conn.close()
    print(f"Successfully populated: {updated_msg} messages, {updated_sed} sediments.")


if __name__ == "__main__":
    populate()
