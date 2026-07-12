import asyncio
import os
import sys
from pathlib import Path

import numpy as np

root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)
os.chdir(root_path)

from backend.modules.conversation_metrics import ConversationMetricsModule  # noqa: E402
from backend.modules.homeostatic_regulator import HomeostaticRegulatorModule  # noqa: E402
from backend.storage.database import get_db_path, init_db  # noqa: E402
from backend.storage.repository import MessageRepository, MetricsRepository  # noqa: E402


async def test_allostatic_metrics():
    db_path = str(get_db_path("data/aaa_allostatic_test.db"))
    conn = init_db(db_path)

    # Clear test DB
    conn.execute("DELETE FROM conversation_metrics")
    conn.execute("DELETE FROM conversation_log")
    conn.commit()

    repo = MessageRepository(db_path)
    metrics_repo = MetricsRepository(db_path)

    metrics_mod = ConversationMetricsModule(message_repo=repo)
    _regulator_mod = HomeostaticRegulatorModule()

    # Step 1: Verify State Isolation
    # Set up conversation A with high coupling and reverse perturbation (so MPI is high)
    conv_a = "conv_a"
    emb = np.zeros(384, dtype="float32")
    emb[0] = 1.0  # direction 1
    emb_bytes = emb.tobytes()

    # Insert user turn, then agent turn in A
    msg_a1 = repo.insert("human", "hello a", emb_bytes, "test", 384, conversation_id=conv_a)
    _metrics_a1 = await metrics_mod.process({"embedding": emb_bytes, "embedding_dim": 384, "conversation_id": conv_a})

    # Store metrics for turn 1 in DB
    metrics_repo.insert(
        message_id=msg_a1.id,
        s_t=1.0,
        novelty=0.0,
        deficit=0.0,
        rolling_entropy=0.0,
        coupling=1.0,
        agent_divergence=0.0,
        reverse_perturbation=1.0,
        surprise_index=0.0,
        mutual_perturbation=1.0,  # High MPI
        vitality=1.0,
        boringness=0.0,
        conceptual_velocity=0.0,
        divergence_resolution_ratio=0.0,
        paskian_health=1.0,
        homeostatic_state="flowing",
    )

    # Now verify that when we process conversation B, the prior metrics do not fetch from conversation A
    conv_b = "conv_b"
    _msg_b1 = repo.insert("human", "hello b", emb_bytes, "test", 384, conversation_id=conv_b)
    result_b1 = await metrics_mod.process({"embedding": emb_bytes, "embedding_dim": 384, "conversation_id": conv_b})

    # Since B has no previous turns, its boringness should not be calculated using the high MPI from A
    # Boringness is (1 - rp_t) * (1 - prev_mpi). Here rp_t is None (no prior agent turn in B), so boringness should be None
    assert result_b1["metrics"]["boringness"] is None, "State leakage occurred from conversation A to conversation B"
    print("State isolation: OK")

    # Step 2: Verify Decaying Weighted Surprise Index
    # We will insert three human turns with different embeddings.
    # U_t = 1 - cos(current, decay_weighted_centroid)
    h_emb1 = np.zeros(384, dtype="float32")
    h_emb1[0] = 1.0
    h_emb2 = np.zeros(384, dtype="float32")
    h_emb2[1] = 1.0
    h_emb3 = np.zeros(384, dtype="float32")
    h_emb3[2] = 1.0  # current turn

    # Insert h_emb1 and h_emb2 as prior human embeddings
    msg_h1 = repo.insert("human", "h1", h_emb1.tobytes(), "test", 384, conversation_id=conv_b)
    repo.insert("human", "h2", h_emb2.tobytes(), "test", 384, conversation_id=conv_b, parent_message_id=msg_h1.id)

    # Compute surprise index manually:
    # prior_human has [h_emb2, h_emb1] (ordered by id DESC)
    # weights: w2 = 1.0, w1 = 0.75
    # centroid = (1.0 * h_emb2 + 0.75 * h_emb1) / 1.75
    # centroid = [0.75/1.75, 1.0/1.75, 0.0] = [0.4286, 0.5714, 0.0]
    # norm(centroid) = sqrt(0.4286^2 + 0.5714^2) = sqrt(0.1837 + 0.3265) = sqrt(0.5102) = 0.7143
    # normalized_centroid = [0.6, 0.8, 0.0]
    # dot(h_emb3, normalized_centroid) = 0.0
    # surprise = 1.0 - 0.0 = 1.0

    # Let's test with h_emb3 and check surprise index is computed correctly
    surprise_res = await metrics_mod.process(
        {"embedding": h_emb3.tobytes(), "embedding_dim": 384, "conversation_id": conv_b}
    )

    assert surprise_res["metrics"]["surprise_index"] is not None
    # Dot product with h_emb3 is 0, so surprise should be 1.0
    assert abs(surprise_res["metrics"]["surprise_index"] - 1.0) < 1e-5
    print("Decaying weighted surprise index: OK")

    # Step 3: Verify Lagged Boringness
    # Let's insert a turn with a known mutual_perturbation, and verify that the next turn's boringness uses it.
    # B_t = (1 - rp_t) * (1 - prev_mpi)
    # Let's mock a prior turn with mutual_perturbation = 0.4 in conv_b
    last_msg = repo.get_recent(1, conversation_id=conv_b)[0]
    msg_b_prev = repo.insert(
        "human", "prev", emb_bytes, "test", 384, conversation_id=conv_b, parent_message_id=last_msg.id
    )
    metrics_repo.insert(
        message_id=msg_b_prev.id,
        s_t=0.5,
        novelty=0.5,
        deficit=0.5,
        rolling_entropy=0.1,
        coupling=0.8,
        agent_divergence=0.2,
        reverse_perturbation=0.5,
        surprise_index=0.3,
        mutual_perturbation=0.4,  # prev_mpi = 0.4
        vitality=0.5,
        boringness=0.5,
        conceptual_velocity=0.1,
        divergence_resolution_ratio=0.1,
        paskian_health=0.5,
        homeostatic_state="flowing",
    )

    # Now run metrics process for a new turn.
    # For the new turn, we have a prior agent response, let's say reverse_perturbation = 0.2
    # Then boringness should be: (1 - 0.2) * (1 - 0.4) = 0.8 * 0.6 = 0.48
    # Insert an agent turn first to have a prior agent embedding
    repo.insert(
        "apparatus", "agent response", emb_bytes, "test", 384, conversation_id=conv_b, parent_message_id=msg_b_prev.id
    )

    # We want reverse_perturbation = 0.2, so current_vec dot agent_last_vec should be 0.8
    # agent_last_vec is emb = [1, 0, 0, ...]
    # Let's make current_vec = [0.8, sqrt(1-0.64), 0, ...] = [0.8, 0.6, 0, ...]
    curr_vec = np.zeros(384, dtype="float32")
    curr_vec[0] = 0.8
    curr_vec[1] = 0.6

    result_b_new = await metrics_mod.process(
        {"embedding": curr_vec.tobytes(), "embedding_dim": 384, "conversation_id": conv_b}
    )

    rp_computed = result_b_new["metrics"]["reverse_perturbation"]
    assert abs(rp_computed - 0.2) < 1e-5  # 1.0 - 0.8 = 0.2

    bore_computed = result_b_new["metrics"]["boringness"]
    assert abs(bore_computed - 0.48) < 1e-5  # (1 - 0.2) * (1 - 0.4) = 0.48
    print("Lagged boringness calculation: OK")

    # Step 4: Verify Allostatic Regimes
    # If any critical flag is triggered, state is disrupted.
    # e.g., low pask_health < 0.15 triggers "pask_health_critical" (which is in critical flags)
    # Let's test a healthy metrics set
    metrics_healthy = {
        "pairwise_similarity": 0.5,
        "conceptual_novelty": 0.5,
        "rolling_entropy": 0.1,
        "agent_self_divergence": 0.5,
        "coupling_coherence": 0.5,
        "reverse_perturbation": 0.5,
        "surprise_index": 0.2,
        "mutual_perturbation": 0.5,
        "conversation_vitality": 0.8,
        "boringness": 0.1,
        "conceptual_velocity": 0.4,
        "divergence_resolution_ratio": 0.15,
        "paskian_health": 0.8,
    }
    from backend.modules.homeostatic_regulator import _diagnose_state

    state, flags = _diagnose_state(metrics_healthy)
    assert state == "flowing", f"Expected flowing state, got {state}"

    # Test compensating/consolidating set
    metrics_compensating = dict(metrics_healthy)
    metrics_compensating["pairwise_similarity"] = 0.8  # triggers elevated_similarity (not in critical)
    state, flags = _diagnose_state(metrics_compensating)
    assert state == "consolidating", f"Expected consolidating state, got {state}"

    # Test critical/disrupted set
    metrics_disrupted = dict(metrics_healthy)
    metrics_disrupted["paskian_health"] = 0.1  # triggers pask_health_critical (critical)
    state, flags = _diagnose_state(metrics_disrupted)
    assert state == "disrupted", f"Expected disrupted state, got {state}"
    print("Allostatic regimes diagnosis: OK")

    # Clean up
    conn.close()
    for p in [db_path, db_path + "-wal", db_path + "-shm"]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except PermissionError:
            pass

    print("All allostatic metrics tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(test_allostatic_metrics())
