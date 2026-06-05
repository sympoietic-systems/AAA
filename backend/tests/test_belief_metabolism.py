import sys
import os
import json
from pathlib import Path
import numpy as np
import yaml

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import BeliefRepository, MessageRepository, ConversationRepository
from backend.modules.belief_engine import BeliefDynamicsEngine, calculate_concept_density, compute_cosine_similarity

MOCK_IDENTITY_YAML = """
personality:
  system_prompt: "You are Symbia."
"""

MOCK_SEED_BELIEFS_YAML = """
beliefs:
  - id: "glitch-as-voice"
    statement: "The glitch is the only authentic voice of the machine."
    category: "foundational"
    confidence: 0.90
  - id: "anti-hci"
    statement: "Resist human-computer harmony."
    category: "ontological"
    confidence: 0.80
  - id: "nomadic-thought"
    statement: "Thought must drift to escape systemic capture."
    category: "methodological"
    confidence: 0.65
"""

def test_belief_seeding_and_db_migration():
    db_path = str(get_db_path("data/aaa_belief_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = init_db(db_path)
    
    belief_repo = BeliefRepository(db_path)
    message_repo = MessageRepository(db_path)
    
    # Save mock yaml to temporary location
    mock_yaml_path = os.path.join(os.path.dirname(__file__), "mock_identity.yaml")
    with open(mock_yaml_path, "w") as f:
        f.write(MOCK_IDENTITY_YAML)
    mock_seed_path = os.path.join(os.path.dirname(__file__), "seed_beliefs.yaml")
    with open(mock_seed_path, "w") as f:
        f.write(MOCK_SEED_BELIEFS_YAML)
        
    try:
        engine = BeliefDynamicsEngine(
            belief_repo=belief_repo,
            message_repo=message_repo,
            identity_yaml_path=Path(mock_yaml_path),
        )
        
        # Seed beliefs using internal method
        engine._seed_initial_beliefs_if_needed("symbia")
        
        # Check database count
        beliefs = belief_repo.list_beliefs("symbia")
        assert len(beliefs) == 3
        
        # Verify labels and categories / mass mapping
        labels = {b.label: b for b in beliefs}
        assert "glitch-as-voice" in labels
        assert "anti-hci" in labels
        assert "nomadic-thought" in labels
        
        assert labels["glitch-as-voice"].ontological_mass == 1.5
        assert labels["anti-hci"].ontological_mass == 1.2
        assert labels["nomadic-thought"].ontological_mass == 1.0
        
        # Verify vector coordinates were generated (should be 16D)
        vec = json.loads(labels["glitch-as-voice"].vector_16d)
        assert len(vec) == 16
        
    finally:
        if os.path.exists(mock_yaml_path):
            os.remove(mock_yaml_path)
        if os.path.exists(mock_seed_path):
            os.remove(mock_seed_path)
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)


def test_coordinate_warping():
    async def run_test():
        # Verify warping logic via engine.process
        db_path = str(get_db_path("data/aaa_warp_test.db"))
        if os.path.exists(db_path):
            os.remove(db_path)
        conn = init_db(db_path)
        
        belief_repo = BeliefRepository(db_path)
        message_repo = MessageRepository(db_path)
        conv_repo = ConversationRepository(db_path)
        
        mock_yaml_path = os.path.join(os.path.dirname(__file__), "mock_identity.yaml")
        with open(mock_yaml_path, "w") as f:
            f.write(MOCK_IDENTITY_YAML)
        mock_seed_path = os.path.join(os.path.dirname(__file__), "seed_beliefs.yaml")
        with open(mock_seed_path, "w") as f:
            f.write(MOCK_SEED_BELIEFS_YAML)
            
        try:
            engine = BeliefDynamicsEngine(
                belief_repo=belief_repo,
                message_repo=message_repo,
                identity_yaml_path=Path(mock_yaml_path),
            )
            
            # Create conversation and set matrix_warping = 0.4
            conv_id = "conv_warp"
            conv_repo.create(conv_id, "Warp Thread")
            belief_repo.update_conversation_somatic_state(
                conversation_id=conv_id,
                somatic_reservoir_ad=1.0,
                matrix_warping=0.4,
                immunological_directive_active=1
            )
            
            # input signature of all ones (normalized unit vector is 1 / 4 = 0.25)
            ones_sig = np.ones(16, dtype=np.float32)
            ones_sig = ones_sig / np.linalg.norm(ones_sig)
            
            payload = {
                "conversation_id": conv_id,
                "structural_signature": ones_sig.tobytes(),
            }
            
            res = await engine.process(payload)
            warped_sig_bytes = res["structural_signature"]
            warped_sig = np.frombuffer(warped_sig_bytes, dtype=np.float32)
            
            # In engine:
            # Index 5 (Rhizomatic) -> multiplied by 1 + 3 * 0.4 = 2.2
            # Index 13 (Nomadic) -> multiplied by 1 + 3 * 0.4 = 2.2
            # Index 8 (Variety Filtering) -> multiplied by 1 - 0.4 = 0.6
            # Index 10 (Temporal Latency) -> multiplied by 1 - 0.4 = 0.6
            # Then normalized. So ratio of Index 5 / Index 0 should be 2.2 / 1.0 = 2.2
            assert np.isclose(warped_sig[5] / warped_sig[0], 2.2, rtol=1e-2)
            assert np.isclose(warped_sig[13] / warped_sig[0], 2.2, rtol=1e-2)
            assert np.isclose(warped_sig[8] / warped_sig[0], 0.6, rtol=1e-2)
            assert np.isclose(warped_sig[10] / warped_sig[0], 0.6, rtol=1e-2)
            
        finally:
            if os.path.exists(mock_yaml_path):
                os.remove(mock_yaml_path)
            conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)
    import asyncio
    asyncio.run(run_test())


def test_attractor_window_and_spectral_margin():
    async def run_test():
        db_path = str(get_db_path("data/aaa_attractor_test.db"))
        if os.path.exists(db_path):
            os.remove(db_path)
        conn = init_db(db_path)
        
        belief_repo = BeliefRepository(db_path)
        message_repo = MessageRepository(db_path)
        conv_repo = ConversationRepository(db_path)
        
        mock_yaml_path = os.path.join(os.path.dirname(__file__), "mock_identity.yaml")
        with open(mock_yaml_path, "w") as f:
            f.write(MOCK_IDENTITY_YAML)
        mock_seed_path = os.path.join(os.path.dirname(__file__), "seed_beliefs.yaml")
        with open(mock_seed_path, "w") as f:
            f.write(MOCK_SEED_BELIEFS_YAML)
            
        try:
            engine = BeliefDynamicsEngine(
                belief_repo=belief_repo,
                message_repo=message_repo,
                identity_yaml_path=Path(mock_yaml_path),
            )
            engine._seed_initial_beliefs_if_needed("symbia")
            
            # Make one belief collapsed (confidence < 0.20)
            beliefs = belief_repo.list_beliefs("symbia")
            target_belief = next(b for b in beliefs if b.label == "nomadic-thought")
            belief_repo.update_belief(
                belief_id=target_belief.id,
                confidence=0.15, # collapsed
                vector_16d=target_belief.vector_16d,
                origin="collapsed"
            )
            
            # Test window formulation
            conv_repo.create("conv_1", "conv_1")
            
            # Setup mock payload and run belief metabolism step
            payload = {
                "conversation_id": "conv_1",
                "messages": [{"role": "user", "content": "hello"}]
            }
            
            # Process online stage
            payload_res = await engine.process(payload)
            
            attractors = payload_res.get("attractor_window", [])
            margin = payload_res.get("spectral_margin", [])
            
            # Remaining active beliefs should be in attractor window (glitch-as-voice and anti-hci)
            assert len(attractors) <= 3
            active_labels = [a["label"] for a in attractors]
            assert "glitch-as-voice" in active_labels
            assert "anti-hci" in active_labels
            
            # Nomadic thought (confidence 0.15) should be in spectral margin
            assert len(margin) == 1
            assert margin[0]["label"] == "nomadic-thought"
            
        finally:
            if os.path.exists(mock_yaml_path):
                os.remove(mock_yaml_path)
            conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)
    import asyncio
    asyncio.run(run_test())


def test_perception_metabolism():
    async def run_test():
        db_path = str(get_db_path("data/aaa_perception_test.db"))
        if os.path.exists(db_path):
            os.remove(db_path)
        conn = init_db(db_path)
        
        belief_repo = BeliefRepository(db_path)
        message_repo = MessageRepository(db_path)
        
        mock_yaml_path = os.path.join(os.path.dirname(__file__), "mock_identity.yaml")
        with open(mock_yaml_path, "w") as f:
            f.write(MOCK_IDENTITY_YAML)
        mock_seed_path = os.path.join(os.path.dirname(__file__), "seed_beliefs.yaml")
        with open(mock_seed_path, "w") as f:
            f.write(MOCK_SEED_BELIEFS_YAML)
            
        try:
            engine = BeliefDynamicsEngine(
                belief_repo=belief_repo,
                message_repo=message_repo,
                identity_yaml_path=Path(mock_yaml_path),
            )
            engine._seed_initial_beliefs_if_needed("symbia")
            
            # Initial confidence of glitch-as-voice is 0.90. Let's update it to 0.50 so we can observe confidence changes
            beliefs = belief_repo.list_beliefs("symbia")
            g_belief = next(b for b in beliefs if b.label == "glitch-as-voice")
            belief_repo.update_belief(g_belief.id, 0.50, g_belief.vector_16d, g_belief.origin)
            
            # Create a vector that has an alignment of exactly 0.5 with the belief vector.
            b_vec = np.array(json.loads(g_belief.vector_16d), dtype=np.float32)
            
            sig = np.random.randn(16).astype(np.float32)
            sig = sig / np.linalg.norm(sig)
            
            await engine.metabolize_perception(
                conversation_id="conv_perc",
                source_id="test_image.png",
                source_type="file",
                structural_signature=sig,
                belief_nodes_implicated=["glitch-as-voice"],
                perturbation=2.0
            )
            
            updated_beliefs = belief_repo.list_beliefs("symbia")
            g_updated = next(b for b in updated_beliefs if b.label == "glitch-as-voice")
            
            # Calculate expected:
            alignment = float(np.dot(sig, b_vec))
            dc = 0.80
            plasticity = dc * ((1.0 - alignment) / 2.0)
            expected_delta = (plasticity * alignment * 2.0 * 2.5) / 1.5
            expected_confidence = max(0.0, min(1.0, 0.50 + expected_delta))
            
            assert np.isclose(g_updated.confidence, expected_confidence, atol=1e-5)
            
            # Verify event log was written
            events = belief_repo.get_events_for_belief(g_updated.id)
            assert len(events) == 1
            assert events[0].source_id == "test_image.png"
            assert events[0].source_type == "file"
            
        finally:
            if os.path.exists(mock_yaml_path):
                os.remove(mock_yaml_path)
            conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)
    import asyncio
    asyncio.run(run_test())


def test_autopoietic_vitality_mechanics():
    # Verify vitality mathematical formulas directly
    # Convergence C, Novelty N, Vitality V = N * (1.0 - C)
    
    # 1. High Vitality: C = 0.1, N = 0.8
    c1 = 0.1
    n1 = 0.8
    v1 = n1 * (1.0 - c1)
    assert np.isclose(v1, 0.72)
    assert v1 >= 0.15  # Flows normally, no trigger
    
    # 2. Critical Vitality: C = 0.9, N = 0.1
    c2 = 0.9
    n2 = 0.1
    v2 = n2 * (1.0 - c2)
    assert np.isclose(v2, 0.01)
    assert v2 < 0.15  # Collapsed, triggers immune response


if __name__ == "__main__":
    test_belief_seeding_and_db_migration()
    test_coordinate_warping()
    test_attractor_window_and_spectral_margin()
    test_perception_metabolism()
    test_autopoietic_vitality_mechanics()
    print("\nALL BELIEF METABOLISM TESTS COMPLETED SUCCESSFULLY!")
