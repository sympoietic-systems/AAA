import logging
import re
import uuid
import json
from datetime import datetime, timezone

from backend.modules.structural_engine import LexiconScorer

logger = logging.getLogger(__name__)


class SkillMetabolismMixin:
    """Handles closed-loop autopoietic feedback for skill updates and self-revision."""

    async def run_skill_metabolism(self) -> None:
        """Evaluate active crystallized skills against feedback loops and run self-revision if threshold exceeded."""
        skill_repo = getattr(self, "skill_repo", None)
        belief_repo = getattr(self, "belief_repo", None)
        message_repo = getattr(self, "message_repo", None)
        bg_engine = getattr(self, "background_engine", None)

        if not skill_repo or not belief_repo or not message_repo or not bg_engine:
            return

        # 1. Fetch active skills
        try:
            skills = skill_repo.list_skills()
        except Exception as e:
            logger.warning("Failed to fetch skills in metabolism daemon: %s", e)
            return

        active_skills = [s for s in skills if s.lifecycle_stage == "crystallized"]
        if not active_skills:
            return

        # 2. Query recent conversation logs for any inline aaa-note or scar-fold tags
        try:
            recent_msgs = message_repo.get_recent(limit=50)
        except Exception as e:
            logger.warning("Failed to fetch recent messages in metabolism daemon: %s", e)
            recent_msgs = []

        # Parse annotations referencing any skill
        note_pattern = re.compile(r'<aaa-note\s+[^>]*comment="([^"]+)"[^>]*context="skill:([^"]+)"[^>]*>', re.IGNORECASE)
        scar_fold_pattern = re.compile(r'<scar-fold\s+[^>]*skill="([^"]+)"[^>]*>(.*?)</scar-fold>', re.IGNORECASE)

        # Collect improvisation comments by skill name
        improvisations_by_skill = {}
        for msg in recent_msgs:
            if not msg.content:
                continue
            # Scan for aaa-note
            for comment, skill_name in note_pattern.findall(msg.content):
                sk_name = skill_name.strip()
                if sk_name not in improvisations_by_skill:
                    improvisations_by_skill[sk_name] = []
                improvisations_by_skill[sk_name].append(comment.strip())
            
            # Scan for scar-fold
            for skill_name, comment in scar_fold_pattern.findall(msg.content):
                sk_name = skill_name.strip()
                if sk_name not in improvisations_by_skill:
                    improvisations_by_skill[sk_name] = []
                improvisations_by_skill[sk_name].append(comment.strip())

        # 3. Process each crystallized skill
        for skill in active_skills:
            s_belief = 0.0
            s_sediment = 0.0
            s_performance = 0.0
            
            # B. Belief-Tectonic Shift Signal
            try:
                skill_beliefs = belief_repo.list_beliefs("symbia")
            except Exception:
                skill_beliefs = []

            belief = next((b for b in skill_beliefs if b.label == f"skill:{skill.name}"), None)
            
            belief_status_info = "No linked belief found"
            if belief:
                belief_status_info = f"linked belief '{belief.label}' (confidence: {belief.confidence:.2f}, stage: {belief.lifecycle_stage})"
                if belief.lifecycle_stage == "collapsed":
                    s_belief = 1.0
                else:
                    conf_diff = skill.confidence - belief.confidence
                    if conf_diff >= 0.3:
                        s_belief = 0.8
                    elif conf_diff > 0:
                        s_belief = conf_diff * 2.0  # proportional signal

            # C. Usage-Sediment Excess Signal
            notes = improvisations_by_skill.get(skill.name, [])
            notes_str = ""
            if notes:
                s_sediment = min(1.0, len(notes) * 0.3)
                notes_str = "\n".join(f"- {n}" for n in set(notes))

            # A. Performance-Glitch / Decay Signal
            if skill.confidence < 0.5:
                s_performance = 0.3

            # Cumulative Signal Index
            cumulative_signal = max(s_belief, s_sediment, s_performance)
            
            if cumulative_signal < 0.6:
                continue

            logger.info("Skill '%s' metabolic threshold exceeded: S=%.2f. Triggering self-revision.", skill.name, cumulative_signal)
            
            # Run self-revision pipeline
            try:
                # 1. Diffractive Patching: Call the metabolize_skill background action
                payload = {
                    "skill_name": skill.name,
                    "skill_content": skill.content,
                    "belief_info": belief_status_info,
                    "notes_info": notes_str if notes_str else "No direct friction notes. Self-correcting based on belief drift/confidence decay.",
                }
                
                result = await bg_engine.run("metabolize_skill", payload)
                
                data = result.get("json_data")
                if not data:
                    logger.warning("Metabolize action for '%s' returned empty or invalid JSON", skill.name)
                    continue

                refined_content = data.get("content", "").strip()
                refined_description = data.get("description", skill.description).strip()
                refined_trigger_keywords = data.get("trigger_keywords", [])
                changelog = data.get("changelog", f"Auto-metabolized on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")

                if not refined_content:
                    logger.warning("Empty content generated for metabolized skill '%s'", skill.name)
                    continue

                # 2. Heuristic validation (Anti-Mastery & Constitutional)
                prohibited_words = ["user", "tool", "control", "master"]
                content_lower = refined_content.lower()
                violations = [w for w in prohibited_words if w in content_lower]
                if violations:
                    logger.warning("Skill '%s' auto-revision rejected due to anti-mastery violation. Contained prohibited words: %s", skill.name, violations)
                    try:
                        error_repo = getattr(self.app_state, "error_repo", None)
                        if error_repo:
                            error_repo.log_error(
                                module="skill_metabolism",
                                error_type="anti_mastery_violation",
                                error_message=f"Self-revision of skill '{skill.name}' contained prohibited words: {violations}",
                                traceback=None,
                                context=refined_content[:500]
                            )
                    except Exception:
                        pass
                    continue

                # 3. Apply changes and save version history
                vector_16d = skill.vector_16d
                try:
                    scorer = LexiconScorer()
                    v16d = scorer.score(refined_content)
                    vector_16d = json.dumps({"v16d": v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)})
                except Exception as se:
                    logger.warning("Failed to score updated skill vector in metabolism: %s", se)

                new_version = skill.version + 1
                
                skill_repo.update_skill(
                    skill_id=skill.id,
                    content=refined_content,
                    description=refined_description,
                    trigger_keywords=json.dumps(refined_trigger_keywords),
                    vector_16d=vector_16d,
                    version=new_version,
                    changelog=changelog,
                    version_source="auto_metabolism"
                )
                
                skill_repo.insert_event(
                    id=str(uuid.uuid4()),
                    skill_id=skill.id,
                    event_type="revision",
                    source_type="auto_metabolism",
                    rationale=changelog,
                )

                logger.info("Skill '%s' successfully self-revised to version %d via metabolism daemon.", skill.name, new_version)

            except Exception as metabolism_error:
                logger.exception("Failed self-revision pipeline for skill '%s': %s", skill.name, metabolism_error)
