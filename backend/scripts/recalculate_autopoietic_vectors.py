import asyncio
import json
import os
import sqlite3
import sys

# Adjust path to find backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.config import load_config
from backend.main import _init_providers
from backend.modules.structural_engine import CompositeStructuralScorer
from backend.storage.database import get_db_path


async def main():
    config = load_config()
    db_path = str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))
    print(f"Opening database: {db_path}")
    if not os.path.exists(db_path):
        print("Database file does not exist!")
        return

    # Initialize LLM structural provider
    _, structural_provider, _ = _init_providers(config)
    if not structural_provider:
        print("Warning: Structural LLM provider not configured. Fallback empirical modes will be used.")

    scorer = CompositeStructuralScorer(llm_provider=structural_provider, config=config)
    print(f"LLM Scorer status: Enabled={scorer.llm_scorer_enabled}, HasProvider={bool(structural_provider)}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 1. Update Skills
    skills = conn.execute("SELECT id, name, content, description, vector_16d FROM skill_nodes").fetchall()
    print(f"Found {len(skills)} skills to recalculate.")
    updated_skills = 0
    for s in skills:
        skill_id = s["id"]
        name = s["name"]
        content = s["content"] or s["description"] or ""

        existing_v384d = []
        if s["vector_16d"]:
            try:
                data = json.loads(s["vector_16d"])
                if isinstance(data, dict):
                    existing_v384d = data.get("v384d", [])
            except Exception:
                pass

        print(f"Recalculating 16D vector for skill '{name}'...")
        try:
            v16d = await scorer.score_async(content, use_llm_scorer=True)
            result = {"v16d": v16d.tolist() if hasattr(v16d, "tolist") else list(v16d), "v384d": existing_v384d}
            conn.execute("UPDATE skill_nodes SET vector_16d = ? WHERE id = ?", (json.dumps(result), skill_id))
            updated_skills += 1
            print(f"  -> Successfully updated skill '{name}'")
        except Exception as e:
            print(f"  -> Failed to score skill '{name}': {e}")

    # 2. Update Beliefs
    beliefs = conn.execute("SELECT id, label, statement, vector_16d FROM belief_nodes").fetchall()
    print(f"Found {len(beliefs)} beliefs to recalculate.")
    updated_beliefs = 0
    for b in beliefs:
        belief_id = b["id"]
        label = b["label"]
        statement = b["statement"] or ""

        print(f"Recalculating 16D vector for belief '{label}'...")
        try:
            v16d = await scorer.score_async(statement, use_llm_scorer=True)
            v16d_list = v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)
            conn.execute("UPDATE belief_nodes SET vector_16d = ? WHERE id = ?", (json.dumps(v16d_list), belief_id))
            updated_beliefs += 1
            print(f"  -> Successfully updated belief '{label}'")
        except Exception as e:
            print(f"  -> Failed to score belief '{label}': {e}")

    conn.commit()
    conn.close()
    print(f"\nRecalculation complete. Updated {updated_skills} skills and {updated_beliefs} beliefs.")


if __name__ == "__main__":
    asyncio.run(main())
