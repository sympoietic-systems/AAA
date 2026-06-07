import json
import logging
from typing import Optional

import numpy as np

from backend.modules.base import ProcessingModule

logger = logging.getLogger(__name__)

MAX_AUTO_LOADED = 3
VECTOR_SIMILARITY_THRESHOLD = 0.7
MAX_SKILL_CONTENT_CHARS = 2000


class SkillActivatorModule(ProcessingModule):
    """Pipeline module that auto-loads relevant skills each turn.

    Runs after belief_metabolism (for attractor window) and before
    prompt_assembler (for injection into system prompt).

    Three-layer trigger:
    1. Attractor window resonance — skill beliefs in the attractor window
    2. Semantic vector matching — cosine similarity of conversation vs skill vectors
    3. Keyword trigger matching — substring match against trigger_keywords
    """

    def __init__(self, skill_repo=None, belief_repo=None):
        self._skill_repo = skill_repo
        self._belief_repo = belief_repo

    @property
    def name(self) -> str:
        return "skill_activator"

    def validate(self) -> bool:
        return True

    def set_repos(self, skill_repo, belief_repo):
        self._skill_repo = skill_repo
        self._belief_repo = belief_repo

    async def process(self, payload: dict) -> dict:
        if not self._skill_repo:
            payload["loaded_skills"] = []
            return payload

        active_skills = self._skill_repo.list_crystallized()
        if not active_skills:
            payload["loaded_skills"] = []
            return payload

        on_demand_skills = [s for s in active_skills if not s.always_active]
        if not on_demand_skills:
            payload["loaded_skills"] = []
            return payload

        candidates: dict[str, dict] = {}

        # Strategy A: Attractor Window Resonance
        attractor_window = payload.get("attractor_window", [])
        self._match_attractor_window(attractor_window, on_demand_skills, candidates)

        # Strategy B: Semantic Vector Matching
        current_vector = self._get_current_vector(payload)
        if current_vector is not None:
            self._match_semantic(current_vector, on_demand_skills, candidates)

        # Strategy C: Keyword Trigger Matching
        user_message = self._get_user_message(payload)
        if user_message:
            self._match_keywords(user_message, on_demand_skills, candidates)

        sorted_candidates = sorted(
            candidates.values(),
            key=lambda c: (c["priority"], c.get("score", 0)),
            reverse=True,
        )

        loaded = sorted_candidates[:MAX_AUTO_LOADED]

        loaded_skills = []
        for candidate in loaded:
            skill = candidate["skill"]
            content = skill.content or ""
            truncated = content[:MAX_SKILL_CONTENT_CHARS]
            if len(content) > MAX_SKILL_CONTENT_CHARS:
                truncated += "\n... [truncated — call load_skill for full content]"

            loaded_skills.append({
                "id": skill.id,
                "name": skill.name,
                "content_truncated": truncated,
                "match_reason": candidate["reason"],
                "score": candidate.get("score"),
            })

            try:
                self._skill_repo.record_usage(skill.id)
            except Exception as e:
                logger.warning("Failed to record skill usage for %s: %s", skill.name, e)

        payload["loaded_skills"] = loaded_skills
        return payload

    def _match_attractor_window(self, attractor_window, on_demand_skills, candidates):
        for item in attractor_window:
            origin = item.get("origin", "")
            if origin != "skill":
                continue
            label = item.get("label", "")
            for skill in on_demand_skills:
                if f"skill:{skill.name}" == label or label == skill.name or label == f"skill-{skill.name}":
                    if skill.name not in candidates:
                        candidates[skill.name] = {
                            "skill": skill,
                            "reason": "Attractor window resonance",
                            "priority": 3,
                            "score": item.get("mass", 0.5),
                        }
                    break

    def _match_semantic(self, current_vector, on_demand_skills, candidates):
        if current_vector is None:
            return
        for skill in on_demand_skills:
            if skill.name in candidates:
                continue
            skill_vec = self._parse_vector(skill.vector_16d or "[]")
            if skill_vec is None:
                continue
            try:
                dot = np.dot(current_vector, skill_vec)
                norm_current = np.linalg.norm(current_vector)
                norm_skill = np.linalg.norm(skill_vec)
                if norm_current == 0 or norm_skill == 0:
                    continue
                similarity = dot / (norm_current * norm_skill)
            except Exception:
                continue
            if similarity >= VECTOR_SIMILARITY_THRESHOLD:
                candidates[skill.name] = {
                    "skill": skill,
                    "reason": f"Semantic match (cos_sim={similarity:.2f})",
                    "priority": 2,
                    "score": float(similarity),
                }

    def _match_keywords(self, user_message: str, on_demand_skills, candidates):
        msg_lower = user_message.lower()
        for skill in on_demand_skills:
            if skill.name in candidates:
                continue
            trigger_keywords = self._parse_trigger_keywords(skill.trigger_keywords or "[]")
            for keyword in trigger_keywords:
                if keyword.lower() in msg_lower:
                    candidates[skill.name] = {
                        "skill": skill,
                        "reason": f"Keyword match: '{keyword}'",
                        "priority": 1,
                        "score": 0.5,
                    }
                    break

    def _get_current_vector(self, payload: dict) -> Optional[np.ndarray]:
        vector_raw = payload.get("current_vector_16d")
        if vector_raw is not None:
            if isinstance(vector_raw, np.ndarray):
                return vector_raw
            if isinstance(vector_raw, list):
                return np.array(vector_raw, dtype=np.float32)
        return None

    def _get_user_message(self, payload: dict) -> Optional[str]:
        messages = payload.get("messages", [])
        if not messages:
            return None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                return msg.get("content", "")
        return None

    def _parse_vector(self, vector_json: str) -> Optional[np.ndarray]:
        if not vector_json or vector_json == "[]":
            return None
        try:
            return np.array(json.loads(vector_json), dtype=np.float32)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def _parse_trigger_keywords(self, trigger_json: str) -> list[str]:
        if not trigger_json or trigger_json == "[]":
            return []
        try:
            return json.loads(trigger_json)
        except (json.JSONDecodeError, TypeError):
            return []
