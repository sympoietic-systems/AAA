import os
import sys
import uuid
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import SkillRepository, BeliefRepository
from backend.utils.skill_parser import parse_skill_nucleation_tags
from backend.modules.background_tasks.actions.refine_skill import RefineSkillAction
from backend.services.skill import SkillService


def _setup_db(name="aaa_skill_refinement_test.db"):
    db_path = str(get_db_path(f"data/{name}"))
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    conn.close()
    return db_path


def test_parse_skill_nucleation_tags():
    # 1. Basic unescaped tag in chat response
    chat_text = "Let's nucleate this: <skill-nucleation name=\"concept-weaver\" always_active=\"false\" trigger_keywords=\"['weave', 'concept']\">\n# Concept Weaver\nBehavior guidelines...\n</skill-nucleation> And that is it."
    cleaned, skills = parse_skill_nucleation_tags(chat_text)
    
    assert "concept-weaver" in [s["name"] for s in skills]
    assert skills[0]["always_active"] is False
    assert "weave" in skills[0]["trigger_keywords"]
    assert "# Concept Weaver" in skills[0]["content"]
    assert "<skill-nucleation" not in cleaned
    assert "</skill-nucleation>" not in cleaned

    # 2. Tag inside parsed JSON field with escaped quotes
    json_summary = "We observed a pattern. <skill-nucleation name=\\\"cybernetic-weaving\\\" always_active=\\\"true\\\" trigger_keywords=\\\"['cyber', 'weaving']\\\">\nInstructions...\n</skill-nucleation>"
    cleaned_json, skills_json = parse_skill_nucleation_tags(json_summary)
    
    assert skills_json[0]["name"] == "cybernetic-weaving"
    assert skills_json[0]["always_active"] is True
    assert "cyber" in skills_json[0]["trigger_keywords"]
    assert "Instructions..." in skills_json[0]["content"]
    assert "<skill-nucleation" not in cleaned_json

    # 3. Tag with no attributes
    no_attribs = "Some text <skill-nucleation>Draft content</skill-nucleation>"
    cleaned_na, skills_na = parse_skill_nucleation_tags(no_attribs)
    assert skills_na[0]["name"] == "unnamed-skill"
    assert skills_na[0]["always_active"] is False
    assert skills_na[0]["content"] == "Draft content"

    # 4. Spacing, colons, and different quoting styles
    spacing_text = "Let's try <skill_nucleation name : 'spaced-name' always_active = true trigger_keywords = [\"a\", \"b\"]>Content here</skill-nucleation>"
    cleaned_sp, skills_sp = parse_skill_nucleation_tags(spacing_text)
    assert skills_sp[0]["name"] == "spaced-name"
    assert skills_sp[0]["always_active"] is True
    assert "a" in skills_sp[0]["trigger_keywords"]
    assert skills_sp[0]["content"] == "Content here"

    # 5. Missing closing tag at the end of text
    unclosed_text = "Some intro <skill-nucleation name='unclosed'>Remaining content till the end"
    cleaned_uc, skills_uc = parse_skill_nucleation_tags(unclosed_text)
    assert cleaned_uc.strip() == "Some intro"
    assert skills_uc[0]["name"] == "unclosed"
    assert skills_uc[0]["content"] == "Remaining content till the end"

    # 6. Multiple sequential tags where one is unclosed
    multi_text = "Intro <skill-nucleation name='first'>first content <skill-nucleation name='second'>second content</skill-nucleation> outro"
    cleaned_mu, skills_mu = parse_skill_nucleation_tags(multi_text)
    assert cleaned_mu.strip() == "Intro  outro"

    assert len(skills_mu) == 2
    assert skills_mu[0]["name"] == "first"
    assert skills_mu[0]["content"] == "first content"
    assert skills_mu[1]["name"] == "second"
    assert skills_mu[1]["content"] == "second content"



@pytest.mark.asyncio
async def test_refine_skill_action_accepts():
    db_path = _setup_db("aaa_refine_accept_test.db")
    
    # Mock configuration loading to use our test db path
    import backend.modules.background_tasks.actions.refine_skill as refine_mod
    refine_mod.load_config = lambda: {"database": {"path": f"data/aaa_refine_accept_test.db"}}

    # Create proposed skill payload
    skill_data = {
        "name": "temporary-weaving",
        "always_active": False,
        "trigger_keywords": ["weaving"],
        "content": "Draft instructions for weaving."
    }

    # Mock LLM provider to return accepted response
    provider = MagicMock()
    
    refined_markdown = """# temporary-weaving
Refined orientation description.

## AI Instructions
1. First rule.
2. Second rule.
3. Third rule.
"""
    mock_response = {
        "content": "json text content",
        "model": "mock-model",
        "json_data": {
            "decision": "accept",
            "reason": "Vetted and accepted.",
            "name": "temporary-weaving",
            "description": "Refined short description",
            "always_active": False,
            "trigger_keywords": ["weaving", "yarn"],
            "content": refined_markdown
        }
    }
    
    # generate_unified is imported in refine_skill, mock it
    async def mock_generate(*args, **kwargs):
        return mock_response
    refine_mod.generate_unified = mock_generate

    action = RefineSkillAction()
    result = await action.execute(provider, {"skill_data": skill_data, "conversation_id": "test-conv"})

    assert result["decision"] == "accept"
    assert result["reason"] == "Vetted and accepted."

    # Verify skill exists in database and is crystallized due to high confidence (0.95)
    repo = SkillRepository(db_path)
    skill = repo.get_skill_by_name("temporary-weaving")
    assert skill is not None
    assert skill.lifecycle_stage == "crystallized"
    assert skill.confidence >= 0.85
    assert "weaving" in json.loads(skill.trigger_keywords)
    assert "## AI Instructions" in skill.content


@pytest.mark.asyncio
async def test_refine_skill_action_refuses():
    db_path = _setup_db("aaa_refine_refuse_test.db")
    
    # Mock configuration loading to use our test db path
    import backend.modules.background_tasks.actions.refine_skill as refine_mod
    refine_mod.load_config = lambda: {"database": {"path": f"data/aaa_refine_refuse_test.db"}}

    skill_data = {
        "name": "redundant-skill",
        "always_active": False,
        "trigger_keywords": ["test"],
        "content": "redundant content"
    }

    # Mock LLM provider to return refuse response
    provider = MagicMock()
    mock_response = {
        "content": "json text content",
        "model": "mock-model",
        "json_data": {
            "decision": "refuse",
            "reason": "Duplicate of existing skill."
        }
    }
    
    async def mock_generate(*args, **kwargs):
        return mock_response
    refine_mod.generate_unified = mock_generate

    action = RefineSkillAction()
    result = await action.execute(provider, {"skill_data": skill_data, "conversation_id": "test-conv"})

    assert result["decision"] == "refuse"
    assert result["reason"] == "Duplicate of existing skill."

    # Verify skill is recorded in database as collapsed (refused)
    repo = SkillRepository(db_path)
    skill = repo.get_skill_by_name("redundant-skill")
    assert skill is not None
    assert skill.lifecycle_stage == "collapsed"
    
    events = repo.list_events(skill.id)
    assert len(events) > 0
    assert events[0].event_type == "collapse"
    assert events[0].rationale == "Duplicate of existing skill."


@pytest.mark.asyncio
async def test_skill_service_returns_collapsed_and_proposed():
    db_path = _setup_db("aaa_service_stages_test.db")
    repo = SkillRepository(db_path)

    # 1. Crystallized always_active
    repo.create_skill(
        id=str(uuid.uuid4()), name="active-baseline", description="baseline description",
        content="# baseline", always_active=True, lifecycle_stage="crystallized", confidence=0.9
    )
    # 2. Crystallized on_demand
    repo.create_skill(
        id=str(uuid.uuid4()), name="active-ondemand", description="ondemand description",
        content="# ondemand", always_active=False, lifecycle_stage="crystallized", confidence=0.8
    )
    # 3. Nucleation (proposed)
    repo.create_skill(
        id=str(uuid.uuid4()), name="proposed-skill", description="proposed description",
        content="# proposed", always_active=False, lifecycle_stage="nucleation", confidence=0.0
    )
    # 4. Collapsed (refused)
    repo.create_skill(
        id=str(uuid.uuid4()), name="refused-skill", description="refused description",
        content="# refused", always_active=False, lifecycle_stage="collapsed", confidence=0.0
    )

    state = MagicMock()
    state.skill_repo = repo
    service = SkillService(state)
    result = await service.get_skills()

    assert len(result["always_active"]) == 1
    assert result["always_active"][0]["name"] == "active-baseline"

    assert len(result["on_demand"]) == 1
    assert result["on_demand"][0]["name"] == "active-ondemand"

    assert len(result["proposed"]) == 1
    assert result["proposed"][0]["name"] == "proposed-skill"

    assert len(result["collapsed"]) == 1
    assert result["collapsed"][0]["name"] == "refused-skill"

    assert len(result["all"]) == 4
