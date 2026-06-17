import json
import logging

import numpy as np

from backend.modules.base import ProcessingModule

logger = logging.getLogger(__name__)

MAX_AUTO_LOADED = 3
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
            payload["always_active_skills"] = []
            payload["on_demand_skills"] = []
            return payload

        all_skills = self._skill_repo.list_crystallized()
        always_active_skills = [s for s in all_skills if s.always_active]
        on_demand_skills = [s for s in all_skills if not s.always_active]

        payload["always_active_skills"] = [
            {
                "name": s.name,
                "short_content": s.short_content or s.description,
                "content": s.content or "",
            }
            for s in always_active_skills
        ]
        payload["on_demand_skills"] = [
            {"name": s.name, "description": s.description}
            for s in on_demand_skills
        ]

        if not on_demand_skills:
            payload["loaded_skills"] = []
            return payload

        candidates: dict[str, dict] = {}

        # Strategy A: Attractor Window Resonance (pipeline-specific)
        attractor_window = payload.get("attractor_window", [])
        self._match_attractor_window(attractor_window, on_demand_skills, candidates)

        # Strategies B + C: Delegated to shared match_on_demand_skills()
        current_vector = self._get_current_vector(payload)
        user_message = self._get_user_message(payload)
        if on_demand_skills and (current_vector is not None or user_message):
            from backend.utils.prompt_builder import match_on_demand_skills
            matched = match_on_demand_skills(
                on_demand_skills,
                user_message or "",
                current_vector,
                max_matched=MAX_AUTO_LOADED,
            )
            # Merge without overwriting A-candidates (higher priority 3)
            for m in matched:
                if m["skill"].name not in candidates:
                    candidates[m["skill"].name] = m

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
                "description": skill.short_content or skill.description,
                "content_truncated": truncated,
                "match_reason": candidate["reason"],
                "score": candidate.get("score"),
            })

            try:
                self._skill_repo.record_usage(skill.id)
            except Exception as e:
                logger.warning("Failed to record skill usage for %s: %s", skill.name, e)

        payload["loaded_skills"] = loaded_skills
        self._detect_underperformance(payload, all_skills)
        return payload

    def _detect_underperformance(self, payload: dict, all_skills) -> None:
        underperforming = []
        for skill in all_skills:
            if skill.lifecycle_stage != "crystallized":
                continue
            if skill.confidence < 0.3:
                underperforming.append(f"{skill.name} (confidence={skill.confidence:.2f})")
        if underperforming:
            note = f"[Skill underperformance detected: {', '.join(underperforming)}. These skills may be misaligned with current entanglement patterns.]"
            payload.setdefault("skill_ecology_notes", []).append(note)

    def _match_attractor_window(self, attractor_window, on_demand_skills, candidates):
        for item in attractor_window:
            label = item.get("label", "")
            if not label.startswith("skill:"):
                continue
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

    def _get_current_vector(self, payload: dict) -> Optional[np.ndarray]:
        vector_raw = payload.get("current_vector_16d")
        if vector_raw is not None:
            if isinstance(vector_raw, np.ndarray):
                return vector_raw
            if isinstance(vector_raw, list):
                return np.array(vector_raw, dtype=np.float32)

        structural_sig = payload.get("structural_signature")
        if structural_sig is not None:
            try:
                if isinstance(structural_sig, bytes):
                    return np.frombuffer(structural_sig, dtype=np.float32)
                if isinstance(structural_sig, list):
                    return np.array(structural_sig, dtype=np.float32)
                if isinstance(structural_sig, np.ndarray):
                    return structural_sig.astype(np.float32)
            except Exception:
                pass

        embedding_blob = payload.get("embedding")
        if embedding_blob is not None:
            try:
                if isinstance(embedding_blob, bytes):
                    return np.frombuffer(embedding_blob, dtype=np.float32)
                if isinstance(embedding_blob, list):
                    return np.array(embedding_blob, dtype=np.float32)
                if isinstance(embedding_blob, np.ndarray):
                    return embedding_blob.astype(np.float32)
            except Exception:
                return None
        return None

    def _get_user_message(self, payload: dict) -> Optional[str]:
        messages = payload.get("messages", [])
        if not messages:
            return None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                return msg.get("content", "")
        return None

    def _parse_vector(self, vector_json: str, target_dim: int = None) -> Optional[np.ndarray]:
        if not vector_json or vector_json == "[]":
            return None
        try:
            data = json.loads(vector_json)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

        if isinstance(data, dict):
            if target_dim:
                key = "v16d" if target_dim == 16 else "v384d" if target_dim >= 100 else None
                if key and key in data and data[key]:
                    return np.array(data[key], dtype=np.float32)
            for key in ("v16d", "v384d"):
                if key in data and data[key]:
                    return np.array(data[key], dtype=np.float32)
            return None

        if isinstance(data, list):
            return np.array(data, dtype=np.float32)

        return None


