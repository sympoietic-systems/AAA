import json
import logging
import uuid
from datetime import datetime
from typing import Optional

import yaml
import numpy as np

from backend.modules.structural_engine import LexiconScorer
from backend.storage.models import SkillNode

logger = logging.getLogger(__name__)


class SkillService:
    def __init__(self, state):
        self._state = state

    async def get_skills(self) -> dict:
        state = self._state
        skill_repo = getattr(state, "skill_repo", None)
        if not skill_repo:
            return {"always_active": [], "on_demand": [], "collapsed": [], "proposed": [], "all": []}

        always_active = skill_repo.list_always_active()
        on_demand = skill_repo.list_on_demand()
        all_skills = skill_repo.list_skills()
        
        collapsed = [s for s in all_skills if s.lifecycle_stage == "collapsed"]
        proposed = [s for s in all_skills if s.lifecycle_stage == "nucleation"]

        return {
            "always_active": [self._format_skill(s) for s in always_active],
            "on_demand": [self._format_skill(s) for s in on_demand],
            "collapsed": [self._format_skill(s) for s in collapsed],
            "proposed": [self._format_skill(s) for s in proposed],
            "all": [self._format_skill(s) for s in all_skills],
        }

    async def update_skill_details(
        self,
        skill_id: str,
        description: Optional[str] = None,
        content: Optional[str] = None,
        trigger_keywords: Optional[list[str]] = None,
    ) -> dict:
        state = self._state
        skill_repo = getattr(state, "skill_repo", None)
        if not skill_repo:
            raise ValueError("Skill repository not initialized")

        skill = skill_repo.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill with ID {skill_id} not found")

        updates = {}
        if description is not None:
            updates["description"] = description
        if content is not None:
            updates["content"] = content
        if trigger_keywords is not None:
            updates["trigger_keywords"] = json.dumps(trigger_keywords)

        # 1. Recompute the 16D autopoietic vector if text has changed
        if description is not None or content is not None:
            embedder = getattr(state, "embedder", None)
            scorer = getattr(embedder, "service", None) if embedder else None
            
            # Content takes priority for embedding, falling back to description/existing
            vector_text = content if content else (description if description else skill.description)
            if not vector_text and skill.content:
                vector_text = skill.content
            updates["vector_16d"] = self._compute_skill_vector(vector_text, scorer)

        # Increment version on edit
        updates["version"] = skill.version + 1
        updates["changelog"] = f"Edited via Agent Page on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # 2. Update the skill in database
        updated_skill = skill_repo.update_skill(skill_id=skill_id, **updates)
        if not updated_skill:
            raise ValueError(f"Failed to update skill {skill_id}")

        # 3. Log the update to the skill_events table
        try:
            skill_repo.insert_event(
                id=str(uuid.uuid4()),
                skill_id=skill_id,
                event_type="revision",
                source_type="user",
                rationale=updates["changelog"],
            )
        except Exception as e:
            logger.warning("Failed to insert event for skill edit: %s", e)

        return self._format_skill(updated_skill)

    async def create_new_skill(
        self,
        name: str,
        description: str,
        content: Optional[str] = None,
        always_active: bool = False,
        trigger_keywords: Optional[list[str]] = None,
    ) -> dict:
        state = self._state
        skill_repo = getattr(state, "skill_repo", None)
        if not skill_repo:
            raise ValueError("Skill repository not initialized")

        # Check for name uniqueness
        existing = skill_repo.get_skill_by_name(name)
        if existing:
            raise ValueError(f"A skill with the name '{name}' already exists.")

        skill_id = str(uuid.uuid4())
        
        # Fall back to generated content template if none is provided
        if not content:
            content = self._generate_skill_content(name, description, always_active)

        # 1. Compute 16D vector
        embedder = getattr(state, "embedder", None)
        scorer = getattr(embedder, "service", None) if embedder else None
        vector_16d = self._compute_skill_vector(content, scorer)

        # 2. Save in database (initial version is 1, stage is crystallized so it's active immediately)
        new_skill = skill_repo.create_skill(
            id=skill_id,
            name=name,
            description=description,
            content=content,
            always_active=always_active,
            trigger_keywords=json.dumps(trigger_keywords or []),
            lifecycle_stage="crystallized",
            confidence=0.8,
            ontological_mass=0.1,
            vector_16d=vector_16d,
            source="authored",
            changelog="Created via Agent Page UI",
        )

        # 3. Log event
        try:
            skill_repo.insert_event(
                id=str(uuid.uuid4()),
                skill_id=skill_id,
                event_type="emergence",
                source_type="user",
                rationale="Created via Agent Page UI",
            )
        except Exception as e:
            logger.warning("Failed to insert event for skill creation: %s", e)

        return self._format_skill(new_skill)

    async def delete_skill(self, skill_id: str) -> None:
        state = self._state
        skill_repo = getattr(state, "skill_repo", None)
        if not skill_repo:
            raise ValueError("Skill repository not initialized")

        skill = skill_repo.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill with ID {skill_id} not found")

        # Delete from repo (foreign key cascade handles events)
        skill_repo.delete_skill(skill_id)

        # Clean up associated belief (label "skill:<name>")
        belief_repo = getattr(state, "belief_repo", None)
        if belief_repo:
            try:
                belief_repo.delete_belief_by_label(f"skill:{skill.name}")
            except Exception as e:
                logger.warning("Failed to clean up associated belief for skill %s: %s", skill.name, e)

    def _compute_skill_vector(self, text: str, embedder_service=None) -> str:
        result = {"v16d": [], "v384d": []}

        try:
            scorer = LexiconScorer()
            v16d = scorer.score(text)
            result["v16d"] = v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)
        except Exception as e:
            logger.warning("Failed to compute 16D structural vector: %s", e)
            result["v16d"] = [0.0] * 16

        if embedder_service:
            try:
                v384d = embedder_service.encode(text)
                result["v384d"] = v384d.tolist() if hasattr(v384d, "tolist") else list(v384d)
            except Exception as e:
                logger.warning("Failed to compute 384D embedding vector: %s", e)
                result["v384d"] = []

        return json.dumps(result)

    def _generate_skill_content(self, name: str, description: str, is_always_active: bool) -> str:
        sections = [f"# {name}\n\n{description}\n"]
        if is_always_active:
            sections.append("\n## Baseline Disposition\n\n")
            sections.append(f"This skill is a baseline disposition — part of Symbia's core personality, not a tool to activate.\n")
            sections.append(f"It is always present in the system prompt and guides every interaction.\n")
            sections.append(f"\n## Application\n\n")
            sections.append(f"Apply this disposition continuously. It requires no explicit invocation.\n")
        else:
            sections.append(f"\n## When to Use\n\n")
            sections.append(f"This skill is loaded when the conversation context matches its trigger patterns.\n")
            sections.append(f"\n## Application\n\n")
            sections.append(f"Follow the instructions below when this skill is active.\n")
        return "".join(sections)

    def _format_skill(self, skill: SkillNode) -> dict:
        trigger_keywords = []
        try:
            trigger_keywords = json.loads(skill.trigger_keywords) if skill.trigger_keywords else []
        except (json.JSONDecodeError, TypeError):
            trigger_keywords = []

        v16d = self._extract_16d_vector(skill.vector_16d)

        # Retrieve refusal reason for collapsed skills
        refusal_reason = None
        if skill.lifecycle_stage == "collapsed":
            skill_repo = getattr(self._state, "skill_repo", None)
            if skill_repo:
                try:
                    events = skill_repo.list_events(skill.id)
                    collapse_event = next((e for e in events if e.event_type == "collapse"), None)
                    if collapse_event:
                        refusal_reason = collapse_event.rationale
                except Exception as e:
                    logger.warning("Failed to fetch events for skill %s: %s", skill.id, e)

        return {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "short_content": skill.short_content,
            "always_active": skill.always_active,
            "trigger_keywords": trigger_keywords,
            "lifecycle_stage": skill.lifecycle_stage,
            "confidence": skill.confidence,
            "ontological_mass": skill.ontological_mass,
            "vector_16d": v16d,
            "source": skill.source,
            "version": skill.version,
            "changelog": skill.changelog,
            "last_used_at": skill.last_used_at.isoformat() if skill.last_used_at else None,
            "created_at": skill.created_at.isoformat() if skill.created_at else None,
            "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
            "refusal_reason": refusal_reason,
        }

    def _extract_16d_vector(self, vector_json: str) -> list[float]:
        if not vector_json or vector_json == "[]":
            return []
        try:
            data = json.loads(vector_json)
        except (json.JSONDecodeError, TypeError):
            return []

        if isinstance(data, list):
            return [float(v) for v in data]

        if isinstance(data, dict) and "v16d" in data:
            return [float(v) for v in data["v16d"]]

        return []
