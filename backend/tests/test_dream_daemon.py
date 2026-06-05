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
        self._metabolized_ids = set()

    def get_last_message_timestamp(self, conversation_id=None):
        return self.last_timestamp

    def get_recent_assistant_signatures(self, conversation_id, limit=3):
        return self.recent_signatures

    def count_dreams_since(self, since_date_str):
        return 0

    def count_messages(self, conversation_id=None):
        return len(self.messages)

    def get_embeddings_and_signatures_except(self, exclude_convo_id, limit=500):
        emb_a = np.random.randn(1536).astype(np.float32)
        emb_b = np.random.randn(1536).astype(np.float32)
        sig_a = np.random.randn(16).astype(np.float32)
        sig_b = np.random.randn(16).astype(np.float32)
        
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

    def get_recent(self, limit=50, conversation_id=None):
        class MockRecentMsg:
            def __init__(self, idx, content, speaker="apparatus"):
                self.id = idx
                self.content = content
                self.speaker = speaker
        return [MockRecentMsg(1, "Mock dream response content.", "apparatus")]

    def insert(self, **kwargs):
        class MockInsertedMsg:
            def __init__(self, idx):
                self.id = idx
        return MockInsertedMsg(len(self.messages) + 1)

    def mark_message_metabolized(self, message_id):
        self._metabolized_ids.add(message_id)


class MockBeliefRepository:
    def __init__(self):
        self.beliefs = []
        self.events = []
        self._last_dreamed_updates = {}

    def list_beliefs(self, agent_id):
        return self.beliefs

    def update_belief(self, **kwargs):
        pass

    def insert_belief_event(self, **kwargs):
        pass

    def update_belief_last_dreamed(self, belief_id, timestamp=None):
        self._last_dreamed_updates[belief_id] = timestamp or datetime.now(timezone.utc).isoformat()

    def get_events_for_belief(self, belief_id, limit=20):
        return []

    def update_belief_mass(self, belief_id, mass):
        pass

    def update_belief_stage(self, belief_id, stage):
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


class MockProvider:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls = []

    async def generate(self, messages, **kwargs):
        self.calls.append(messages)
        return {"content": self.response_text}


class MockAppState:
    def __init__(self):
        self.message_repo = MockMessageRepository()
        self.belief_repo = MockBeliefRepository()
        self.conversation_repo = MockConversationRepository()
        self.pipeline = MockPipeline()
        self.structural_provider = None
        self.llm_provider = None
        self.config = {
            "daemon": {
                "enabled": True,
                "check_interval": 1,
                "idle_threshold": 2,
                "min_dream_interval": 1,
                "max_daily_dreams": 5,
                "belief_dream_cooldown_minutes": 30,
                "prompt_hash_window": 10,
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
async def test_daemon_tension_trigger_fallback():
    """Tests tension hotspot triggers using fallback prompt (no LLM provider)."""
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
    
    # Run trigger check (forcing ignores time delta checks, executes triggers)
    # Without LLM provider, uses fallback template
    res = await daemon.check_and_trigger_dream(force=True)
    assert res is not None
    assert res["action"] == "intra_active_monologue"
    assert "Tension Node" in res["prompt"]
    assert len(app_state.pipeline.run_payloads) == 1
    assert app_state.pipeline.run_payloads[0]["dream_action"] == "intra_active_monologue"


@pytest.mark.asyncio
async def test_daemon_tension_trigger_with_llm():
    """Tests tension hotspot triggers with LLM-generated dynamic prompt."""
    app_state = MockAppState()
    
    # Provide a mock LLM provider that generates a custom prompt
    custom_prompt = "Considering your recent shift toward posthuman ontologies, how does the belief 'Tension Node' need to be re-evaluated in light of your current ecosystem vitality?"
    app_state.llm_provider = MockProvider(custom_prompt)
    
    daemon = AutopoieticDreamDaemon(app_state)
    
    # Setup idle state
    app_state.message_repo.last_timestamp = datetime.now(timezone.utc) - timedelta(seconds=10)
    app_state.conversation_repo.convos = [
        Conversation(id="c1", title="Convo 1", agent_id="symbia", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    ]
    
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
    
    res = await daemon.check_and_trigger_dream(force=True)
    assert res is not None
    assert res["action"] == "intra_active_monologue"
    # Should use the LLM-generated prompt, not the fallback
    assert res["prompt"] == custom_prompt
    assert len(app_state.pipeline.run_payloads) == 1


@pytest.mark.asyncio
async def test_belief_dream_cooldown():
    """Tests that beliefs within cooldown window are skipped."""
    app_state = MockAppState()
    daemon = AutopoieticDreamDaemon(app_state)
    
    # Set a short cooldown for testing
    daemon.belief_dream_cooldown_minutes = 30
    
    # Setup idle state
    app_state.message_repo.last_timestamp = datetime.now(timezone.utc) - timedelta(seconds=10)
    app_state.conversation_repo.convos = [
        Conversation(id="c1", title="Convo 1", agent_id="symbia", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    ]
    
    # Add two beliefs, one recently dreamed
    vec_a = [1.0] + [0.0]*15
    vec_b = [0.0] + [1.0] + [0.0]*14
    belief_recent = BeliefNode(
        id="b1",
        label="Recently Dreamed",
        statement="This was just dreamed about.",
        confidence=0.5,
        ontological_mass=1.0,
        somatic_anchor="homeostatic",
        vector_16d=json.dumps(vec_a),
        origin="zettelkasten",
        agent_id="symbia",
        last_dreamed_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    belief_eligible = BeliefNode(
        id="b2",
        label="Eligible",
        statement="This is eligible for dreaming.",
        confidence=0.5,
        ontological_mass=1.0,
        somatic_anchor="homeostatic",
        vector_16d=json.dumps(vec_b),
        origin="zettelkasten",
        agent_id="symbia",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    app_state.belief_repo.beliefs = [belief_recent, belief_eligible]
    
    # Should skip the recently-dreamed belief and pick the other one
    hotspot, score = await daemon._evaluate_tension_hotspot()
    assert hotspot is not None
    assert hotspot.id == "b2", f"Expected eligible belief b2, got {hotspot.label}"
    assert score > 0.0


@pytest.mark.asyncio
async def test_belief_dream_cooldown_all_blocked():
    """Tests that when ALL beliefs are in cooldown, no hotspot is found."""
    app_state = MockAppState()
    daemon = AutopoieticDreamDaemon(app_state)
    
    daemon.belief_dream_cooldown_minutes = 30
    
    app_state.message_repo.last_timestamp = datetime.now(timezone.utc) - timedelta(seconds=10)
    app_state.conversation_repo.convos = [
        Conversation(id="c1", title="Convo 1", agent_id="symbia", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    ]
    
    vec = [1.0] + [0.0]*15
    belief = BeliefNode(
        id="b1",
        label="Cooled Down",
        statement="Just dreamed about.",
        confidence=0.5,
        ontological_mass=1.0,
        somatic_anchor="homeostatic",
        vector_16d=json.dumps(vec),
        origin="zettelkasten",
        agent_id="symbia",
        last_dreamed_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    app_state.belief_repo.beliefs = [belief]
    
    hotspot, score = await daemon._evaluate_tension_hotspot()
    assert hotspot is None, "Expected no hotspot when all beliefs in cooldown"
    assert score == 0.0


@pytest.mark.asyncio
async def test_prompt_hash_dedup():
    """Tests that duplicate prompts across dream cycles are regenerated."""
    app_state = MockAppState()
    
    call_count = [0]
    responses = ["Same prompt text", "Same prompt text", "Different prompt text"]
    
    class CountingProvider:
        def __init__(self):
            self.calls = []
        async def generate(self, messages, **kwargs):
            self.calls.append(messages)
            idx = min(call_count[0], len(responses) - 1)
            result = responses[idx]
            call_count[0] += 1
            return {"content": result}
    
    provider = CountingProvider()
    app_state.llm_provider = provider
    daemon = AutopoieticDreamDaemon(app_state)
    
    context = {
        "belief_label": "test",
        "belief_statement": "test statement",
        "belief_confidence": 0.5,
        "action": "intra_active_monologue",
    }
    
    # First dream: returns "Same prompt text", hash added to deque
    prompt1 = await daemon._generate_dream_prompt("intra_active_monologue", context)
    assert prompt1 == "Same prompt text"
    assert call_count[0] == 1
    
    # Second dream: LLM returns "Same prompt text" again (attempt 0)
    # Hash collision detected → regenerate with modified user_prompt (attempt 1)
    # LLM returns "Same prompt text" again (count 3) → collision again → regenerate (attempt 2)
    # LLM returns "Different prompt text" (count 4) → accepted
    prompt2 = await daemon._generate_dream_prompt("intra_active_monologue", context)
    assert prompt2 == "Different prompt text", f"Expected final unique prompt, got: {prompt2}"
    assert call_count[0] == 3, f"Expected 3 generate calls (first dream 1 + second dream 1 collision + 1 accepted), got {call_count[0]}"


@pytest.mark.asyncio
async def test_fallback_prompt_generation():
    """Tests that fallback prompts are generated when no LLM available."""
    app_state = MockAppState()
    daemon = AutopoieticDreamDaemon(app_state)
    
    context = {
        "belief_label": "posthuman ethics",
        "belief_statement": "Posthuman ethics emerge from relational ontologies.",
        "belief_confidence": 0.5,
    }
    
    prompt = await daemon._generate_dream_prompt("intra_active_monologue", context)
    assert "posthuman ethics" in prompt
    assert "Critically examine" in prompt or "posthuman" in prompt.lower()


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
    assert len(app_state.pipeline.run_payloads) == 1
    assert app_state.pipeline.run_payloads[0]["dream_action"] == "nomadic_synthesis"


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
async def test_mass_decay():
    import time
    app_state = MockAppState()
    app_state.config["belief_ecosystem"] = {"mass_decay": {"lambda_base": 0.05}}

    updated_masses = []
    updated_stages = []
    def mock_update_belief_mass(belief_id, mass):
        updated_masses.append((belief_id, mass))
    def mock_update_belief_stage(belief_id, stage):
        updated_stages.append((belief_id, stage))
    app_state.belief_repo.update_belief_mass = mock_update_belief_mass
    app_state.belief_repo.update_belief_stage = mock_update_belief_stage

    vec_16d = [1.0] + [0.0]*15
    from datetime import timedelta
    belief1 = BeliefNode(
        id="b1",
        label="Decaying Belief",
        statement="A belief that hasn't been reinforced.",
        confidence=0.8,
        ontological_mass=0.8,
        somatic_anchor="conceptual",
        vector_16d=json.dumps(vec_16d),
        origin="authoring",
        agent_id="symbia",
        lifecycle_stage="crystallized",
        last_reinforced_at=datetime.now(timezone.utc) - timedelta(hours=10),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    app_state.belief_repo.beliefs = [belief1]

    daemon = AutopoieticDreamDaemon(app_state)

    # Short idle shouldn't trigger decay
    await daemon._apply_mass_decay(5.0)
    assert len(updated_masses) == 0

    # Long idle should trigger decay
    daemon.last_decay_time = time.time() - 100.0
    await daemon._apply_mass_decay(100.0)

    assert len(updated_masses) == 1
    b_id, new_mass = updated_masses[0]
    assert b_id == "b1"
    assert new_mass < 0.8


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


@pytest.mark.asyncio
async def test_daemon_agentic_conversation_resolution():
    app_state = MockAppState()
    
    class MockConvo:
        def __init__(self, convo_id, title):
            self.id = convo_id
            self.title = title
    app_state.conversation_repo.convos = [
        MockConvo("existing-1", "Dream Log: Somatic Drift"),
        MockConvo("existing-2", "Dream Log: Nomadic Synthesis")
    ]
    
    json_response_reuse = '{"decision": "reuse", "conversation_id": "existing-1", "new_title": null}'
    app_state.llm_provider = MockProvider(json_response_reuse)
    daemon = AutopoieticDreamDaemon(app_state)
    
    convo_id = await daemon._resolve_dream_conversation("somatic_drift_reflection", "test prompt", "Dream Log: Somatic Drift")
    assert convo_id == "existing-1"
    
    json_response_create = '{"decision": "create", "conversation_id": null, "new_title": "Dream Log: Custom Topic"}'
    app_state.llm_provider = MockProvider(json_response_create)
    
    created_convos = []
    def mock_create(conversation_id, agent_id, title):
        created_convos.append((conversation_id, title))
    app_state.conversation_repo.create = mock_create
    
    convo_id_new = await daemon._resolve_dream_conversation("custom_action", "test prompt", "Dream Log: Custom Topic")
    assert len(created_convos) == 1
    assert created_convos[0][1] == "Dream Log: Custom Topic"
    assert convo_id_new == created_convos[0][0]


@pytest.mark.asyncio
async def test_daemon_updates_belief_last_dreamed():
    """Tests that after a hotspot-triggered dream, the belief's last_dreamed_at is updated."""
    app_state = MockAppState()
    daemon = AutopoieticDreamDaemon(app_state)
    
    app_state.message_repo.last_timestamp = datetime.now(timezone.utc) - timedelta(seconds=10)
    app_state.conversation_repo.convos = [
        Conversation(id="c1", title="Convo 1", agent_id="symbia", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    ]
    
    vec_16d = [1.0] + [0.0]*15
    belief = BeliefNode(
        id="b1",
        label="To Be Updated",
        statement="Will have last_dreamed_at set.",
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
    
    assert "b1" not in app_state.belief_repo._last_dreamed_updates
    
    res = await daemon.check_and_trigger_dream(force=True)
    assert res is not None
    assert "b1" in app_state.belief_repo._last_dreamed_updates, \
        "Expected belief b1 to have last_dreamed_at updated after dream"


if __name__ == "__main__":
    asyncio.run(test_daemon_idle_logic())
    asyncio.run(test_daemon_tension_trigger_fallback())
    asyncio.run(test_daemon_tension_trigger_with_llm())
    asyncio.run(test_belief_dream_cooldown())
    asyncio.run(test_belief_dream_cooldown_all_blocked())
    asyncio.run(test_prompt_hash_dedup())
    asyncio.run(test_fallback_prompt_generation())
    asyncio.run(test_daemon_stagnation_trigger())
    asyncio.run(test_somatic_vitality())
    asyncio.run(test_mass_decay())
    asyncio.run(test_memory_compaction())
    asyncio.run(test_daemon_agentic_conversation_resolution())
    asyncio.run(test_daemon_updates_belief_last_dreamed())
    print("All daemon tests completed successfully!")
