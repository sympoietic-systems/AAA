import sys
from pathlib import Path

# Adjust path to import backend
root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import ConversationRepository

db_path = str(get_db_path("data/aaa_test_tags.db"))
conn = init_db(db_path)

try:
    repo = ConversationRepository(db_path)
    
    # 1. Create mock conversations
    c1 = repo.create("user_conv_1", "symbia", "My User Chat")
    c2 = repo.create("dream_conv_2", "symbia", "Dream Log: Flight")
    c3 = repo.create("agent_conv_3", "other_agent", "Consultation: Antigravity")
    
    print("Created mock conversations.")
    
    # 2. Add tags
    repo.add_tag(c1.id, "philosophy", "semantic")
    repo.add_tag(c1.id, "cybernetics", "semantic")
    repo.add_tag(c2.id, "astral", "keyword")
    
    # Verify tags retrieval
    tags_c1 = repo.get_tags(c1.id)
    print("Tags for C1:", tags_c1)
    assert len(tags_c1) == 2
    assert {t["tag"] for t in tags_c1} == {"philosophy", "cybernetics"}
    
    # 3. Check unique tags
    all_tags = repo.get_all_unique_tags()
    print("All Unique Tags:", all_tags)
    assert len(all_tags) == 3
    
    # 4. Filter by tag
    phil_convs = repo.list_all(tag="philosophy")
    print("Convs with philosophy tag:", [c.title for c in phil_convs])
    assert len(phil_convs) == 1
    assert phil_convs[0].id == c1.id
    
    # 5. Remove tag
    repo.remove_tag(c1.id, "philosophy")
    tags_c1_after = repo.get_tags(c1.id)
    print("Tags for C1 after removal:", tags_c1_after)
    assert len(tags_c1_after) == 1
    assert tags_c1_after[0]["tag"] == "cybernetics"
    
    # 6. Test delete conversation cascading
    repo.delete(c1.id)
    tags_c1_deleted = repo.get_tags(c1.id)
    print("Tags for C1 after deletion:", tags_c1_deleted)
    assert len(tags_c1_deleted) == 0
    
    print("\nAll tag repository checks passed successfully!")
    
finally:
    conn.close()
    import os
    if os.path.exists(db_path):
        os.remove(db_path)
