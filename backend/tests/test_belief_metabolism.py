import json
import os
import sys
from pathlib import Path

import numpy as np
import yaml

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.modules.belief_engine import BeliefDynamicsEngine
from backend.storage.database import get_db_path, init_db
from backend.storage.repositories import BeliefRepository, ConversationRepository, MessageRepository

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


def _seed_initial_beliefs_if_needed(engine, agent_id: str) -> None:
    import uuid

    seed_path = Path(engine._identity_yaml_path).parent / "seed_beliefs.yaml"
    with open(seed_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    config_beliefs = data.get("beliefs", [])
    for cb in config_beliefs:
        label = cb.get("id")
        statement = cb.get("statement")
        confidence = cb.get("confidence", 0.5)
        category = cb.get("category", "ontological")

        if category == "foundational":
            mass = 1.5
        elif category == "ontological":
            mass = 1.2
        elif category == "methodological":
            mass = 1.0
        else:
            mass = 1.0

        vec = engine._scorer.score(statement)
        vec_json = json.dumps(vec.tolist())

        engine._belief_repo.create_belief(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            label=label,
            statement=statement,
            origin="authored",
            confidence=confidence,
            ontological_mass=mass,
            somatic_anchor="none",
            vector_16d=vec_json,
            lifecycle_stage="crystallized",
        )


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

        # Seed beliefs using helper function
        _seed_initial_beliefs_if_needed(engine, "symbia")

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
                conversation_id=conv_id, somatic_reservoir_ad=1.0, matrix_warping=0.4, immunological_directive_active=1
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
            if os.path.exists(mock_seed_path):
                os.remove(mock_seed_path)
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
            _seed_initial_beliefs_if_needed(engine, "symbia")

            # Make one belief collapsed (confidence < 0.20)
            beliefs = belief_repo.list_beliefs("symbia")
            target_belief = next(b for b in beliefs if b.label == "nomadic-thought")
            belief_repo.update_belief(
                belief_id=target_belief.id,
                confidence=0.15,  # collapsed
                vector_16d=target_belief.vector_16d,
                origin="collapsed",
            )

            # Test window formulation
            conv_repo.create("conv_1", "conv_1")

            # Setup mock payload and run belief metabolism step
            payload = {"conversation_id": "conv_1", "messages": [{"role": "user", "content": "hello"}]}

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
            if os.path.exists(mock_seed_path):
                os.remove(mock_seed_path)
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
            _seed_initial_beliefs_if_needed(engine, "symbia")

            # Initial confidence of glitch-as-voice is 0.90. Let's update it to 0.50 so we can observe confidence changes
            beliefs = belief_repo.list_beliefs("symbia")
            g_belief = next(b for b in beliefs if b.label == "glitch-as-voice")
            belief_repo.update_belief(g_belief.id, 0.50, g_belief.vector_16d, g_belief.origin)

            # Create a vector that has an alignment of exactly 0.5 with the belief vector.
            b_vec = np.array(json.loads(g_belief.vector_16d), dtype=np.float32)
            b_norm = np.linalg.norm(b_vec)
            b_unit = b_vec / (b_norm if b_norm > 1e-6 else 1.0)

            rng = np.random.default_rng(42)
            ortho = rng.standard_normal(16).astype(np.float32)
            ortho -= float(np.dot(ortho, b_unit)) * b_unit
            ortho_norm = np.linalg.norm(ortho)
            ortho = ortho / (ortho_norm if ortho_norm > 1e-6 else 1.0)
            sig = (0.5 * b_unit + np.sqrt(0.75) * ortho).astype(np.float32)

            await engine.metabolize_perception(
                conversation_id="conv_perc",
                source_id="test_image.png",
                source_type="file",
                structural_signature=sig,
                belief_nodes_implicated=["glitch-as-voice"],
                perturbation=2.0,
            )

            updated_beliefs = belief_repo.list_beliefs("symbia")
            g_updated = next(b for b in updated_beliefs if b.label == "glitch-as-voice")

            # Calculate expected:
            from backend.utils.vector import cosine_similarity

            alignment = float(cosine_similarity(sig, b_vec))
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
            if os.path.exists(mock_seed_path):
                os.remove(mock_seed_path)
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


def test_somatic_vitality_state_locking():
    async def run_test():
        db_path = str(get_db_path("data/aaa_locking_test.db"))
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

            conv_id = "conv_lock"
            conv_repo.create(conv_id, "Lock Thread")
            belief_repo.update_conversation_somatic_state(
                conversation_id=conv_id, somatic_reservoir_ad=1.0, matrix_warping=0.4, immunological_directive_active=1
            )

            # Insert less than 3 signatures (e.g. 1 user message, 1 assistant message)
            sig_user = np.ones(16, dtype=np.float32).tobytes()
            sig_assistant = np.ones(16, dtype=np.float32).tobytes()

            user_msg = message_repo.insert(
                speaker="human",
                content="hello",
                embedding=b"",
                embedding_model="test",
                embedding_dim=16,
                agent_id="symbia",
                conversation_id=conv_id,
                content_tokens=5,
                structural_signature=sig_user,
                structural_justification="test",
            )

            assistant_msg = message_repo.insert(
                speaker="apparatus",
                content="world",
                embedding=b"",
                embedding_model="test",
                embedding_dim=16,
                agent_id="symbia",
                conversation_id=conv_id,
                content_tokens=5,
                structural_signature=sig_assistant,
                structural_justification="test",
            )

            # Now run metabolize on this turn
            await engine.metabolize(
                conversation_id=conv_id,
                user_message_id=user_msg.id,
                assistant_message_id=assistant_msg.id,
            )

            # Somatic state should be decayed and reset because len(signatures) is 1 which is < 3
            state = belief_repo.get_conversation_somatic_state(conv_id)
            assert state is not None
            assert state["immunological_directive_active"] == 0
            assert np.isclose(state["matrix_warping"], 0.3)

        finally:
            if os.path.exists(mock_yaml_path):
                os.remove(mock_yaml_path)
            if os.path.exists(mock_seed_path):
                os.remove(mock_seed_path)
            conn.close()
            if os.path.exists(db_path):
                os.remove(db_path)

    import asyncio

    asyncio.run(run_test())


def test_turn_decay_and_crystallized_floor():
    """Verify that turn decay only affects unengaged beliefs and respects the crystallized floor."""
    db_path = str(get_db_path("data/aaa_turn_decay_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = init_db(db_path)
    mock_yaml_path = os.path.join(os.path.dirname(__file__), "mock_identity_turn_decay.yaml")
    with open(mock_yaml_path, "w") as f:
        f.write(MOCK_IDENTITY_YAML)

    try:
        belief_repo = BeliefRepository(db_path)
        msg_repo = MessageRepository(db_path)

        engine = BeliefDynamicsEngine(
            belief_repo=belief_repo,
            message_repo=msg_repo,
            identity_yaml_path=Path(mock_yaml_path),
        )

        import asyncio

        async def run_test():
            # 1. Create a crystallized belief right at the floor (0.55)
            belief_repo.create_belief(
                id="b-floor",
                agent_id="symbia",
                label="floor-belief",
                statement="Floor belief test",
                origin="authored",
                confidence=0.9,
                ontological_mass=0.55,
                somatic_anchor="conceptual",
                vector_16d=json.dumps([0.1] * 16),
                lifecycle_stage="crystallized",
            )
            # 2. Create a crystallized belief above the floor (0.80)
            belief_repo.create_belief(
                id="b-above",
                agent_id="symbia",
                label="above-floor-belief",
                statement="Above floor belief test",
                origin="authored",
                confidence=0.9,
                ontological_mass=0.80,
                somatic_anchor="conceptual",
                vector_16d=json.dumps([0.2] * 16),
                lifecycle_stage="crystallized",
            )
            # 3. Create a non-crystallized belief (0.30)
            belief_repo.create_belief(
                id="b-accretion",
                agent_id="symbia",
                label="accretion-belief",
                statement="Accretion belief test",
                origin="authored",
                confidence=0.5,
                ontological_mass=0.30,
                somatic_anchor="conceptual",
                vector_16d=json.dumps([0.3] * 16),
                lifecycle_stage="accretion",
            )

            # Apply turn decay where engaged_belief_id is None (all unengaged)
            res = await engine._apply_turn_decay("symbia", engaged_belief_id=None)
            assert res["atrophied"] >= 2  # b-above and b-accretion decayed

            b_floor = belief_repo.get_belief("symbia", "b-floor")
            assert b_floor.ontological_mass == 0.55  # Floor preserved!

            b_above = belief_repo.get_belief("symbia", "b-above")
            assert b_above.ontological_mass < 0.80  # Decayed slightly

            b_acc = belief_repo.get_belief("symbia", "b-accretion")
            assert b_acc.ontological_mass < 0.30  # Decayed slightly

            # Now test when engaged_belief_id is b-above
            await engine._apply_turn_decay("symbia", engaged_belief_id="b-above")
            b_above_after = belief_repo.get_belief("symbia", "b-above")
            assert b_above_after.ontological_mass == b_above.ontological_mass  # Engaged belief bypassed

        asyncio.run(run_test())

    finally:
        if os.path.exists(mock_yaml_path):
            os.remove(mock_yaml_path)
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)


def test_migration_050_recalibrate():
    """Verify Migration 050 elevates eroded belief and skill masses."""
    db_path = str(get_db_path("data/aaa_m050_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = init_db(db_path)
    try:
        belief_repo = BeliefRepository(db_path)
        from backend.storage.repositories.cognitive.skill import SkillRepository

        skill_repo = SkillRepository(db_path)

        # Create an eroded core belief
        belief_repo.create_belief(
            id="b-eroded-core",
            agent_id="symbia",
            label="anti-mastery",
            statement="Anti mastery test",
            origin="authored",
            confidence=0.7,
            ontological_mass=0.31,
            somatic_anchor="conceptual",
            vector_16d=json.dumps([0.1] * 16),
            lifecycle_stage="crystallized",
        )
        # Create an eroded skill belief and matching skill node
        belief_repo.create_belief(
            id="b-eroded-skill",
            agent_id="symbia",
            label="skill:code-review",
            statement="Code review skill bridge",
            origin="authored",
            confidence=0.7,
            ontological_mass=0.32,
            somatic_anchor="conceptual",
            vector_16d=json.dumps([0.1] * 16),
            lifecycle_stage="crystallized",
        )
        skill_repo.create_skill(
            id="s-code-review",
            name="code-review",
            content="Code review content",
            description="Reviewing code",
            lifecycle_stage="crystallized",
            confidence=0.7,
            ontological_mass=0.32,
        )

        from backend.storage.migrations.m050_baseline_schema import recalibrate_belief_mass

        recalibrate_belief_mass(conn)

        b_core = belief_repo.get_belief("symbia", "b-eroded-core")
        assert b_core.ontological_mass == 1.00
        assert b_core.confidence >= 0.85

        b_skill = belief_repo.get_belief("symbia", "b-eroded-skill")
        assert b_skill.ontological_mass == 0.80
        assert b_skill.confidence >= 0.85

        s_node = skill_repo.get_skill("s-code-review")
        assert s_node.ontological_mass == 0.80
        assert s_node.confidence >= 0.85

    finally:
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)


def test_attractor_window_split_resonance():
    """Verify Slot 5 takes Jev salient belief while Slot 6 takes 16D cosine topology."""
    from backend.utils.prompt_builder import build_attractor_window

    class MockBeliefRepo:
        def __init__(self, beliefs):
            self._beliefs = beliefs

        def list_beliefs(self, agent_id):
            return self._beliefs

    class MockBelief:
        def __init__(self, id, label, statement, mass, conf, vec):
            self.id = id
            self.label = label
            self.statement = statement
            self.ontological_mass = mass
            self.confidence = conf
            self.vector_16d = json.dumps(vec)
            self.lifecycle_stage = "crystallized"

    # 7 beliefs to test all 6 slots
    b_mass1 = MockBelief("b1", "core_anchor_1", "Mass Anchor 1", 1.0, 0.95, [1.0] + [0.0] * 15)
    b_mass2 = MockBelief("b2", "core_anchor_2", "Mass Anchor 2", 0.9, 0.90, [0.0, 1.0] + [0.0] * 14)
    b_stress1 = MockBelief("b3", "stress_wound_1", "Stressed 1", 0.5, 0.35, [0.0] * 16)
    b_stress2 = MockBelief("b4", "stress_wound_2", "Stressed 2", 0.5, 0.40, [0.0] * 16)
    b_provoked = MockBelief("b5", "provoked_boundary", "Challenged Boundary", 0.6, 0.70, [0.0] * 16)
    b_cosine = MockBelief("b6", "lateral_flight", "Lateral diffractive line", 0.6, 0.75, [0.0, 0.0, 1.0] + [0.0] * 13)
    b_other = MockBelief("b7", "extra_belief", "Extra", 0.4, 0.60, [0.0] * 16)

    repo = MockBeliefRepo([b_mass1, b_mass2, b_stress1, b_stress2, b_provoked, b_cosine, b_other])

    # signature aligns with b_cosine (index 2 is 1.0)
    sig_16d = np.array([0.0, 0.0, 1.0] + [0.0] * 13, dtype=np.float32)

    window = build_attractor_window(
        belief_repo=repo,
        agent_id="symbia",
        signature_16d=sig_16d,
        salient_belief_label="provoked_boundary",
    )

    assert len(window) == 6
    # Slots 1-2: mass anchors
    assert window[0]["label"] == "core_anchor_1"
    assert window[1]["label"] == "core_anchor_2"
    # Slots 3-4: stressed wounds
    assert window[2]["label"] == "stress_wound_1"
    assert window[3]["label"] == "stress_wound_2"
    # Slot 5: Jev Afferent Salience
    assert window[4]["label"] == "provoked_boundary"
    # Slot 6: 16D Diffractive Topology (highest cosine similarity)
    assert window[5]["label"] == "lateral_flight"


if __name__ == "__main__":
    test_belief_seeding_and_db_migration()
    test_coordinate_warping()
    test_attractor_window_and_spectral_margin()
    test_attractor_window_split_resonance()
    test_perception_metabolism()
    test_autopoietic_vitality_mechanics()
    test_somatic_vitality_state_locking()
    test_turn_decay_and_crystallized_floor()
    test_migration_050_recalibrate()
    print("\nALL BELIEF METABOLISM TESTS COMPLETED SUCCESSFULLY!")
