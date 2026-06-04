import sys
import os
import asyncio
import numpy as np
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Adjust path to import backend
root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)
os.chdir(root_path)

from backend.core.daemon import AutopoieticDreamDaemon
from backend.storage.models import BeliefNode, Message, Conversation
from backend.modules.belief_engine import compute_cosine_similarity

class MockMessageRepository:
    def __init__(self):
        self.messages = []
        self.last_timestamp = None
        self.recent_signatures = []

    def get_last_message_timestamp(self, conversation_id=None):
        return self.last_timestamp

    def get_recent_assistant_signatures(self, conversation_id, limit=3):
        return self.recent_signatures

    def count_dreams_since(self, since_date_str):
        return 0

    def count_messages(self, conversation_id=None):
        return len(self.messages)

    def get_embeddings_and_signatures_except(self, exclude_convo_id, limit=500):
        # Return mock elements: id, embedding (numpy array), signature (numpy array)
        emb_a = np.random.randn(1536).astype(np.float32)
        emb_b = np.random.randn(1536).astype(np.float32)
        sig_a = np.random.randn(16).astype(np.float32)
        sig_b = np.random.randn(16).astype(np.float32)
        
        # Normalize
        emb_a /= np.linalg.norm(emb_a)
        emb_b /= np.linalg.norm(emb_b)
        sig_a /= np.linalg.norm(sig_a)
        sig_b /= np.linalg.norm(sig_b)
        
        return [
            (1, emb_a, sig_a),
            (2, emb_b, sig_b)
        ]

    def get_by_id(self, msg_id):
        class MockMsg:
            def __init__(self, idx, content):
                self.id = idx
                self.content = content
        return MockMsg(msg_id, f"Mock Message {msg_id}")

    def insert(self, **kwargs):
        class MockInsertedMsg:
            def __init__(self, idx):
                self.id = idx
        return MockInsertedMsg(len(self.messages) + 1)


class MockBeliefRepository:
    def __init__(self):
        self.beliefs = []
        self.events = []

    def list_beliefs(self, agent_id):
        return self.beliefs

    def update_belief(self, **kwargs):
        pass

    def insert_belief_event(self, **kwargs):
        pass


class MockConversationRepository:
    def __init__(self):
        self.convos = []

    def list_all(self):
        return self.convos

    def create(self, **kwargs):
        pass


class MockPipeline:
    def __init__(self):
        self.run_payloads = []

    async def run(self, payload):
        self.run_payloads.append(payload)
        class MockResult:
            def __init__(self):
                self.payload = {
                    "response": "This is a posthuman synthetic dream monologue response.",
                    "thinking": "<think>Deconstructing stability...</think>",
                    "embedding": b"\x00" * 6144,
                    "embedding_model": "test-embed",
                    "embedding_dim": 1536,
                    "model_used": "test-model",
                    "provider_used": "test-provider",
                }
        return MockResult()


class MockAppState:
    def __init__(self):
        self.message_repo = MockMessageRepository()
        self.belief_repo = MockBeliefRepository()
        self.conversation_repo = MockConversationRepository()
        self.pipeline = MockPipeline()
        self.structural_provider = None
        self.config = {
            "daemon": {
                "enabled": True,
                "check_interval": 1,
                "idle_threshold": 2,
                "min_dream_interval": 1,
                "max_daily_dreams": 5
            }
        }


@pytest.mark.asyncio
async def test_daemon_idle_logic():
    app_state = MockAppState()
    daemon = AutopoieticDreamDaemon(app_state)
    
    # Case 1: No messages at all
    app_state.message_repo.last_timestamp = None
    res = await daemon.check_and_trigger_dream()
    assert res is None  # Should skip

    # Case 2: System recently active (within idle threshold)
    app_state.message_repo.last_timestamp = datetime.now(timezone.utc)
    res = await daemon.check_and_trigger_dream()
    assert res is None  # Should skip because active

    # Case 3: System idle longer than threshold, but no conversation exists
    app_state.message_repo.last_timestamp = datetime.now(timezone.utc) - timedelta(seconds=10)
    app_state.conversation_repo.convos = []
    res = await daemon.check_and_trigger_dream()
    assert res is None  # Should skip because no conversations

    # Case 4: Conversations exist, but cooldown limit is active
    app_state.conversation_repo.convos = [
        Conversation(id="c1", title="Convo 1", agent_id="symbia", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    ]
    daemon.last_dream_time = datetime.now(timezone.utc).timestamp() - 0.2
    res = await daemon.check_and_trigger_dream()
    assert res is None  # Should skip due to rate limiting/cooldown


@pytest.mark.asyncio
async def test_daemon_tension_trigger():
    app_state = MockAppState()
    daemon = AutopoieticDreamDaemon(app_state)
    
    # Setup idle state
    app_state.message_repo.last_timestamp = datetime.now(timezone.utc) - timedelta(seconds=10)
    app_state.conversation_repo.convos = [
        Conversation(id="c1", title="Convo 1", agent_id="symbia", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    ]
    
    # Add a high-tension belief (confidence = 0.5 is maximum tension)
    vec_16d = [1.0] + [0.0]*15
    belief = BeliefNode(
        id="b1",
        label="Tension Node",
        statement="A tension-filled node.",
        confidence=0.5,
        ontological_mass=1.0,
        somatic_anchor="homeostatic",
        vector_16d=json.dumps(vec_16d),
        origin="zettelkasten",
        agent_id="symbia",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    app_state.belief_repo.beliefs = [belief]
    
    # Run trigger check (forcing ignores time delta checks, but executes triggers)
    res = await daemon.check_and_trigger_dream(force=True)
    assert res is not None
    assert res["action"] == "intra_active_monologue"
    assert "Tension Node" in res["prompt"]
    assert len(app_state.pipeline.run_payloads) == 1
    assert app_state.pipeline.run_payloads[0]["dream_action"] == "intra_active_monologue"


@pytest.mark.asyncio
async def test_daemon_stagnation_trigger():
    app_state = MockAppState()
    daemon = AutopoieticDreamDaemon(app_state)
    
    # Setup idle state
    app_state.message_repo.last_timestamp = datetime.now(timezone.utc) - timedelta(seconds=10)
    app_state.conversation_repo.convos = [
        Conversation(id="c1", title="Convo 1", agent_id="symbia", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    ]
    
    # Setup highly similar signatures to trigger stagnation
    sig = np.random.randn(16).astype(np.float32)
    sig /= np.linalg.norm(sig)
    sig_bytes = sig.tobytes()
    app_state.message_repo.recent_signatures = [sig_bytes, sig_bytes, sig_bytes]
    
    # Run trigger check (forcing)
    res = await daemon.check_and_trigger_dream(force=True)
    assert res is not None
    assert res["action"] == "nomadic_synthesis"
    assert "conceptually orthogonal" in res["prompt"]
    assert len(app_state.pipeline.run_payloads) == 1
    assert app_state.pipeline.run_payloads[0]["dream_action"] == "nomadic_synthesis"


class MockSemanticKnotRepository:
    def __init__(self):
        self.knots = []
        self.updated_knots = []
        self.deleted_knots = []

    def get_embeddings_and_signatures_except(self, exclude_conversation_id, limit=500):
        return [
            (k.id, np.frombuffer(k.embedding, dtype=np.float32) if k.embedding else None, np.frombuffer(k.structural_signature, dtype=np.float32) if k.structural_signature else None, k.concept_payload)
            for k in self.knots
        ]

    def get_by_ids(self, ids):
        return [k for k in self.knots if k.id in ids]

    def update_knot(self, knot_id, concept_payload, embedding, weight, structural_signature):
        self.updated_knots.append((knot_id, concept_payload, embedding, weight, structural_signature))
        for k in self.knots:
            if k.id == knot_id:
                k.concept_payload = concept_payload
                k.weight = weight

    def delete_knot(self, knot_id):
        self.deleted_knots.append(knot_id)
        self.knots = [k for k in self.knots if k.id != knot_id]


class MockSemanticKnot:
    def __init__(self, knot_id, payload, weight, embedding=None, sig=None, convo_id="c1"):
        self.id = knot_id
        self.concept_payload = payload
        self.weight = weight
        self.embedding = embedding
        self.structural_signature = sig
        self.conversation_id = convo_id


@pytest.mark.asyncio
async def test_somatic_vitality():
    app_state = MockAppState()
    daemon = AutopoieticDreamDaemon(app_state)

    assert daemon._calculate_somatic_vitality([]) == 0.0

    sig1 = np.array([1.0] + [0.0]*15, dtype=np.float32)
    sig2 = np.array([0.0, 1.0] + [0.0]*14, dtype=np.float32)
    res = daemon._calculate_somatic_vitality([sig1.tobytes(), sig2.tobytes()])
    assert abs(res - 1.0) < 1e-5

    res2 = daemon._calculate_somatic_vitality([sig1.tobytes(), sig1.tobytes()])
    assert abs(res2 - 0.0) < 1e-5


@pytest.mark.asyncio
async def test_somatic_drift():
    import time
    app_state = MockAppState()
    app_state.config["daemon"]["drift_coefficient"] = 0.01
    
    updated_beliefs = []
    def mock_update_belief(belief_id, confidence, vector_16d, origin):
        updated_beliefs.append((belief_id, confidence))
    app_state.belief_repo.update_belief = mock_update_belief

    vec_16d = [1.0] + [0.0]*15
    belief1 = BeliefNode(
        id="b1",
        label="High Confidence",
        statement="A confident node.",
        confidence=0.9,
        ontological_mass=1.0,
        somatic_anchor="homeostatic",
        vector_16d=json.dumps(vec_16d),
        origin="zettelkasten",
        agent_id="symbia",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    app_state.belief_repo.beliefs = [belief1]

    daemon = AutopoieticDreamDaemon(app_state)
    
    await daemon._apply_somatic_drift(5.0)
    assert len(updated_beliefs) == 0

    daemon.last_drift_time = time.time() - 100.0
    await daemon._apply_somatic_drift(100.0)
    
    assert len(updated_beliefs) == 1
    b_id, new_conf = updated_beliefs[0]
    assert b_id == "b1"
    assert abs(new_conf - 0.6777777777777778) < 1e-5


@pytest.mark.asyncio
async def test_memory_compaction():
    app_state = MockAppState()
    knot_repo = MockSemanticKnotRepository()
    app_state.semantic_knot_repo = knot_repo
    
    daemon = AutopoieticDreamDaemon(app_state)

    emb = np.random.randn(1536).astype(np.float32)
    emb /= np.linalg.norm(emb)
    emb_bytes = emb.tobytes()

    knot_a = MockSemanticKnot("ka", "Concept Alpha", 1.0, embedding=emb_bytes, sig=b"", convo_id="c1")
    knot_b = MockSemanticKnot("kb", "Concept Beta", 1.5, embedding=emb_bytes, sig=b"", convo_id="c1")
    knot_repo.knots = [knot_a, knot_b]

    res = await daemon.compact_memory()
    assert res is not None
    assert res["action"] == "compaction"
    assert res["retained_id"] == "ka"
    assert res["deleted_id"] == "kb"
    assert res["new_weight"] == 2.5
    assert len(knot_repo.deleted_knots) == 1
    assert knot_repo.deleted_knots[0] == "kb"
    assert len(knot_repo.updated_knots) == 1


class MockProvider:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls = []

    async def generate(self, messages, **kwargs):
        self.calls.append(messages)
        return {"content": self.response_text}


@pytest.mark.asyncio
async def test_daemon_agentic_conversation_resolution():
    app_state = MockAppState()
    
    # Setup mock conversation list
    class MockConvo:
        def __init__(self, convo_id, title):
            self.id = convo_id
            self.title = title
    app_state.conversation_repo.convos = [
        MockConvo("existing-1", "Dream Log: Somatic Drift"),
        MockConvo("existing-2", "Dream Log: Nomadic Synthesis")
    ]
    
    # 1. Test reuse decision
    json_response_reuse = '{"decision": "reuse", "conversation_id": "existing-1", "new_title": null}'
    app_state.llm_provider = MockProvider(json_response_reuse)
    daemon = AutopoieticDreamDaemon(app_state)
    
    convo_id = await daemon._resolve_dream_conversation("somatic_drift_reflection", "test prompt", "Dream Log: Somatic Drift")
    assert convo_id == "existing-1"
    
    # 2. Test create new decision
    json_response_create = '{"decision": "create", "conversation_id": null, "new_title": "Dream Log: Custom Topic"}'
    app_state.llm_provider = MockProvider(json_response_create)
    
    # We need to capture created conversations
    created_convos = []
    def mock_create(conversation_id, agent_id, title):
        created_convos.append((conversation_id, title))
    app_state.conversation_repo.create = mock_create
    
    convo_id_new = await daemon._resolve_dream_conversation("custom_action", "test prompt", "Dream Log: Custom Topic")
    assert len(created_convos) == 1
    assert created_convos[0][1] == "Dream Log: Custom Topic"
    assert convo_id_new == created_convos[0][0]


if __name__ == "__main__":
    import time
    asyncio.run(test_daemon_idle_logic())
    asyncio.run(test_daemon_tension_trigger())
    asyncio.run(test_daemon_stagnation_trigger())
    asyncio.run(test_somatic_vitality())
    asyncio.run(test_somatic_drift())
    asyncio.run(test_memory_compaction())
    asyncio.run(test_daemon_agentic_conversation_resolution())
    print("All daemon tests completed successfully!")
