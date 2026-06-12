from pathlib import Path
import yaml
import json
import logging
from typing import Optional

from backend.config import load_config
from backend.storage.database import get_db_path
from backend.storage.repository import SkillRepository, BeliefRepository
from backend.modules.llm_client import BaseLLMProvider, generate_unified
from backend.modules.skill_workshop import SkillWorkshopModule

from ..base import BackgroundAction

logger = logging.getLogger(__name__)


class RefineSkillAction(BackgroundAction):
    _prompt_file = "refine_skill.yaml"

    @property
    def action_type(self) -> str:
        return "refine_skill"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        skill_data = payload.get("skill_data")
        if not skill_data and isinstance(payload.get("context"), dict):
            skill_data = payload["context"].get("skill_data")
        if not skill_data:
            skill_data = {}
            
        conversation_id = payload.get("conversation_id")
        
        if not skill_data or not skill_data.get("name"):
            return {"content": "", "model": "", "error": "No skill data or name provided"}

        # 1. Resolve database path and repositories
        config = load_config()
        db_path = str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))
        skill_repo = SkillRepository(db_path)
        belief_repo = BeliefRepository(db_path)

        # 2. Query list of existing active/crystallized skills
        try:
            existing_skills = skill_repo.list_skills()
            existing_skills_list = [
                {"name": s.name, "description": s.description, "lifecycle_stage": s.lifecycle_stage}
                for s in existing_skills
                if s.lifecycle_stage != "collapsed"
            ]
        except Exception as e:
            logger.warning("Failed to fetch existing skills: %s", e)
            existing_skills_list = []

        # 3. Load Symbia core personality
        personality_prompt = ""
        try:
            identity_path = Path(__file__).resolve().parents[4] / "personality" / "identity.yaml"
            if identity_path.exists():
                with open(identity_path, "r", encoding="utf-8") as f:
                    identity_data = yaml.safe_load(f) or {}
                    personality_prompt = identity_data.get("personality", {}).get("system_prompt", "")
        except Exception as e:
            logger.warning("Failed to load Symbia identity: %s", e)

        # 4. Assemble system prompt
        action_system_prompt = self.system_prompt()
        assembled_system_prompt = f"{action_system_prompt}\n\n[SYMBIA CORE PERSONALITY & STYLE]:\n{personality_prompt}"

        # 5. Formulate user prompt
        user_prompt = f"""Proposed Skill for Nucleation:
Name: {skill_data.get('name')}
Always Active: {skill_data.get('always_active')}
Trigger Keywords: {skill_data.get('trigger_keywords')}
Draft Content / Idea:
\"\"\"
{skill_data.get('content')}
\"\"\"

Active Skills already in Symbia's database:
{json.dumps(existing_skills_list, indent=2)}
"""

        params = {**self.default_params(), **payload.get("params", {})}

        # 6. Call LLM
        result = await generate_unified(
            provider,
            system_prompt=assembled_system_prompt,
            user_prompt=user_prompt,
            expect_json=True,
            **params,
        )

        model_used = result.get("model", "")
        data = result.get("json_data")
        
        if not data:
            # Fallback if JSON parsing failed
            content = result.get("content", "").strip()
            return {
                "decision": "refuse",
                "reason": "Failed to generate valid JSON decision",
                "content": content,
                "model": model_used
            }

        decision = data.get("decision", "refuse").lower()
        reason = data.get("reason", "No reason provided.")
        
        # 7. Apply decision
        if decision == "accept":
            refined_name = data.get("name", skill_data.get("name"))
            refined_description = data.get("description", "")
            refined_always_active = data.get("always_active", skill_data.get("always_active", False))
            refined_trigger_keywords = data.get("trigger_keywords", skill_data.get("trigger_keywords", []))
            refined_content = data.get("content", "")

            # Instantiate workshop and repositories to propose the skill
            workshop = SkillWorkshopModule(skill_repo=skill_repo, belief_repo=belief_repo)
            
            propose_cmd = {
                "action": "propose",
                "name": refined_name,
                "description": refined_description,
                "always_active": refined_always_active,
                "trigger_keywords": refined_trigger_keywords,
                "content": refined_content,
            }
            
            # Execute propose action (inserts in nucleation stage)
            prop_res = workshop._propose(propose_cmd)
            
            if prop_res.get("status") == "ok":
                skill_id = prop_res.get("skill_id")
                # Run review action to compute confidence and anti-mastery check
                rev_res = workshop._review({"skill_id": skill_id})
                
                # Check confidence for auto-crystallization of non-always-active skills
                confidence = rev_res.get("confidence", 0.0)
                if confidence >= 0.85 and not refined_always_active:
                    workshop._apply({"skill_id": skill_id, "human_approved": False})
                    logger.info("Successfully nucleated, reviewed, and auto-crystallized skill: %s (confidence=%.2f)", refined_name, confidence)
                else:
                    logger.info("Successfully nucleated and reviewed skill: %s (confidence=%.2f, always_active=%s)", refined_name, confidence, refined_always_active)
            else:
                logger.warning("Propose failed: %s", prop_res.get("message"))
        else:
            # Refused - insert as collapsed skill with the refusal reason!
            logger.info("Skill proposal '%s' refused: %s", skill_data.get("name"), reason)
            # Create a collapsed node
            import uuid
            skill_id = str(uuid.uuid4())
            try:
                skill_repo.create_skill(
                    id=skill_id,
                    name=skill_data.get("name"),
                    description=skill_data.get("content")[:200] if skill_data.get("content") else skill_data.get("name"),
                    content=skill_data.get("content") or "",
                    always_active=skill_data.get("always_active", False),
                    lifecycle_stage="collapsed",
                    confidence=0.0,
                    source="emergent",
                    changelog="Refused by Workshop Daemon",
                )
                skill_repo.insert_event(
                    id=str(uuid.uuid4()),
                    skill_id=skill_id,
                    event_type="collapse",
                    source_type="chat_turn",
                    rationale=reason
                )
            except Exception as se:
                logger.warning("Failed to record collapsed skill: %s", se)

        return {
            "decision": decision,
            "reason": reason,
            "data": data,
            "model": model_used
        }
