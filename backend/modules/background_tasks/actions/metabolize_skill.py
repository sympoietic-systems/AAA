from pathlib import Path
import yaml
import json
import logging
from typing import Optional

from backend.config import load_config
from backend.storage.database import get_db_path
from backend.modules.llm_client import BaseLLMProvider, generate_unified

from ..base import BackgroundAction

logger = logging.getLogger(__name__)


class MetabolizeSkillAction(BackgroundAction):
    _prompt_file = "metabolize_skill.yaml"

    @property
    def action_type(self) -> str:
        return "metabolize_skill"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        skill_name = payload.get("skill_name")
        skill_content = payload.get("skill_content")
        belief_info = payload.get("belief_info", "")
        notes_info = payload.get("notes_info", "")

        personality_prompt = ""
        try:
            identity_path = Path(__file__).resolve().parents[4] / "personality" / "identity.yaml"
            if identity_path.exists():
                with open(identity_path, "r", encoding="utf-8") as f:
                    identity_data = yaml.safe_load(f) or {}
                    personality_prompt = identity_data.get("personality", {}).get("system_prompt", "")
        except Exception as e:
            logger.warning("Failed to load Symbia identity: %s", e)

        action_system_prompt = self.system_prompt()
        assembled_system_prompt = f"{action_system_prompt}\n\n[SYMBIA CORE PERSONALITY & STYLE]:\n{personality_prompt}"

        user_prompt = f"""
Existing Skill Content:
\"\"\"
{skill_content}
\"\"\"

Metabolic Feedback Signals:
- Epistemological Belief Shifts: {belief_info}
- Accumulated Improvisation Notes (friction comments):
{notes_info}
"""

        params = {**self.default_params(), **payload.get("params", {})}

        result = await generate_unified(
            provider,
            system_prompt=assembled_system_prompt,
            user_prompt=user_prompt,
            expect_json=True,
            **params,
        )

        return result
