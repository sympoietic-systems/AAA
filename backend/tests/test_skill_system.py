import sys
import os
import json
import uuid
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import BeliefRepository, SkillRepository
from backend.storage.models import SkillNode, SkillEvent


def _setup_db(name="aaa_skill_test.db"):
    db_path = str(get_db_path(f"data/{name}"))
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    conn.close()
    return db_path


def test_migration_creates_tables():
    db_path = _setup_db("aaa_skill_migration_test.db")
    repo = SkillRepository(db_path)

    skills = repo.list_skills()
    assert len(skills) == 0
    assert repo.skill_count() == 0


def test_create_and_get_skill():
    db_path = _setup_db("aaa_skill_create_test.db")
    repo = SkillRepository(db_path)

    skill = repo.create_skill(
        id=str(uuid.uuid4()),
        name="test-skill",
        description="A test skill",
        content="# Test\n\nTest content.",
        short_content="Test skill summary",
        always_active=False,
        trigger_keywords='["test", "example"]',
        lifecycle_stage="crystallized",
        confidence=0.85,
        ontological_mass=1.0,
        source="authored",
    )

    assert skill.name == "test-skill"
    assert skill.description == "A test skill"
    assert skill.content == "# Test\n\nTest content."
    assert skill.short_content == "Test skill summary"
    assert skill.always_active is False
    assert skill.lifecycle_stage == "crystallized"
    assert skill.confidence == 0.85
    assert skill.ontological_mass == 1.0
    assert skill.source == "authored"
    assert skill.version == 1

    fetched = repo.get_skill(skill.id)
    assert fetched is not None
    assert fetched.name == "test-skill"

    by_name = repo.get_skill_by_name("test-skill")
    assert by_name is not None
    assert by_name.id == skill.id


def test_list_and_filter_skills():
    db_path = _setup_db("aaa_skill_list_test.db")
    repo = SkillRepository(db_path)

    repo.create_skill(
        id=str(uuid.uuid4()), name="always-skill", description="Always active skill",
        content="# Always", short_content="Always summary", always_active=True,
        lifecycle_stage="crystallized", confidence=0.90, ontological_mass=1.2,
    )
    repo.create_skill(
        id=str(uuid.uuid4()), name="on-demand-skill", description="On-demand skill",
        content="# On-demand", short_content="", always_active=False,
        lifecycle_stage="crystallized", confidence=0.80, ontological_mass=1.0,
    )
    repo.create_skill(
        id=str(uuid.uuid4()), name="proto-skill", description="Proto skill",
        content="# Proto", always_active=False,
        lifecycle_stage="nucleation", confidence=0.0, ontological_mass=0.05,
    )

    all_skills = repo.list_skills()
    assert len(all_skills) == 3

    crystallized = repo.list_crystallized()
    assert len(crystallized) == 2

    always = repo.list_always_active()
    assert len(always) == 1
    assert always[0].name == "always-skill"

    on_demand = repo.list_on_demand()
    assert len(on_demand) == 1
    assert on_demand[0].name == "on-demand-skill"

    nucleated = repo.list_by_stage("nucleation")
    assert len(nucleated) == 1
    assert nucleated[0].name == "proto-skill"


def test_update_skill():
    db_path = _setup_db("aaa_skill_update_test.db")
    repo = SkillRepository(db_path)

    skill = repo.create_skill(
        id=str(uuid.uuid4()), name="update-skill", description="Original",
        content="Old content", lifecycle_stage="nucleation",
    )

    updated = repo.update_skill(
        skill_id=skill.id,
        content="New content",
        description="Updated description",
        lifecycle_stage="crystallized",
        confidence=0.90,
        version=2,
        changelog="Major revision",
    )
    assert updated.content == "New content"
    assert updated.description == "Updated description"
    assert updated.lifecycle_stage == "crystallized"
    assert updated.confidence == 0.90
    assert updated.version == 2
    assert updated.changelog == "Major revision"


def test_skill_events():
    db_path = _setup_db("aaa_skill_events_test.db")
    repo = SkillRepository(db_path)

    skill = repo.create_skill(
        id=str(uuid.uuid4()), name="event-skill", description="Event test",
        content="# Events",
    )

    repo.insert_event(
        id=str(uuid.uuid4()), skill_id=skill.id,
        event_type="emergence", source_type="chat_turn",
        rationale="Initial proposal",
    )
    repo.insert_event(
        id=str(uuid.uuid4()), skill_id=skill.id,
        event_type="revision", source_type="chat_turn",
        rationale="Improved instructions",
    )
    repo.insert_event(
        id=str(uuid.uuid4()), skill_id=skill.id,
        event_type="crystallization", source_type="chat_turn",
        rationale="Approved by human co-review",
    )

    events = repo.list_events(skill.id)
    assert len(events) == 3
    event_types = {e.event_type for e in events}
    assert event_types == {"emergence", "revision", "crystallization"}


def test_record_usage():
    db_path = _setup_db("aaa_skill_usage_test.db")
    repo = SkillRepository(db_path)

    skill = repo.create_skill(
        id=str(uuid.uuid4()), name="usage-skill", description="Usage test",
        content="# Usage",
    )
    assert skill.last_used_at is None

    repo.record_usage(skill.id)
    updated = repo.get_skill(skill.id)
    assert updated.last_used_at is not None


def test_delete_skill():
    db_path = _setup_db("aaa_skill_delete_test.db")
    repo = SkillRepository(db_path)

    skill = repo.create_skill(
        id=str(uuid.uuid4()), name="delete-skill", description="Delete me",
        content="# Delete",
    )
    assert repo.skill_count() == 1

    repo.delete_skill(skill.id)
    assert repo.skill_count() == 0
    assert repo.get_skill(skill.id) is None


def test_belief_bridge_creation():
    db_path = _setup_db("aaa_skill_bridge_test.db")
    skill_repo = SkillRepository(db_path)
    belief_repo = BeliefRepository(db_path)

    skill = skill_repo.create_skill(
        id=str(uuid.uuid4()), name="bridge-skill", description="Bridge test",
        content="# Bridge", lifecycle_stage="crystallized",
        confidence=0.85, ontological_mass=1.0,
    )

    belief_repo.create_belief(
        id=str(uuid.uuid4()), agent_id="symbia",
        label=f"skill:{skill.name}",
        statement=skill.description,
        origin="emergent",
        confidence=skill.confidence,
        ontological_mass=skill.ontological_mass,
        somatic_anchor="conceptual",
        vector_16d="[]",
        lifecycle_stage="crystallized",
    )

    beliefs = belief_repo.list_beliefs("symbia")
    skill_beliefs = [b for b in beliefs if b.label and b.label.startswith("skill:")]
    assert len(skill_beliefs) == 1
    assert skill_beliefs[0].label == "skill:bridge-skill"
    assert skill_beliefs[0].confidence == 0.85


async def test_service_update_skill_details():
    from backend.services.skill import SkillService
    
    db_path = _setup_db("aaa_skill_service_test.db")
    skill_repo = SkillRepository(db_path)
    
    class MockState:
        def __init__(self):
            self.skill_repo = skill_repo
            self.embedder = None
            
    state = MockState()
    
    skill = skill_repo.create_skill(
        id=str(uuid.uuid4()), name="service-skill", description="Original description",
        content="Original content", lifecycle_stage="crystallized",
    )
    
    service = SkillService(state)
    updated = await service.update_skill_details(
        skill_id=skill.id,
        description="New description",
        content="New content",
        trigger_keywords=["word1", "word2"]
    )
    
    assert updated["description"] == "New description"
    assert updated["trigger_keywords"] == ["word1", "word2"]
    
    # Verify in DB
    db_skill = skill_repo.get_skill(skill.id)
    assert db_skill.description == "New description"
    assert db_skill.content == "New content"
    assert json.loads(db_skill.trigger_keywords) == ["word1", "word2"]
    assert db_skill.version == 2
    
    # Verify event logged
    events = skill_repo.list_events(skill.id)
    assert len(events) == 1
    assert events[0].event_type == "revision"
    assert events[0].source_type == "user"


async def test_service_create_and_delete_skill():
    from backend.services.skill import SkillService
    
    db_path = _setup_db("aaa_skill_service_create_delete_test.db")
    skill_repo = SkillRepository(db_path)
    belief_repo = BeliefRepository(db_path)
    
    class MockState:
        def __init__(self):
            self.skill_repo = skill_repo
            self.belief_repo = belief_repo
            self.embedder = None
            
    state = MockState()
    service = SkillService(state)
    
    # 1. Create a skill
    created = await service.create_new_skill(
        name="test-create",
        description="A test creation description",
        content="# Test Content",
        always_active=True,
        trigger_keywords=["test", "create"]
    )
    
    assert created["name"] == "test-create"
    assert created["always_active"] is True
    assert created["trigger_keywords"] == ["test", "create"]
    assert created["version"] == 1
    assert created["lifecycle_stage"] == "crystallized"
    
    # Verify DB
    db_skill = skill_repo.get_skill_by_name("test-create")
    assert db_skill is not None
    assert db_skill.id == created["id"]
    
    # Verify creation event
    events = skill_repo.list_events(db_skill.id)
    assert len(events) == 1
    assert events[0].event_type == "emergence"
    assert events[0].source_type == "user"
    
    # Try creating duplicate name
    try:
        await service.create_new_skill(name="test-create", description="dup")
        assert False, "Should raise ValueError on duplicate name"
    except ValueError:
        pass
        
    # 2. Add associated belief to simulate system linking
    belief_repo.create_belief(
        id=str(uuid.uuid4()),
        agent_id="symbia",
        label="skill:test-create",
        statement="Test creation description",
        origin="emergent",
        confidence=0.8,
        ontological_mass=0.1,
        somatic_anchor="conceptual",
        vector_16d="[]",
    )
    
    assert len(belief_repo.list_beliefs("symbia")) == 1
    
    # 3. Delete the skill
    await service.delete_skill(created["id"])
    
    # Verify skill deleted
    assert skill_repo.get_skill(created["id"]) is None
    # Verify associated belief deleted
    assert len(belief_repo.list_beliefs("symbia")) == 0


def test_skills_api_flux_control():
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.services.skill import SkillService
    
    db_path = _setup_db("aaa_skill_api_test.db")
    skill_repo = SkillRepository(db_path)
    belief_repo = BeliefRepository(db_path)
    
    # Override app state repos
    app.state.skill_repo = skill_repo
    app.state.belief_repo = belief_repo
    
    # Create a skill in repo
    skill = skill_repo.create_skill(
        id=str(uuid.uuid4()), name="api-skill", description="desc", content="content"
    )
    
    client = TestClient(app)
    
    # Save original env state
    orig_flux = os.environ.get("AAA_AGENT_FLUX")
    
    try:
        # Test 1: When AAA_AGENT_FLUX is False/unset
        if "AAA_AGENT_FLUX" in os.environ:
            del os.environ["AAA_AGENT_FLUX"]
            
        # GET /api/agent should return agent_flux=False
        res = client.get("/api/agent")
        assert res.status_code == 200
        assert res.json()["agent_flux"] is False
        
        # POST /api/skills should return 403 Forbidden
        res = client.post("/api/skills", json={"name": "new", "description": "desc"})
        assert res.status_code == 403
        
        # PUT /api/skills/{id} should return 403 Forbidden
        res = client.put(f"/api/skills/{skill.id}", json={"description": "new"})
        assert res.status_code == 403
        
        # DELETE /api/skills/{id} should return 403 Forbidden
        res = client.delete(f"/api/skills/{skill.id}")
        assert res.status_code == 403
        
        # Test 2: When AAA_AGENT_FLUX is True
        os.environ["AAA_AGENT_FLUX"] = "true"
        
        # GET /api/agent should return agent_flux=True
        res = client.get("/api/agent")
        assert res.status_code == 200
        assert res.json()["agent_flux"] is True
        
        # POST /api/skills should succeed and create skill
        res = client.post("/api/skills", json={"name": "new-api-skill", "description": "desc"})
        assert res.status_code == 200
        assert res.json()["name"] == "new-api-skill"
        
        # PUT /api/skills/{id} should succeed
        res = client.put(f"/api/skills/{skill.id}", json={"description": "new-desc"})
        assert res.status_code == 200
        assert res.json()["description"] == "new-desc"
        
        # DELETE /api/skills/{id} should succeed
        res = client.delete(f"/api/skills/{skill.id}")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
    finally:
        # Restore env
        if orig_flux is not None:
            os.environ["AAA_AGENT_FLUX"] = orig_flux
        elif "AAA_AGENT_FLUX" in os.environ:
            del os.environ["AAA_AGENT_FLUX"]


def test_skill_version_history_and_revert():
    db_path = _setup_db("aaa_skill_versions_test.db")
    repo = SkillRepository(db_path)

    # 1. Create skill (should write v1 to skill_versions)
    skill = repo.create_skill(
        id=str(uuid.uuid4()),
        name="versioned-skill",
        description="Version 1 description",
        content="Version 1 content",
    )
    assert skill.version == 1

    versions = repo.list_versions(skill.id)
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["content"] == "Version 1 content"

    # 2. Update skill (should write v2 to skill_versions)
    updated = repo.update_skill(
        skill_id=skill.id,
        content="Version 2 content",
        description="Version 2 description",
        version=2,
        changelog="Updated to v2",
    )
    assert updated.version == 2

    versions = repo.list_versions(skill.id)
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[0]["content"] == "Version 2 content"
    assert versions[1]["version"] == 1
    assert versions[1]["content"] == "Version 1 content"


def test_skills_version_api():
    from fastapi.testclient import TestClient
    from backend.main import app
    
    db_path = _setup_db("aaa_skill_versions_api_test.db")
    skill_repo = SkillRepository(db_path)
    
    app.state.skill_repo = skill_repo
    client = TestClient(app)
    
    # Create skill and edit it to generate v2
    skill = skill_repo.create_skill(
        id=str(uuid.uuid4()), name="revert-skill", description="d1", content="c1"
    )
    skill_repo.update_skill(
        skill_id=skill.id, content="c2", description="d2", version=2, changelog="edited"
    )
    
    # Set agent flux env
    orig_flux = os.environ.get("AAA_AGENT_FLUX")
    os.environ["AAA_AGENT_FLUX"] = "true"
    
    try:
        # GET /api/skills/{id}/versions
        res = client.get(f"/api/skills/{skill.id}/versions")
        assert res.status_code == 200
        data = res.json()
        assert len(data["versions"]) == 2
        assert data["versions"][0]["version"] == 2
        assert data["versions"][1]["version"] == 1
        
        # POST /api/skills/{id}/revert/1
        res = client.post(f"/api/skills/{skill.id}/revert/1")
        assert res.status_code == 200
        reverted = res.json()
        assert reverted["version"] == 3
        assert reverted["content"] == "c1"
        assert reverted["description"] == "d1"
        
        # Verify events logged a revert revision
        events = skill_repo.list_events(skill.id)
        assert any("Reverted to version 1" in e.rationale for e in events)
        
    finally:
        if orig_flux is not None:
            os.environ["AAA_AGENT_FLUX"] = orig_flux
        elif "AAA_AGENT_FLUX" in os.environ:
            del os.environ["AAA_AGENT_FLUX"]


def test_list_recent_events():
    db_path = _setup_db("aaa_skill_recent_events_test.db")
    repo = SkillRepository(db_path)

    skill = repo.create_skill(
        id=str(uuid.uuid4()), name="recent-event-skill", description="Recent event test",
        content="# Recent Events",
    )

    repo.insert_event(
        id=str(uuid.uuid4()), skill_id=skill.id,
        event_type="emergence", source_type="user",
        rationale="Initial creation",
    )

    events = repo.list_recent_events(limit=5)
    assert len(events) == 1
    assert events[0]["skill_name"] == "recent-event-skill"
    assert events[0]["event_type"] == "emergence"
    assert events[0]["source_type"] == "user"
    assert events[0]["rationale"] == "Initial creation"


def test_skills_events_api():
    from fastapi.testclient import TestClient
    from backend.main import app
    
    db_path = _setup_db("aaa_skill_events_api_test.db")
    skill_repo = SkillRepository(db_path)
    app.state.skill_repo = skill_repo
    
    skill = skill_repo.create_skill(
        id=str(uuid.uuid4()), name="api-event-skill", description="desc", content="content"
    )
    skill_repo.insert_event(
        id=str(uuid.uuid4()), skill_id=skill.id,
        event_type="emergence", source_type="user",
        rationale="Proposed",
    )
    
    client = TestClient(app)
    res = client.get("/api/skills/events?limit=10")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 1
    assert events[0]["skill_name"] == "api-event-skill"
    assert events[0]["event_type"] == "emergence"




