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
