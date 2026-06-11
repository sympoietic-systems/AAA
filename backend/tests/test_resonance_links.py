import os
import sys
import numpy as np
import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path

# Ensure parent directory is in path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.storage.database import init_db
from backend.storage.repository import (
    MessageRepository,
    ConversationRepository,
)
from backend.storage.models import Message, MessageLink
from backend.api.schemas import TreeLink, SpectralSuggestion

@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_resonance_links_db_and_repo(tmp_path):
    # 1. Setup temporary sqlite DB and run migrations
    db_file = tmp_path / "test_resonance.db"
    conn = init_db(str(db_file))
    conn.close()
    
    msg_repo = MessageRepository(str(db_file))
    conv_repo = ConversationRepository(str(db_file))
    
    conv_id = "test_resonance_conv"
    conv_repo.create(conversation_id=conv_id, agent_id="symbia", title="Resonance Test")
    
    # 2. Insert messages with embeddings
    # We create a main line and a parallel branch
    emb1 = np.array([1.0, 0.0, 0.0], dtype="float32").tobytes()
    emb2 = np.array([0.9, 0.1, 0.0], dtype="float32").tobytes()  # High similarity to msg1
    emb3 = np.array([0.0, 0.0, 1.0], dtype="float32").tobytes()  # Low similarity to msg1
    
    msg1 = msg_repo.insert(
        speaker="human",
        content="Concept of intra-active cut.",
        embedding=emb1,
        embedding_model="test",
        embedding_dim=3,
        conversation_id=conv_id,
    )
    
    msg2 = msg_repo.insert(
        speaker="apparatus",
        content="The cut produces agencies.",
        embedding=emb3,
        embedding_model="test",
        embedding_dim=3,
        conversation_id=conv_id,
        parent_message_id=msg1.id,
    )
    
    # Message on a parallel branch
    msg3 = msg_repo.insert(
        speaker="human",
        content="Diffraction and intra-action in Karen Barad's work.",
        embedding=emb2,
        embedding_model="test",
        embedding_dim=3,
        conversation_id=conv_id,
        parent_message_id=msg1.id,
    )
    
    # 3. Test adding proposed resonance link
    link = msg_repo.add_message_link(
        source_id=msg3.id,
        target_id=msg1.id,
        link_type="resonance",
        status="proposed",
        justification="Both discuss Baradian intra-action.",
    )
    
    assert link.source_id == msg3.id
    assert link.target_id == msg1.id
    assert link.status == "proposed"
    assert link.justification == "Both discuss Baradian intra-action."
    
    # 4. Test fetch links
    links = msg_repo.get_message_links(conv_id)
    assert len(links) == 1
    assert links[0].id == f"{min(msg3.id, msg1.id)}_{max(msg3.id, msg1.id)}_resonance"
    assert links[0].status == "proposed"
    assert links[0].justification == "Both discuss Baradian intra-action."
    
    # 5. Test confirm resonance link
    msg_repo.confirm_message_link(link.id)
    links_updated = msg_repo.get_message_links(conv_id)
    assert links_updated[0].status == "active"
    
    # 6. Test delete/dismiss resonance link
    msg_repo.delete_message_link(link.id)
    links_empty = msg_repo.get_message_links(conv_id)
    assert len(links_empty) == 0
    
    # 7. Test get_parallel_messages_by_similarity
    # Ancestor path of msg3 is [msg1, msg3]. So the parallel node is msg2 (though low similarity)
    # Let's test with threshold 0.0 to verify it retrieves msg2
    suggestions = msg_repo.get_parallel_messages_by_similarity(
        conversation_id=conv_id,
        message_id=msg3.id,
        ancestor_ids=[msg1.id, msg3.id],
        threshold=0.0,
        limit=5,
    )
    assert len(suggestions) == 1
    assert suggestions[0]["message_id"] == msg2.id


@pytest.mark.anyio
async def test_resonance_api_integration():
    from backend.storage.connection import with_connection

    @with_connection
    def get_max_id(repo_instance):
        conn = repo_instance._conn()
        row = conn.execute("SELECT MAX(id) FROM conversation_log").fetchone()
        return row[0] if row[0] is not None else 0

    async def mock_generate(*args, **kwargs):
        from backend.main import app
        repo = app.state.message_repo
        current_max = get_max_id(repo)
        next_user_msg_id = current_max + 1
        
        return {
            "content": f"This is a response to diffraction.\n<resonance target=\"{next_user_msg_id}\">Symbia detected an echo with our initial cut.</resonance>",
            "thinking": "Synthesizing diffraction...",
            "model": "mock-model",
            "provider_used": "mock-provider",
        }
    
    with patch(
        "backend.modules.llm_client.OpenAICompatibleProvider.generate",
        new=mock_generate,
    ), patch(
        "backend.services.chat.run_background_resonance_scan",
        new=AsyncMock()  # Avoid running the actual background similarity task in API test
    ):
        from backend.main import app
        from fastapi.testclient import TestClient
        
        with TestClient(app) as client:
            # 1. Post a chat message
            req = {
                "content": "Let us talk about Karen Barad.",
                "speaker": "human"
            }
            res = client.post("/api/chat", json=req)
            assert res.status_code == 200
            data = res.json()
            conv_id = data["conversation_id"]
            user_msg_id = data["user_message_id"]
            agent_msg_id = data["id"]
            
            # Verify tag is stripped from content
            assert "<resonance" not in data["content"]
            assert "This is a response to diffraction." in data["content"]
            
            # Since target was "1", a link should have been created (if user_msg_id is 1)
            # Let's verify tree endpoint returns the links
            tree_res = client.get(f"/api/conversations/{conv_id}/tree")
            assert tree_res.status_code == 200
            tree_data = tree_res.json()
            
            # Verify link was saved as proposed
            assert "links" in tree_data
            proposed_links = [l for l in tree_data["links"] if l["status"] == "proposed"]
            assert len(proposed_links) >= 1
            link_id = proposed_links[0]["id"]
            
            # 2. Confirm the proposed link
            conf_res = client.post(f"/api/conversations/{conv_id}/links/{link_id}/confirm")
            assert conf_res.status_code == 200
            assert conf_res.json() == {"status": "success"}
            
            # Verify it is now active
            tree_res = client.get(f"/api/conversations/{conv_id}/tree")
            tree_data = tree_res.json()
            active_links = [l for l in tree_data["links"] if l["id"] == link_id]
            assert active_links[0]["status"] == "active"
            
            # 3. Create a manual link (Tier 3)
            manual_req = {
                "source_id": agent_msg_id,
                "target_id": user_msg_id,
                "link_type": "resonance",
                "status": "active",
                "justification": "Manual link from user."
            }
            manual_res = client.post(f"/api/conversations/{conv_id}/links", json=manual_req)
            assert manual_res.status_code == 200
            manual_data = manual_res.json()
            assert manual_data["status"] == "active"
            assert manual_data["justification"] == "Manual link from user."
            
            # 4. Get spectral suggestions
            sug_res = client.get(f"/api/conversations/{conv_id}/messages/{agent_msg_id}/spectral-suggestions?threshold=0.0")
            assert sug_res.status_code == 200
            assert isinstance(sug_res.json(), list)
            
            # 5. Dismiss/delete the link
            del_res = client.delete(f"/api/conversations/{conv_id}/links/{link_id}")
            assert del_res.status_code == 200
            
            tree_res = client.get(f"/api/conversations/{conv_id}/tree")
            tree_data = tree_res.json()
            assert not any(l["id"] == link_id for l in tree_data["links"])
