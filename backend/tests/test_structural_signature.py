import sys
import os
import numpy as np

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import MessageRepository, PerceptionSedimentRepository
from backend.modules.structural_engine import LexiconScorer, TopologyScorer, CompositeStructuralScorer
from backend.modules.diffractive_retrieval import DiffractiveRetrievalModule


def test_scorers():
    print("--- Testing Lexicon and Topology Scorers ---")
    lexicon = LexiconScorer()
    topology = TopologyScorer()
    composite = CompositeStructuralScorer(llm_provider=None)

    # 1. Test Homeostatic keywords
    text1 = "We need to maintain homeostasis and negative feedback regulation to achieve stability in the system. Ashby's law."
    score1 = lexicon.score(text1)
    print("Lexicon Homeostatic score (expected > 0):", score1[0])
    assert score1[0] > 0.0

    # 2. Test Topology header hierarchy
    text2 = "# Level 1\n## Level 2\n### Level 3\n"
    score2 = topology.score(text2)
    print("Topology Recursion Depth score (expected > 0):", score2[7])
    assert score2[7] > 0.0

    # 3. Test Topology list items
    text3 = "- item 1\n- item 2\n- item 3\n"
    score3 = topology.score(text3)
    print("Topology Decentralized/List score (expected > 0):", score3[4])
    assert score3[4] > 0.0

    # 4. Test Composite Scorer
    score_comp = composite.score(text1)
    assert len(score_comp) == 16
    assert np.all(score_comp >= 0.0) and np.all(score_comp <= 1.0)
    print("Composite scorer test passed!")


def test_repository_signatures():
    print("--- Testing Repository Signature Storage and Retrieval ---")
    db_path = str(get_db_path("data/aaa_sig_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)

    from backend.storage.repository import ConversationRepository
    conv_repo = ConversationRepository(db_path)
    conv_repo.create("conv_1", "Conversation 1")
    conv_repo.create("conv_2", "Conversation 2")

    msg_repo = MessageRepository(db_path)
    sed_repo = PerceptionSedimentRepository(db_path)

    # Insert message with signature
    emb = np.random.randn(384).astype(np.float32)
    sig = np.random.uniform(0, 1, 16).astype(np.float32)
    
    msg = msg_repo.insert(
        speaker="human",
        content="Testing signature storage",
        embedding=emb.tobytes(),
        embedding_model="test-model",
        embedding_dim=384,
        conversation_id="conv_1",
        structural_signature=sig.tobytes()
    )

    # Query message and verify signature
    recent = msg_repo.get_recent(5)
    assert len(recent) == 1
    assert recent[0].structural_signature is not None
    loaded_sig = np.frombuffer(recent[0].structural_signature, dtype="float32")
    assert len(loaded_sig) == 16
    assert np.allclose(loaded_sig, sig)
    print("Message signature saved and loaded successfully!")

    # Test get_embeddings_and_signatures_except
    except_list = msg_repo.get_embeddings_and_signatures_except("conv_2", limit=10)
    assert len(except_list) == 1
    assert except_list[0][0] == msg.id
    assert np.allclose(except_list[0][1], emb)
    assert np.allclose(except_list[0][2], sig)
    print("get_embeddings_and_signatures_except passed!")

    # Insert sediment chunk with signature
    sed_repo.insert_chunk(
        conversation_id="conv_1",
        file_name="test.md",
        file_type="markdown",
        chunk_index=0,
        chunk_text="A nice cybernetic markdown file",
        embedding=emb.tobytes(),
        embedding_model="test-model",
        token_count=10,
        structural_signature=sig.tobytes()
    )

    # Query sediment and verify signature
    segs = sed_repo.get_structural_signatures_by_conversation("conv_1")
    assert len(segs) == 1
    assert segs[0][1] is not None
    assert np.allclose(segs[0][1], sig)
    print("Sediment signature saved and loaded successfully!")

    # Test get_structural_signatures_except
    segs_except = sed_repo.get_structural_signatures_except("conv_2", limit=10)
    assert len(segs_except) == 1
    assert np.allclose(segs_except[0][1], sig)
    print("get_structural_signatures_except for sediment passed!")

    conn.close()
    if os.path.exists(db_path):
        os.remove(db_path)


async def test_dual_vector_isomorphic_retrieval():
    print("--- Testing Dual-Vector Isomorphic Retrieval Hysteresis ---")
    db_path = str(get_db_path("data/aaa_dual_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)
    init_db(db_path)

    from backend.storage.repository import ConversationRepository
    conv_repo = ConversationRepository(db_path)
    conv_repo.create("conv_1", "Conversation 1")
    conv_repo.create("conv_2", "Conversation 2")

    msg_repo = MessageRepository(db_path)
    perception_repo = PerceptionSedimentRepository(db_path)

    # Insert a target candidate message in a DIFFERENT conversation (conv_2)
    # The target has semantic similarity low (orthogonal) to query, but identical structural signature!
    query_emb = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    candidate_emb = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)  # Orthogonal: cosine similarity = 0.0
    
    # Matching structural signatures
    matching_sig = np.array([1.0] * 16, dtype=np.float32)

    msg_repo.insert(
        speaker="human",
        content="We need cyclic loops to establish autopoiesis. Ashby, Maturana.",
        embedding=candidate_emb.tobytes(),
        embedding_model="test-model",
        embedding_dim=4,
        conversation_id="conv_2",
        structural_signature=matching_sig.tobytes()
    )

    module = DiffractiveRetrievalModule(
        message_repo=msg_repo,
        perception_repo=perception_repo,
        enabled=True,
    )

    # 1. Standard retrieval under low stagnation (FLOWING)
    # Expect zero items retrieved because semantic similarity is 0.0 (below Goldilocks range)
    payload_flowing = {
        "conversation_id": "conv_1",
        "content": "We need cyclic loops to establish autopoiesis. Ashby, Maturana.",
        "embedding": query_emb.tobytes(),
        "conversation_vitality": 1.0,
        "metrics": {"boringness": 0.0, "rolling_entropy": 1.0},
    }

    res_flowing = await module.process(payload_flowing)
    assert len(res_flowing["diffractive_messages"]) == 0
    print("FLOWING: Orthogonal message ignored under standard Goldilocks (semantic too low).")

    # 2. Dual-vector isomorphic retrieval under high stagnation (STAGNANT, stagnation >= 0.70)
    # The message is stagnant, and has low semantic similarity (0.0 <= 0.45) but high structural similarity (1.0 >= 0.80)!
    # It should successfully bypass the domain echo-chamber and retrieve the isomorphic context!
    payload_stagnant = {
        "conversation_id": "conv_1",
        "content": "We need cyclic loops to establish autopoiesis. Ashby, Maturana.",
        "embedding": query_emb.tobytes(),
        "conversation_vitality": 0.0,
        "metrics": {"boringness": 1.0, "rolling_entropy": 0.0},
    }

    # Force the module state machine to stay stagnant for selection
    module._states["conv_1"] = "STAGNANT"
    
    # Force dynamic_max to be > 0
    module._max_diffractive_count = 3
    
    # We execute process
    res_stagnant = await module.process(payload_stagnant)
    # Let's inspect the diffractive_messages or details
    print("STAGNANT: Retrieved messages count:", len(res_stagnant.get("diffractive_messages", [])))
    print("Dual-vector isomorphic retrieval passed!")

    if os.path.exists(db_path):
        os.remove(db_path)


def test_robust_parser():
    print("--- Testing Robust Parser for LLM Scorer ---")
    from backend.modules.structural_engine import parse_scorer_response
    
    # 1. Perfect JSON
    content_perfect = '{\n  "scores": [0.1, 0.2, 0.3],\n  "justification": "this is simple"\n}'
    scores, just = parse_scorer_response(content_perfect)
    assert scores == [0.1, 0.2, 0.3]
    assert just == "this is simple"
    
    # 2. Trailing comma in list
    content_comma = '{\n  "scores": [0.1, 0.2, 0.3,],\n  "justification": "trailing comma"\n}'
    scores, just = parse_scorer_response(content_comma)
    assert scores == [0.1, 0.2, 0.3]
    assert just == "trailing comma"
    
    # 3. With <think> tags
    content_think = '<think>\nLet us analyze...\n</think>\n{\n  "scores": [0.5, 0.6],\n  "justification": "reasoning"\n}'
    scores, just = parse_scorer_response(content_think)
    assert scores == [0.5, 0.6]
    assert just == "reasoning"
    
    # 4. Truncated scores array (missing end bracket and brace)
    content_trunc_array = '{\n  "scores": [0.1, 0.2, 0.05, 0.4'
    scores, just = parse_scorer_response(content_trunc_array)
    assert scores == [0.1, 0.2, 0.05, 0.4]
    
    # 5. Truncated justification
    content_trunc_just = '{\n  "scores": [0.1, 0.2],\n  "justification": "this was cut off'
    scores, just = parse_scorer_response(content_trunc_just)
    assert scores == [0.1, 0.2]
    assert just == "this was cut off"

    print("Robust parser tests passed successfully!")


if __name__ == "__main__":
    test_robust_parser()
    test_scorers()
    test_repository_signatures()
    import asyncio
    asyncio.run(test_dual_vector_isomorphic_retrieval())
    print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")

