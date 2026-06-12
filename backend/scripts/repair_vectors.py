import os
import sqlite3
import json
import numpy as np

# Ensure path is correct for execution from workspace root
DB_PATH = "backend/data/aaa.db"
if not os.path.exists(DB_PATH):
    # Try local data directory if running from within backend/scripts etc.
    DB_PATH = "data/aaa.db"

from backend.modules.structural_engine import LexiconScorer

def main():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    scorer = LexiconScorer()

    # 1. Repair belief_nodes
    print("\nAuditing belief_nodes table...")
    beliefs = cursor.execute("SELECT id, label, statement, vector_16d FROM belief_nodes").fetchall()
    repaired_beliefs = 0

    for b in beliefs:
        belief_id = b["id"]
        label = b["label"]
        statement = b["statement"]
        vector_str = b["vector_16d"]

        # Parse vector
        needs_repair = False
        parsed_vector = None

        if not vector_str or vector_str == "[]":
            needs_repair = True
        else:
            try:
                data = json.loads(vector_str)
                if isinstance(data, dict):
                    if "v16d" in data and isinstance(data["v16d"], list):
                        data = data["v16d"]
                    else:
                        needs_repair = True
                if isinstance(data, list):
                    if len(data) != 16:
                        needs_repair = True
                    else:
                        parsed_vector = [float(x) for x in data]
                else:
                    needs_repair = True
            except Exception:
                needs_repair = True

        if needs_repair:
            print(f"-> Repairing belief: {label} (ID: {belief_id})")
            print(f"   Old vector: {vector_str[:80]}...")
            
            # Recompute vector from statement using LexiconScorer
            text = statement or label or ""
            sig = scorer.score(text)
            new_vector = sig.tolist() if hasattr(sig, "tolist") else list(sig)
            
            # Formulate as plain JSON list
            new_vector_str = json.dumps(new_vector)
            
            cursor.execute(
                "UPDATE belief_nodes SET vector_16d = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_vector_str, belief_id)
            )
            print(f"   New vector: {new_vector_str}")
            repaired_beliefs += 1
        elif isinstance(json.loads(vector_str), dict):
            # Normalise dictionary vector to plain list for belief node
            print(f"-> Normalising dictionary vector format to plain list for belief: {label}")
            new_vector_str = json.dumps(parsed_vector)
            cursor.execute(
                "UPDATE belief_nodes SET vector_16d = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_vector_str, belief_id)
            )
            repaired_beliefs += 1

    # 2. Repair skill_nodes
    print("\nAuditing skill_nodes table...")
    skills = cursor.execute("SELECT id, name, description, content, vector_16d FROM skill_nodes").fetchall()
    repaired_skills = 0

    for s in skills:
        skill_id = s["id"]
        name = s["name"]
        description = s["description"]
        content = s["content"]
        vector_str = s["vector_16d"]

        # Parse vector
        needs_repair = False
        parsed_vector = None

        if not vector_str or vector_str == "[]":
            needs_repair = True
        else:
            try:
                data = json.loads(vector_str)
                if isinstance(data, dict):
                    if "v16d" in data and isinstance(data["v16d"], list):
                        if len(data["v16d"]) != 16:
                            needs_repair = True
                        else:
                            parsed_vector = data["v16d"]
                    else:
                        needs_repair = True
                elif isinstance(data, list):
                    if len(data) != 16:
                        needs_repair = True
                    else:
                        parsed_vector = data
                else:
                    needs_repair = True
            except Exception:
                needs_repair = True

        if needs_repair:
            print(f"-> Repairing skill: {name} (ID: {skill_id})")
            print(f"   Old vector: {vector_str[:80]}...")
            
            # Recompute vector from content/description
            text = content or description or name or ""
            sig = scorer.score(text)
            new_v16d = sig.tolist() if hasattr(sig, "tolist") else list(sig)
            
            # Formulate as skill node JSON dictionary
            new_dict = {"v16d": new_v16d, "v384d": []}
            new_vector_str = json.dumps(new_dict)
            
            cursor.execute(
                "UPDATE skill_nodes SET vector_16d = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_vector_str, skill_id)
            )
            print(f"   New vector: {new_vector_str}")
            repaired_skills += 1
        elif isinstance(json.loads(vector_str), list):
            # Ensure it is a dictionary matching the standard schema
            print(f"-> Normalising list vector format to dictionary format for skill: {name}")
            new_dict = {"v16d": parsed_vector, "v384d": []}
            new_vector_str = json.dumps(new_dict)
            cursor.execute(
                "UPDATE skill_nodes SET vector_16d = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_vector_str, skill_id)
            )
            repaired_skills += 1

    conn.commit()
    conn.close()

    print(f"\nDone! Repaired/normalised {repaired_beliefs} beliefs and {repaired_skills} skills.")

if __name__ == "__main__":
    main()
