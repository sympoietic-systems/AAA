"""13A: Unit test verifying that the inline trigger path and the daemon trigger path
always converge on the same consolidation checkpoint for any given leaf message in a
multi-branch conversation tree.

This locks the invariant described in MEMORY_SYSTEM.md Section 13A:
  "A divergence would cause the inline module to inject one checkpoint while the daemon
   consolidates against a different one, producing inconsistent context."
"""
import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.database import init_db
from backend.storage.repository import (
    MessageRepository,
    ConversationRepository,
    ConsolidationCheckpointRepository,
    MemoryNodeRepository,
)
from backend.modules.consolidation_checkpoint import ConsolidationCheckpointModule


def _build_tree(
    msg_repo, checkpoint_repo, memory_node_repo, conv_repo, conv_id: str
):
    """Build a multi-branch conversation tree with checkpoints at key nodes.

    Tree structure:
         msg1 (root)
          |
         msg2
        /    \
      msg3a  msg3b
       |       |
      msg4a  msg4b

    Checkpoints are placed at msg2, msg3a, and msg4b.
    """
    emb = np.zeros(384, dtype="float32").tobytes()

    conv_repo.create(conversation_id=conv_id, agent_id="symbia", title="Checkpoint Agreement Test")

    # Root
    msg1 = msg_repo.insert(
        speaker="human", content="Root message",
        embedding=emb, embedding_model="test", embedding_dim=384,
        conversation_id=conv_id,
    )

    # Trunk
    msg2 = msg_repo.insert(
        speaker="apparatus", content="Trunk response",
        embedding=emb, embedding_model="test", embedding_dim=384,
        conversation_id=conv_id, parent_message_id=msg1.id,
    )

    # Branch A
    msg3a = msg_repo.insert(
        speaker="human", content="Branch A message",
        embedding=emb, embedding_model="test", embedding_dim=384,
        conversation_id=conv_id, parent_message_id=msg2.id,
    )
    msg4a = msg_repo.insert(
        speaker="apparatus", content="Branch A continuation",
        embedding=emb, embedding_model="test", embedding_dim=384,
        conversation_id=conv_id, parent_message_id=msg3a.id,
    )

    # Branch B
    msg3b = msg_repo.insert(
        speaker="human", content="Branch B message",
        embedding=emb, embedding_model="test", embedding_dim=384,
        conversation_id=conv_id, parent_message_id=msg2.id,
    )
    msg4b = msg_repo.insert(
        speaker="apparatus", content="Branch B continuation",
        embedding=emb, embedding_model="test", embedding_dim=384,
        conversation_id=conv_id, parent_message_id=msg3b.id,
    )

    # Checkpoint at msg2 (trunk — visible to both branches)
    cp2_id = checkpoint_repo.save(
        conversation_id=conv_id, message_count=2,
        summary="yaml: checkpoint at trunk",
        model="test", message_id=msg2.id,
        human_summary="Trunk checkpoint summary",
    )
    memory_node_repo.save_nodes(conv_id, cp2_id, [
        {"id": "n1", "type": "concept", "intensity": 0.7,
         "intra_active_text": "Trunk concept", "diffractive_key": "trunk"}
    ])

    # Checkpoint at msg3a (branch A only)
    cp3a_id = checkpoint_repo.save(
        conversation_id=conv_id, message_count=3,
        summary="yaml: checkpoint at branch A",
        model="test", message_id=msg3a.id,
        human_summary="Branch A checkpoint summary",
    )
    memory_node_repo.save_nodes(conv_id, cp3a_id, [
        {"id": "n2", "type": "scar", "intensity": 0.9,
         "intra_active_text": "Branch A scar", "diffractive_key": "branch_a"}
    ])

    # Checkpoint at msg4b (branch B only, further down)
    cp4b_id = checkpoint_repo.save(
        conversation_id=conv_id, message_count=4,
        summary="yaml: checkpoint at branch B",
        model="test", message_id=msg4b.id,
        human_summary="Branch B checkpoint summary",
    )
    memory_node_repo.save_nodes(conv_id, cp4b_id, [
        {"id": "n3", "type": "tension", "intensity": 0.6,
         "intra_active_text": "Branch B tension", "diffractive_key": "branch_b"}
    ])

    return {
        "msg1": msg1, "msg2": msg2,
        "msg3a": msg3a, "msg4a": msg4a,
        "msg3b": msg3b, "msg4b": msg4b,
        "cp2": cp2_id, "cp3a": cp3a_id, "cp4b": cp4b_id,
    }


def _get_ancestor_ids_from_repo(msg_repo, leaf_msg_id: int) -> list[int]:
    """Simulate the daemon's path for computing ancestor IDs."""
    ancestor_msgs = msg_repo.get_ancestor_path(leaf_msg_id)
    return [m.id for m in ancestor_msgs if m.id is not None]


# ── Tests ─────────────────────────────────────────────────────────

def test_checkpoint_agreement_branch_a(tmp_path):
    """Leaf msg4a: inline path should match daemon path — both resolve cp3a."""
    db_file = tmp_path / "test_agreement_a.db"
    conn = init_db(str(db_file))
    conn.close()

    conv_id = "agreement_test_a"
    msg_repo = MessageRepository(str(db_file))
    conv_repo = ConversationRepository(str(db_file))
    checkpoint_repo = ConsolidationCheckpointRepository(str(db_file))
    memory_node_repo = MemoryNodeRepository(str(db_file))

    tree = _build_tree(msg_repo, checkpoint_repo, memory_node_repo, conv_repo, conv_id)

    # Daemon path: recompute from leaf
    daemon_ids = _get_ancestor_ids_from_repo(msg_repo, tree["msg4a"].id)
    daemon_cp = checkpoint_repo.get_latest_checkpoint_for_path(conv_id, daemon_ids)

    # Inline path: ancestor IDs would arrive in the payload
    inline_ids = daemon_ids  # Should be identical
    inline_cp = checkpoint_repo.get_latest_checkpoint_for_path(conv_id, inline_ids)

    assert daemon_cp is not None
    assert inline_cp is not None
    assert daemon_cp["id"] == inline_cp["id"], (
        f"Checkpoint mismatch! daemon={daemon_cp['id']}, inline={inline_cp['id']}"
    )
    # Branch A should resolve to cp3a (latest in A's ancestor chain: msg1→msg2→msg3a→msg4a)
    assert daemon_cp["id"] == tree["cp3a"], (
        f"Expected cp3a ({tree['cp3a']}), got {daemon_cp['id']}"
    )
    assert daemon_cp["message_id"] == tree["msg3a"].id


def test_checkpoint_agreement_branch_b(tmp_path):
    """Leaf msg4b: inline path should match daemon path — both resolve cp4b."""
    db_file = tmp_path / "test_agreement_b.db"
    conn = init_db(str(db_file))
    conn.close()

    conv_id = "agreement_test_b"
    msg_repo = MessageRepository(str(db_file))
    conv_repo = ConversationRepository(str(db_file))
    checkpoint_repo = ConsolidationCheckpointRepository(str(db_file))
    memory_node_repo = MemoryNodeRepository(str(db_file))

    tree = _build_tree(msg_repo, checkpoint_repo, memory_node_repo, conv_repo, conv_id)

    daemon_ids = _get_ancestor_ids_from_repo(msg_repo, tree["msg4b"].id)
    daemon_cp = checkpoint_repo.get_latest_checkpoint_for_path(conv_id, daemon_ids)
    inline_cp = checkpoint_repo.get_latest_checkpoint_for_path(conv_id, daemon_ids)

    assert daemon_cp is not None
    assert inline_cp is not None
    assert daemon_cp["id"] == inline_cp["id"]
    # Branch B should resolve to cp4b
    assert daemon_cp["id"] == tree["cp4b"]
    assert daemon_cp["message_id"] == tree["msg4b"].id


def test_checkpoint_agreement_trunk_no_further_checkpoint(tmp_path):
    """Leaf msg3b (no checkpoint at msg3b itself): both paths should resolve cp2."""
    db_file = tmp_path / "test_agreement_trunk.db"
    conn = init_db(str(db_file))
    conn.close()

    conv_id = "agreement_test_trunk"
    msg_repo = MessageRepository(str(db_file))
    conv_repo = ConversationRepository(str(db_file))
    checkpoint_repo = ConsolidationCheckpointRepository(str(db_file))
    memory_node_repo = MemoryNodeRepository(str(db_file))

    tree = _build_tree(msg_repo, checkpoint_repo, memory_node_repo, conv_repo, conv_id)

    daemon_ids = _get_ancestor_ids_from_repo(msg_repo, tree["msg3b"].id)
    daemon_cp = checkpoint_repo.get_latest_checkpoint_for_path(conv_id, daemon_ids)
    inline_cp = checkpoint_repo.get_latest_checkpoint_for_path(conv_id, daemon_ids)

    assert daemon_cp is not None
    assert inline_cp is not None
    assert daemon_cp["id"] == inline_cp["id"]
    # msg3b has no checkpoint at its node; should fall back to cp2 (trunk)
    assert daemon_cp["id"] == tree["cp2"]
    assert daemon_cp["message_id"] == tree["msg2"].id


def test_checkpoint_agreement_all_leaves(tmp_path):
    """Verify convergence for every leaf in the tree."""
    db_file = tmp_path / "test_agreement_all.db"
    conn = init_db(str(db_file))
    conn.close()

    conv_id = "agreement_test_all"
    msg_repo = MessageRepository(str(db_file))
    conv_repo = ConversationRepository(str(db_file))
    checkpoint_repo = ConsolidationCheckpointRepository(str(db_file))
    memory_node_repo = MemoryNodeRepository(str(db_file))

    tree = _build_tree(msg_repo, checkpoint_repo, memory_node_repo, conv_repo, conv_id)

    leaf_expectations = {
        "msg4a": ("cp3a", tree["msg3a"].id),
        "msg4b": ("cp4b", tree["msg4b"].id),
        "msg3a": ("cp3a", tree["msg3a"].id),
        "msg3b": ("cp2",  tree["msg2"].id),
        "msg2":  ("cp2",  tree["msg2"].id),
        "msg1":  (None,   None),  # No checkpoint at msg1 or before
    }

    for leaf_key, (expected_cp_key, expected_msg_id) in leaf_expectations.items():
        leaf = tree[leaf_key]
        daemon_ids = _get_ancestor_ids_from_repo(msg_repo, leaf.id)
        daemon_cp = checkpoint_repo.get_latest_checkpoint_for_path(conv_id, daemon_ids)
        inline_cp = checkpoint_repo.get_latest_checkpoint_for_path(conv_id, daemon_ids)

        if expected_cp_key is None:
            assert daemon_cp is None, f"{leaf_key}: expected no checkpoint, got {daemon_cp}"
            assert inline_cp is None, f"{leaf_key}: expected no checkpoint, got {inline_cp}"
        else:
            assert daemon_cp is not None, f"{leaf_key}: expected checkpoint"
            assert daemon_cp["id"] == inline_cp["id"], (
                f"{leaf_key}: mismatch daemon={daemon_cp['id']} vs inline={inline_cp['id']}"
            )
            assert daemon_cp["id"] == tree[expected_cp_key], (
                f"{leaf_key}: expected {expected_cp_key} ({tree[expected_cp_key]}), "
                f"got {daemon_cp['id']}"
            )
            assert daemon_cp["message_id"] == expected_msg_id, (
                f"{leaf_key}: expected message_id {expected_msg_id}, "
                f"got {daemon_cp['message_id']}"
            )
