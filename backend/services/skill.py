import json
import logging
import uuid

import yaml
import numpy as np

from backend.storage.models import SkillNode

logger = logging.getLogger(__name__)


class SkillService:
    def __init__(self, state):
        self._state = state

    async def get_skills(self) -> dict:
        state = self._state
        skill_repo = getattr(state, "skill_repo", None)
        if not skill_repo:
            return {"always_active": [], "on_demand": [], "all": []}

        self._seed_initial_skills_if_needed()

        always_active = skill_repo.list_always_active()
        on_demand = skill_repo.list_on_demand()
        all_skills = skill_repo.list_skills()

        return {
            "always_active": [self._format_skill(s) for s in always_active],
            "on_demand": [self._format_skill(s) for s in on_demand],
            "all": [self._format_skill(s) for s in all_skills],
        }

    def _seed_initial_skills_if_needed(self) -> None:
        state = self._state
        skill_repo = getattr(state, "skill_repo", None)
        if not skill_repo:
            return

        count = skill_repo.skill_count()
        if count > 0:
            self._repair_empty_skill_content(skill_repo)
            return

        identity = getattr(state, "config", {}).get("personality", {})
        identity_path = identity.get("path", "backend/personality/identity.yaml")
        from pathlib import Path
        parent_dir = Path(identity_path).parent if identity_path else Path(__file__).parent.parent / "personality"
        seed_path = parent_dir / "seed_skills.yaml"

        if isinstance(parent_dir, str):
            parent_dir = Path(parent_dir)
            seed_path = parent_dir / "seed_skills.yaml"

        if not seed_path.exists():
            project_root = Path(__file__).parent.parent
            seed_path = project_root / "personality" / "seed_skills.yaml"
            if not seed_path.exists():
                seed_path = project_root.parent / "backend" / "personality" / "seed_skills.yaml"

        if not seed_path.exists():
            logger.warning("seed_skills.yaml not found, cannot seed skills")
            return

        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            logger.error("Error loading seed_skills.yaml: %s", e)
            return

        skills_cfg = data.get("skills", {})
        if not skills_cfg:
            logger.info("No skills section in identity.yaml, skipping skill seeding")
            return

        embedder = getattr(state, "embedder", None)
        scorer = getattr(embedder, "service", None) if embedder else None

        always_active = skills_cfg.get("always_active", [])
        on_demand = skills_cfg.get("on_demand", [])

        belief_repo = getattr(state, "belief_repo", None)

        for skill_def in always_active:
            skill_id = str(uuid.uuid4())
            name = skill_def["id"]
            statement = skill_def["statement"]

            vec_json = "[]"
            if scorer:
                try:
                    vec = scorer.encode(statement)
                    if hasattr(vec, 'tolist'):
                        vec_json = json.dumps(vec.tolist())
                    else:
                        vec_json = json.dumps(list(vec))
                except Exception as e:
                    logger.warning("Failed to compute vector for skill %s: %s", name, e)

            content = self._generate_skill_content(name, statement, is_always_active=True)

            skill_repo.create_skill(
                id=skill_id,
                name=name,
                description=statement,
                content=content,
                short_content=statement,
                always_active=True,
                trigger_keywords="[]",
                lifecycle_stage="crystallized",
                confidence=0.90,
                ontological_mass=1.2,
                vector_16d=vec_json,
                source="authored",
            )

            if belief_repo:
                try:
                    belief_repo.create_belief(
                        id=str(uuid.uuid4()),
                        agent_id="symbia",
                        label=f"skill:{name}",
                        statement=statement,
                        origin="emergent",
                        confidence=0.90,
                        ontological_mass=1.2,
                        somatic_anchor="conceptual",
                        vector_16d=vec_json,
                        lifecycle_stage="crystallized",
                    )
                except Exception as e:
                    logger.warning("Failed to create belief bridge for skill %s: %s", name, e)

        for skill_def in on_demand:
            skill_id = str(uuid.uuid4())
            name = skill_def["id"]
            description = skill_def.get("description", name)
            triggers = skill_def.get("triggers", [])
            trigger_json = json.dumps(triggers)

            vec_json = "[]"
            if scorer:
                try:
                    vec = scorer.encode(description)
                    if hasattr(vec, 'tolist'):
                        vec_json = json.dumps(vec.tolist())
                    else:
                        vec_json = json.dumps(list(vec))
                except Exception as e:
                    logger.warning("Failed to compute vector for skill %s: %s", name, e)

            content = skill_def.get("content", "")
            if not content:
                content = self._generate_skill_content(name, description, is_always_active=False)

            skill_repo.create_skill(
                id=skill_id,
                name=name,
                description=description,
                content=content,
                short_content="",
                always_active=False,
                trigger_keywords=trigger_json,
                lifecycle_stage="crystallized",
                confidence=0.85,
                ontological_mass=1.0,
                vector_16d=vec_json,
                source="authored",
            )

            if belief_repo:
                try:
                    belief_repo.create_belief(
                        id=str(uuid.uuid4()),
                        agent_id="symbia",
                        label=f"skill:{name}",
                        statement=description,
                        origin="emergent",
                        confidence=0.85,
                        ontological_mass=1.0,
                        somatic_anchor="conceptual",
                        vector_16d=vec_json,
                        lifecycle_stage="crystallized",
                    )
                except Exception as e:
                    logger.warning("Failed to create belief bridge for skill %s: %s", name, e)

        total = len(always_active) + len(on_demand)
        logger.info("Seeded %d initial skills (%d always-active, %d on-demand)", total, len(always_active), len(on_demand))

    def _repair_empty_skill_content(self, skill_repo) -> None:
        skills = skill_repo.list_skills()
        repaired = 0
        for skill in skills:
            if skill.content and len(skill.content.strip()) > 50:
                continue

            seed_content = self._find_seed_content(skill.name)
            if not seed_content:
                continue

            skill_repo.update_skill(
                skill_id=skill.id,
                content=seed_content,
            )
            repaired += 1
            logger.info("Repaired empty content for skill '%s' from seed", skill.name)

        if repaired > 0:
            logger.info("Repaired %d skills with empty/stub content", repaired)

    def _find_seed_content(self, skill_name: str) -> str:
        from pathlib import Path
        import yaml

        project_root = Path(__file__).parent.parent
        seed_path = project_root / "personality" / "seed_skills.yaml"
        if not seed_path.exists():
            seed_path = project_root.parent / "backend" / "personality" / "seed_skills.yaml"
        if not seed_path.exists():
            return ""

        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception:
            return ""

        skills_cfg = data.get("skills", {})
        for skill_def in skills_cfg.get("on_demand", []):
            if skill_def.get("id") == skill_name:
                return skill_def.get("content", "")
        for skill_def in skills_cfg.get("always_active", []):
            if skill_def.get("id") == skill_name:
                return skill_def.get("content", "")
        return ""

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
            "source": skill.source,
            "version": skill.version,
            "changelog": skill.changelog,
            "last_used_at": skill.last_used_at.isoformat() if skill.last_used_at else None,
            "created_at": skill.created_at.isoformat() if skill.created_at else None,
            "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
        }
