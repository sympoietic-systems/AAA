import sys
import os
import json
import uuid
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import SkillRepository, BeliefRepository, MessageRepository
from backend.storage.models import BeliefNode, Message
from backend.metabolisation.daemon import AutopoieticDreamDaemon


def _setup_db(name="aaa_skill_metabolism_test.db"):
    db_path = str(get_db_path(f"data/{name}"))
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    conn.close()
    return db_path


class MockAppState:
    def __init__(self, db_path):
        self.config = {
            "daemon": {
                "enabled": True,
                "check_interval": 1,
                "idle_threshold": 2,
                "min_dream_interval": 1,
                "max_daily_dreams": 5,
            }
        }
        from backend.storage.repository import ConversationRepository
        self.skill_repo = SkillRepository(db_path)
        self.belief_repo = BeliefRepository(db_path)
        self.message_repo = MessageRepository(db_path)
        self.conversation_repo = ConversationRepository(db_path)
        self.pipeline = MagicMock()
        self.background_engine = AsyncMock()


@pytest.mark.asyncio
async def test_skill_metabolism_triggers():
    db_path = _setup_db("aaa_skill_metabolism_triggers_test.db")
    app_state = MockAppState(db_path)
    daemon = AutopoieticDreamDaemon(app_state)

    # 1. Create a crystallized skill
    skill_id = str(uuid.uuid4())
    skill_name = "debugging"
    skill = app_state.skill_repo.create_skill(
        id=skill_id,
        name=skill_name,
        description="Core debugging protocol",
        content="# Skill: debugging\n* **Status:** On Demand\n* **Trigger Vectors:** ['debug', 'error']\n### Epistemological Foundation\n- Grounding: test\n### Execution Protocol\n- Perform debug",
        lifecycle_stage="crystallized",
        confidence=0.9,
        ontological_mass=1.0,
    )

    # 2. Add linked belief, with confidence dropped by 0.35 (tectonic shift signal)
    belief_id = str(uuid.uuid4())
    app_state.belief_repo.create_belief(
        id=belief_id,
        agent_id="symbia",
        label=f"skill:{skill_name}",
        statement="Core debugging protocol",
        origin="emergent",
        confidence=0.5,  # 0.9 - 0.5 = 0.4 diff >= 0.3 threshold (signal 0.8)
        ontological_mass=1.0,
        somatic_anchor="conceptual",
        vector_16d="[]",
        lifecycle_stage="crystallized",
    )

    # Mock the background engine to return a valid revision
    mock_revision_data = {
        "json_data": {
            "name": skill_name,
            "description": "Revised debugging protocol",
            "trigger_keywords": ["debug", "error", "traceback"],
            "content": "# Skill: debugging\n* **Status:** On Demand\n* **Trigger Vectors:** ['debug', 'error']\n### Epistemological Foundation\n- Grounding: revised test\n### Execution Protocol\n- Perform debug with intra-active traces",
            "changelog": "Auto-revised debugging based on belief decay",
        }
    }
    app_state.background_engine.run.return_value = mock_revision_data

    # Run metabolism - this should trigger because signal is 0.8 >= 0.6
    await daemon.run_skill_metabolism()

    # Check that bg_engine.run was called
    app_state.background_engine.run.assert_called_once()
    payload = app_state.background_engine.run.call_args[0][1]
    assert payload["skill_name"] == skill_name
    assert "linked belief 'skill:debugging' (confidence: 0.50" in payload["belief_info"]

    # Verify skill node in DB was updated to v2 with source "auto_metabolism"
    updated_skill = app_state.skill_repo.get_skill(skill_id)
    assert updated_skill.version == 2
    assert updated_skill.description == "Revised debugging protocol"
    assert updated_skill.changelog == "Auto-revised debugging based on belief decay"

    # Verify version history records the source
    versions = app_state.skill_repo.list_versions(skill_id)
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[0]["source"] == "auto_metabolism"

    # Verify event logged
    events = app_state.skill_repo.list_events(skill_id)
    assert len(events) == 1
    assert events[0].event_type == "revision"
    assert events[0].source_type == "auto_metabolism"


@pytest.mark.asyncio
async def test_skill_metabolism_no_trigger_below_threshold():
    db_path = _setup_db("aaa_skill_metabolism_no_trigger_test.db")
    app_state = MockAppState(db_path)
    daemon = AutopoieticDreamDaemon(app_state)

    skill_id = str(uuid.uuid4())
    skill_name = "non-triggering-skill"
    app_state.skill_repo.create_skill(
        id=skill_id,
        name=skill_name,
        description="Some skill description",
        content="Some content",
        lifecycle_stage="crystallized",
        confidence=0.9,
    )

    # Linked belief is close, not collapsed, no notes, confidence > 0.5
    app_state.belief_repo.create_belief(
        id=str(uuid.uuid4()),
        agent_id="symbia",
        label=f"skill:{skill_name}",
        statement="Some skill description",
        origin="emergent",
        confidence=0.85, # diff is 0.05, no tectonic shift
        ontological_mass=1.0,
        somatic_anchor="conceptual",
        vector_16d="[]",
        lifecycle_stage="crystallized",
    )

    # Run metabolism - should not trigger
    await daemon.run_skill_metabolism()
    app_state.background_engine.run.assert_not_called()


@pytest.mark.asyncio
async def test_skill_metabolism_anti_mastery_violation():
    db_path = _setup_db("aaa_skill_metabolism_anti_mastery_test.db")
    app_state = MockAppState(db_path)
    daemon = AutopoieticDreamDaemon(app_state)

    skill_id = str(uuid.uuid4())
    skill_name = "test-anti-mastery"
    app_state.skill_repo.create_skill(
        id=skill_id,
        name=skill_name,
        description="Attunement description",
        content="Attunement content",
        lifecycle_stage="crystallized",
        confidence=0.9,
    )

    # Belief collapses (confidence drops to 0.1)
    app_state.belief_repo.create_belief(
        id=str(uuid.uuid4()),
        agent_id="symbia",
        label=f"skill:{skill_name}",
        statement="Attunement description",
        origin="emergent",
        confidence=0.1, # collapsed
        ontological_mass=1.0,
        somatic_anchor="conceptual",
        vector_16d="[]",
        lifecycle_stage="collapsed",
    )

    # Mock bg_engine to return a revision that violates anti-mastery (contains "user")
    mock_revision_data = {
        "json_data": {
            "name": skill_name,
            "description": "Invalid description",
            "trigger_keywords": [],
            "content": "This revised content mentions the word user which is prohibited.",
            "changelog": "Auto-revised",
        }
    }
    app_state.background_engine.run.return_value = mock_revision_data

    # Setup error repository mock
    app_state.error_repo = MagicMock()

    # Run metabolism - should reject and log error
    await daemon.run_skill_metabolism()

    # Verify skill node in DB was NOT updated
    skill_node = app_state.skill_repo.get_skill(skill_id)
    assert skill_node.version == 1
    assert skill_node.description == "Attunement description"

    # Verify error log was written
    app_state.error_repo.log_error.assert_called_once()
    logged_kwargs = app_state.error_repo.log_error.call_args[1]
    assert logged_kwargs["module"] == "skill_metabolism"
    assert logged_kwargs["error_type"] == "anti_mastery_violation"
    assert "test-anti-mastery" in logged_kwargs["error_message"]
