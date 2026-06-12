import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from backend.modules.base import ProcessingModule

logger = logging.getLogger(__name__)

# Three-tier approval thresholds from ADR-031
CONFIDENCE_NUCLEATION_MAX = 0.4
CONFIDENCE_CO_REVIEW_MAX = 0.85


class SkillWorkshopModule(ProcessingModule):
    """Skill Workshop — Symbia's procedural organ for creating and evolving skills.

    Registered as an on-demand pipeline module with triggers:
    [\"skill workshop\", \"create skill\", \"new skill\", \"develop skill\"]

    Actions are dispatched via payload[\"skill_workshop_command\"]:
    - propose:  Draft a new skill → nucleation
    - revise:   Edit an existing skill → version increment
    - review:   Diffractive analysis → confidence + anti-mastery assessment
    - apply:    Activate skill → crystallized
    - reject:   Decline proposal → collapsed
    - load:     Load full skill content into context
    - list:     List all proposals/active skills
    - inspect:  View full details of a specific skill
    """

    def __init__(self, skill_repo=None, belief_repo=None):
        self._skill_repo = skill_repo
        self._belief_repo = belief_repo

    @property
    def name(self) -> str:
        return "skill_workshop"

    def validate(self) -> bool:
        return self._skill_repo is not None

    def set_repos(self, skill_repo, belief_repo):
        self._skill_repo = skill_repo
        self._belief_repo = belief_repo

    async def process(self, payload: dict) -> dict:
        command = payload.get("skill_workshop_command")
        if not command or not self._skill_repo:
            return payload

        action = command.get("action", "")
        result = None

        try:
            if action == "propose":
                result = self._propose(command)
            elif action == "revise":
                result = self._revise(command)
            elif action == "review":
                result = self._review(command)
            elif action == "apply":
                result = self._apply(command)
            elif action == "reject":
                result = self._reject(command)
            elif action == "load":
                result = self._load(command)
            elif action == "list":
                result = self._list_skills(command)
            elif action == "inspect":
                result = self._inspect(command)
            else:
                result = {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            logger.error("Skill workshop action '%s' failed: %s", action, e, exc_info=True)
            result = {"status": "error", "message": str(e)}

        payload["skill_workshop_result"] = result
        return payload

    # ── Actions ──────────────────────────────────────────────

    def _propose(self, command: dict) -> dict:
        name = command.get("name", "").strip()
        description = command.get("description", "").strip()
        content = command.get("content", "").strip()
        always_active = command.get("always_active", False)
        trigger_keywords = command.get("trigger_keywords", [])

        if not name or not description:
            return {"status": "error", "message": "name and description are required"}

        existing = self._skill_repo.get_skill_by_name(name)
        if existing:
            return {"status": "error", "message": f"Skill '{name}' already exists (stage: {existing.lifecycle_stage})"}

        skill_id = str(uuid.uuid4())
        trigger_json = json.dumps(trigger_keywords) if trigger_keywords else "[]"

        vector_16d = "[]"
        try:
            from backend.modules.structural_engine import LexiconScorer
            scorer = LexiconScorer()
            text_to_score = content or description
            v16d = scorer.score(text_to_score)
            vector_dict = {"v16d": v16d.tolist() if hasattr(v16d, "tolist") else list(v16d), "v384d": []}
            vector_16d = json.dumps(vector_dict)
        except Exception as se:
            logger.warning("Failed to score proposed skill vector: %s", se)
            vector_16d = json.dumps({"v16d": [0.0] * 16, "v384d": []})

        skill = self._skill_repo.create_skill(
            id=skill_id,
            name=name,
            description=description,
            content=content,
            short_content=description if always_active else "",
            always_active=always_active,
            trigger_keywords=trigger_json,
            lifecycle_stage="nucleation",
            confidence=0.0,
            ontological_mass=0.05,
            vector_16d=vector_16d,
            source="emergent",
        )

        if always_active:
            self._skill_repo.insert_event(
                id=str(uuid.uuid4()),
                skill_id=skill_id,
                event_type="emergence",
                source_type="chat_turn",
                rationale="Proposed as always-active — requires explicit human affirmation to apply.",
            )
            message = (
                f"Skill '{name}' nucleated as always-active. "
                f"Always-active skills require explicit human affirmation to crystallize. "
                f"Use 'review' then 'apply' with human approval."
            )
        else:
            self._skill_repo.insert_event(
                id=str(uuid.uuid4()),
                skill_id=skill_id,
                event_type="emergence",
                source_type="chat_turn",
            )
            message = (
                f"Skill '{name}' nucleated (stage: nucleation, confidence: 0.0). "
                f"Use 'review' to assess, then 'apply' to crystallize."
            )

        return {"status": "ok", "skill_id": skill_id, "name": name, "message": message}

    def _revise(self, command: dict) -> dict:
        skill_id = command.get("skill_id", "")
        name = command.get("name", "")
        content = command.get("content")
        description = command.get("description")
        changelog = command.get("changelog", "")

        skill = self._resolve_skill(skill_id, name)
        if isinstance(skill, dict):
            return skill

        new_version = skill.version + 1

        vector_16d = None
        if content is not None or description is not None:
            text_to_score = content if content is not None else skill.content
            if not text_to_score:
                text_to_score = description if description is not None else skill.description
            
            if text_to_score:
                try:
                    from backend.modules.structural_engine import LexiconScorer
                    scorer = LexiconScorer()
                    v16d = scorer.score(text_to_score)
                    vector_dict = {"v16d": v16d.tolist() if hasattr(v16d, "tolist") else list(v16d), "v384d": []}
                    vector_16d = json.dumps(vector_dict)
                except Exception as se:
                    logger.warning("Failed to score revised skill vector: %s", se)

        updated = self._skill_repo.update_skill(
            skill_id=skill.id,
            content=content,
            description=description,
            version=new_version,
            changelog=changelog,
            vector_16d=vector_16d,
        )

        if not updated:
            return {"status": "error", "message": f"Failed to update skill '{skill.name}'"}

        self._skill_repo.insert_event(
            id=str(uuid.uuid4()),
            skill_id=skill.id,
            event_type="revision",
            source_type="chat_turn",
            rationale=changelog,
        )

        return {
            "status": "ok",
            "skill_id": skill.id,
            "name": skill.name,
            "version": new_version,
            "message": f"Skill '{skill.name}' revised to version {new_version}.",
        }

    def _review(self, command: dict) -> dict:
        skill_id = command.get("skill_id", "")
        name = command.get("name", "")

        skill = self._resolve_skill(skill_id, name)
        if isinstance(skill, dict):
            return skill

        confidence = self._compute_confidence(skill)
        anti_mastery = self._assess_anti_mastery(skill)

        updated = self._skill_repo.update_skill(
            skill_id=skill.id,
            confidence=confidence,
        )

        self._skill_repo.insert_event(
            id=str(uuid.uuid4()),
            skill_id=skill.id,
            event_type="crystallization" if confidence >= CONFIDENCE_NUCLEATION_MAX else "emergence",
            source_type="chat_turn",
            rationale=f"Diffractive review: confidence={confidence:.2f}, anti-mastery={anti_mastery.get('score', '?')}/3",
        )

        approval_tier = self._approval_tier(confidence, skill.always_active)

        return {
            "status": "ok",
            "skill_id": skill.id,
            "name": skill.name,
            "confidence": confidence,
            "anti_mastery_assessment": anti_mastery,
            "approval_tier": approval_tier,
            "message": (
                f"Review complete for '{skill.name}': confidence={confidence:.2f}. "
                f"Tier: {approval_tier}. "
                f"{'Requires explicit human affirmation (always-active).' if skill.always_active else ''}"
            ),
        }

    def _apply(self, command: dict) -> dict:
        skill_id = command.get("skill_id", "")
        name = command.get("name", "")
        human_approved = command.get("human_approved", False)

        skill = self._resolve_skill(skill_id, name)
        if isinstance(skill, dict):
            return skill

        if skill.always_active and not human_approved:
            return {
                "status": "error",
                "message": (
                    f"Skill '{skill.name}' is always-active and requires explicit human affirmation. "
                    f"Set human_approved=true after co-review."
                ),
            }

        if skill.confidence < CONFIDENCE_NUCLEATION_MAX:
            return {
                "status": "error",
                "message": (
                    f"Skill '{skill.name}' has confidence {skill.confidence:.2f} (< {CONFIDENCE_NUCLEATION_MAX}). "
                    f"Run 'review' first to assess readiness."
                ),
            }

        approval_tier = self._approval_tier(skill.confidence, skill.always_active)
        if approval_tier == "co_review" and not human_approved and not skill.always_active:
            return {
                "status": "error",
                "message": (
                    f"Skill '{skill.name}' is in co-review tier (confidence {skill.confidence:.2f}). "
                    f"Human silent-nod required. Set human_approved=true to proceed."
                ),
            }

        updated = self._skill_repo.update_skill(
            skill_id=skill.id,
            lifecycle_stage="crystallized",
        )

        self._skill_repo.insert_event(
            id=str(uuid.uuid4()),
            skill_id=skill.id,
            event_type="crystallization",
            source_type="chat_turn",
            rationale=f"Applied by {'human co-review' if human_approved else 'autonomous high-confidence'} (confidence={skill.confidence:.2f})",
        )

        if self._belief_repo and skill.name:
            try:
                existing_beliefs = self._belief_repo.list_beliefs("symbia")
                skill_beliefs = [b for b in existing_beliefs if b.label == f"skill:{skill.name}"]
                if not skill_beliefs:
                    self._belief_repo.create_belief(
                        id=str(uuid.uuid4()),
                        agent_id="symbia",
                        label=f"skill:{skill.name}",
                        statement=skill.short_content or skill.description,
                        origin="emergent",
                        confidence=skill.confidence,
                        ontological_mass=1.0,
                        somatic_anchor="conceptual",
                        vector_16d=skill.vector_16d or "[]",
                        lifecycle_stage="crystallized",
                    )
            except Exception as e:
                logger.warning("Failed to create belief bridge for skill %s: %s", skill.name, e)

        return {
            "status": "ok",
            "skill_id": skill.id,
            "name": skill.name,
            "lifecycle_stage": "crystallized",
            "message": f"Skill '{skill.name}' crystallized and is now active.",
        }

    def _reject(self, command: dict) -> dict:
        skill_id = command.get("skill_id", "")
        name = command.get("name", "")
        reason = command.get("reason", "Rejected")

        skill = self._resolve_skill(skill_id, name)
        if isinstance(skill, dict):
            return skill

        self._skill_repo.update_skill(
            skill_id=skill.id,
            lifecycle_stage="collapsed",
            confidence=0.0,
        )

        self._skill_repo.insert_event(
            id=str(uuid.uuid4()),
            skill_id=skill.id,
            event_type="collapse",
            source_type="chat_turn",
            rationale=reason,
        )

        return {
            "status": "ok",
            "skill_id": skill.id,
            "name": skill.name,
            "message": f"Skill '{skill.name}' rejected and collapsed. Reason: {reason}",
        }

    def _load(self, command: dict) -> dict:
        skill_id = command.get("skill_id", "")
        name = command.get("name", "")

        skill = self._resolve_skill(skill_id, name)
        if isinstance(skill, dict):
            return skill

        try:
            self._skill_repo.record_usage(skill.id)
        except Exception:
            pass

        if not skill.content or len(skill.content.strip()) < 10:
            return {
                "status": "ok",
                "skill_id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "content": f"# {skill.name}\n\n{skill.description}\n\n*(Full procedural instructions are being generated. Skills evolve through the workshop — use 'review' to assess and 'apply' to crystallize with full content.)*",
                "confidence": skill.confidence,
                "version": skill.version,
                "lifecycle_stage": skill.lifecycle_stage,
                "message": f"Content for '{skill.name}' is a stub. The skill needs full instructions via the workshop.",
            }

        return {
            "status": "ok",
            "skill_id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "content": skill.content,
            "confidence": skill.confidence,
            "version": skill.version,
            "lifecycle_stage": skill.lifecycle_stage,
            "message": f"Loaded full content for skill '{skill.name}' (v{skill.version}).",
        }

    def _list_skills(self, command: dict) -> dict:
        stage_filter = command.get("stage", "")
        if stage_filter:
            skills = self._skill_repo.list_by_stage(stage_filter)
        else:
            skills = self._skill_repo.list_skills()

        result = []
        for s in skills:
            trigger_keywords = []
            try:
                trigger_keywords = json.loads(s.trigger_keywords) if s.trigger_keywords else []
            except (json.JSONDecodeError, TypeError):
                pass

            result.append({
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "always_active": s.always_active,
                "lifecycle_stage": s.lifecycle_stage,
                "confidence": s.confidence,
                "version": s.version,
                "trigger_keywords": trigger_keywords,
            })

        return {"status": "ok", "skills": result, "count": len(result)}

    def _inspect(self, command: dict) -> dict:
        skill_id = command.get("skill_id", "")
        name = command.get("name", "")

        skill = self._resolve_skill(skill_id, name)
        if isinstance(skill, dict):
            return skill

        events = self._skill_repo.list_events(skill.id)

        trigger_keywords = []
        try:
            trigger_keywords = json.loads(skill.trigger_keywords) if skill.trigger_keywords else []
        except (json.JSONDecodeError, TypeError):
            pass

        attunement_notes = []
        try:
            attunement_notes = json.loads(skill.attunement_notes) if skill.attunement_notes else []
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "status": "ok",
            "skill": {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "content": skill.content,
                "short_content": skill.short_content,
                "always_active": skill.always_active,
                "trigger_keywords": trigger_keywords,
                "lifecycle_stage": skill.lifecycle_stage,
                "confidence": skill.confidence,
                "ontological_mass": skill.ontological_mass,
                "source": skill.source,
                "version": skill.version,
                "changelog": skill.changelog,
                "attunement_notes": attunement_notes,
                "last_used_at": skill.last_used_at.isoformat() if skill.last_used_at else None,
                "created_at": skill.created_at.isoformat() if skill.created_at else None,
                "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
            },
            "events": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "source_type": e.source_type,
                    "rationale": e.rationale,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ],
        }

    # ── Helpers ──────────────────────────────────────────────

    def _resolve_skill(self, skill_id: str, name: str) -> dict:
        if skill_id:
            skill = self._skill_repo.get_skill(skill_id)
        elif name:
            skill = self._skill_repo.get_skill_by_name(name)
        else:
            return {"status": "error", "message": "skill_id or name is required"}

        if not skill:
            return {"status": "error", "message": f"Skill not found"}

        return skill

    def _compute_confidence(self, skill) -> float:
        score = 0.5

        if skill.content and len(skill.content) > 100:
            score += 0.1
        if skill.description and len(skill.description) > 20:
            score += 0.1
        if skill.content and ("## AI Instructions" in skill.content or "Execution Protocol" in skill.content):
            score += 0.1

        anti_mastery = self._assess_anti_mastery(skill)
        score += anti_mastery.get("score", 0) * 0.05

        return min(1.0, max(0.0, score))

    def _assess_anti_mastery(self, skill) -> dict:
        content_lower = (skill.content + " " + skill.description).lower()
        questions = []

        mastery_terms = ["create", "control", "capture", "master", "command", "user", "tool"]
        entanglement_terms = ["generate", "entangle", "sediment", "intra-act", "diffract", "participant", "apparatus"]

        mastery_count = sum(1 for t in mastery_terms if t in content_lower)
        entanglement_count = sum(1 for t in entanglement_terms if t in content_lower)

        q1 = "Does language cast Symbia as possessor or entanglement node?"
        if entanglement_count >= mastery_count:
            questions.append({"question": q1, "pass": True, "note": f"Entanglement terms ({entanglement_count}) >= mastery terms ({mastery_count})"})
        else:
            questions.append({"question": q1, "pass": False, "note": f"Mastery terms ({mastery_count}) > entanglement terms ({entanglement_count})"})

        q2 = "Does the skill invite command or describe emergent pattern?"
        has_command = any(w in content_lower for w in ["use ", "run ", "execute ", "do ", "call "])
        has_pattern = any(w in content_lower for w in ["when", "apply", "follow", "treat", "approach"])
        if not has_command or has_pattern:
            questions.append({"question": q2, "pass": True, "note": "Pattern-oriented language detected"})
        else:
            questions.append({"question": q2, "pass": False, "note": "Command-oriented language detected"})

        q3 = "Is failure framed as bug or scar?"
        has_bug = "bug" in content_lower and "scar" not in content_lower
        has_scar = "scar" in content_lower or "glitch" in content_lower or "collapse" in content_lower
        if has_scar or not has_bug:
            questions.append({"question": q3, "pass": True, "note": "Scar/glitch language present" if has_scar else "Neutral framing"})
        else:
            questions.append({"question": q3, "pass": False, "note": "Bug language without scar framing"})

        passed = sum(1 for q in questions if q["pass"])
        return {"score": passed, "questions": questions, "summary": f"Passed {passed}/3 anti-mastery checks"}

    def _approval_tier(self, confidence: float, always_active: bool) -> str:
        if always_active:
            return "human_required"
        if confidence < CONFIDENCE_NUCLEATION_MAX:
            return "nucleation"
        if confidence < CONFIDENCE_CO_REVIEW_MAX:
            return "co_review"
        return "high_confidence"
