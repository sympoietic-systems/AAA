import os
import sys

import numpy as np

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.database import init_db
from backend.storage.repository import (
    ConsolidationCheckpointRepository,
    ConversationRepository,
    MemoryNodeRepository,
    MessageRepository,
)


def test_conversation_branching_and_dag(tmp_path):
    # Set up temporary sqlite DB
    db_file = tmp_path / "test_branching.db"

    # Initialize DB
    conn = init_db(str(db_file))
    conn.close()

    conv_repo = ConversationRepository(str(db_file))
    msg_repo = MessageRepository(str(db_file))
    _link_repo = MessageRepository(str(db_file))  # Methods are in MessageRepository
    checkpoint_repo = ConsolidationCheckpointRepository(str(db_file))
    memory_node_repo = MemoryNodeRepository(str(db_file))

    # 1. Setup conversation
    conv_id = "branch_conv_test"
    conv_repo.create(conversation_id=conv_id, agent_id="symbia", title="Rhizome Test")

    # Dummy embedding
    emb = np.zeros(384, dtype="float32").tobytes()

    # 2. Insert linear path: Msg 1 -> Msg 2 -> Msg 3
    msg1 = msg_repo.insert(
        speaker="human",
        content="Root Msg 1",
        embedding=emb,
        embedding_model="test",
        embedding_dim=384,
        conversation_id=conv_id,
    )
    assert msg1.id is not None
    assert msg1.parent_message_id is None

    msg2 = msg_repo.insert(
        speaker="apparatus",
        content="Agent Msg 2",
        embedding=emb,
        embedding_model="test",
        embedding_dim=384,
        conversation_id=conv_id,
        parent_message_id=msg1.id,
    )
    assert msg2.parent_message_id == msg1.id

    msg3 = msg_repo.insert(
        speaker="human",
        content="Human Msg 3",
        embedding=emb,
        embedding_model="test",
        embedding_dim=384,
        conversation_id=conv_id,
        parent_message_id=msg2.id,
    )
    assert msg3.parent_message_id == msg2.id

    # 3. Insert branch from Msg 2: Msg 2 -> Msg 4b (branch)
    msg4b = msg_repo.insert(
        speaker="human",
        content="Branched Msg 4b",
        embedding=emb,
        embedding_model="test",
        embedding_dim=384,
        conversation_id=conv_id,
        parent_message_id=msg2.id,
    )
    assert msg4b.parent_message_id == msg2.id

    # 4. Check get_ancestor_path for main line (msg3)
    path_main = msg_repo.get_ancestor_path(msg3.id)
    assert len(path_main) == 3
    assert path_main[0].id == msg1.id
    assert path_main[1].id == msg2.id
    assert path_main[2].id == msg3.id

    # Check get_ancestor_path for branched line (msg4b)
    path_branch = msg_repo.get_ancestor_path(msg4b.id)
    assert len(path_branch) == 3
    assert path_branch[0].id == msg1.id
    assert path_branch[1].id == msg2.id
    assert path_branch[2].id == msg4b.id

    # 5. Check retroactive/DAG links
    # Link msg4b back to msg3 to represent a cross-timeline resonance link
    link = msg_repo.add_message_link(source_id=msg4b.id, target_id=msg3.id, link_type="resonance")
    assert link.source_id == msg4b.id
    assert link.target_id == msg3.id
    assert link.link_type == "resonance"

    # Fetch links for conversation
    links = msg_repo.get_message_links(conv_id)
    assert len(links) == 1
    assert links[0].source_id == msg4b.id
    assert links[0].target_id == msg3.id

    # 6. Check Checkpoints & Versioned Memory Nodes
    # Save checkpoint 1 on Msg 2
    checkpoint1_id = checkpoint_repo.save(
        conversation_id=conv_id,
        message_count=2,
        summary="yaml summary 1",
        model="test",
        message_id=msg2.id,
    )
    assert checkpoint1_id > 0

    # Save memory nodes for checkpoint 1
    nodes1 = [
        {"id": "node_a", "type": "concept", "intensity": 0.8, "intra_active_text": "Node A text"},
        {"id": "node_b", "type": "concept", "intensity": 0.5, "intra_active_text": "Node B text"},
    ]
    memory_node_repo.save_nodes(conv_id, checkpoint1_id, nodes1)

    # Save checkpoint 2 on Msg 3 (main line)
    checkpoint2_id = checkpoint_repo.save(
        conversation_id=conv_id,
        message_count=3,
        summary="yaml summary 2",
        model="test",
        message_id=msg3.id,
    )
    assert checkpoint2_id > 0

    # Save memory nodes for checkpoint 2 (modified/updated node_a, new node_c)
    nodes2 = [
        {"id": "node_a", "type": "concept", "intensity": 0.9, "intra_active_text": "Node A updated text"},
        {"id": "node_c", "type": "concept", "intensity": 0.7, "intra_active_text": "Node C text"},
    ]
    memory_node_repo.save_nodes(conv_id, checkpoint2_id, nodes2)

    # Check get_latest_checkpoint_for_path for main line (msg1, msg2, msg3)
    path_main_ids = [msg1.id, msg2.id, msg3.id]
    cp_main = checkpoint_repo.get_latest_checkpoint_for_path(conv_id, path_main_ids)
    assert cp_main is not None
    assert cp_main["id"] == checkpoint2_id
    assert cp_main["message_id"] == msg3.id

    # Check get_latest_checkpoint_for_path for branched line (msg1, msg2, msg4b)
    path_branch_ids = [msg1.id, msg2.id, msg4b.id]
    cp_branch = checkpoint_repo.get_latest_checkpoint_for_path(conv_id, path_branch_ids)
    assert cp_branch is not None
    assert cp_branch["id"] == checkpoint1_id  # Should resolve checkpoint1 because msg3 is not in branch path!
    assert cp_branch["message_id"] == msg2.id

    # Verify nodes for each checkpoint
    nodes_cp1 = memory_node_repo.get_nodes_by_checkpoint(checkpoint1_id)
    assert len(nodes_cp1) == 2
    assert any(n["id"] == "node_a" and n["intensity"] == 0.8 for n in nodes_cp1)
    assert any(n["id"] == "node_b" for n in nodes_cp1)

    nodes_cp2 = memory_node_repo.get_nodes_by_checkpoint(checkpoint2_id)
    assert len(nodes_cp2) == 2
    assert any(n["id"] == "node_a" and n["intensity"] == 0.9 for n in nodes_cp2)
    assert any(n["id"] == "node_c" for n in nodes_cp2)

    # Test delete_by_checkpoint
    memory_node_repo.delete_by_checkpoint(checkpoint1_id)
    assert len(memory_node_repo.get_nodes_by_checkpoint(checkpoint1_id)) == 0
    # Checkpoint 2 nodes should still be intact
    assert len(memory_node_repo.get_nodes_by_checkpoint(checkpoint2_id)) == 2
