from pathlib import Path
import yaml
import json
import logging
from typing import Optional

from backend.config import load_config
from backend.storage.database import get_db_path
from backend.storage.repository import BeliefRepository
from backend.modules.llm_client import BaseLLMProvider, generate_unified

from ..base import BackgroundAction

logger = logging.getLogger(__name__)


class RefineBeliefAction(BackgroundAction):
    _prompt_file = "refine_belief.yaml"

    @property
    def action_type(self) -> str:
        return "refine_belief"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        proposal_id = payload.get("proposal_id")
        if not proposal_id and isinstance(payload.get("context"), dict):
            proposal_id = payload["context"].get("proposal_id")

        if not proposal_id:
            return {"content": "", "model": "", "error": "No proposal_id provided"}

        # 1. Resolve database path and repositories
        config = load_config()
        db_path = str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))
        belief_repo = BeliefRepository(db_path)

        # 2. Retrieve proposal
        proposal = belief_repo.get_proposal(proposal_id)
        if not proposal:
            return {"content": "", "model": "", "error": f"Proposal not found for id {proposal_id}"}

        # 3. Query list of existing active/crystallized/senescent/accretion beliefs
        try:
            active_beliefs = belief_repo.list_beliefs(agent_id=proposal.agent_id)
            # Filter to non-collapsed and non-faded
            active_beliefs_list = [
                {"id": b.id, "label": b.label, "statement": b.statement}
                for b in active_beliefs
                if b.lifecycle_stage in ("crystallized", "senescence", "accretion")
            ]
        except Exception as e:
            logger.warning("Failed to fetch active beliefs: %s", e)
            active_beliefs_list = []

        # 4. Load Symbia core personality
        personality_prompt = ""
        try:
            from backend.utils.persona_loader import get_identity_yaml_path, load_identity, get_persona_text
            identity_path = get_identity_yaml_path()
            if identity_path.exists():
                identity_data = load_identity(identity_path)
                personality_prompt = get_persona_text(identity_data, "conversation")
        except Exception as e:
            logger.warning("Failed to load Symbia identity: %s", e)

        # 5. Assemble system prompt
        action_system_prompt = self.system_prompt()
        assembled_system_prompt = f"{action_system_prompt}\n\n[SYMBIA CORE PERSONALITY & STYLE]:\n{personality_prompt}"

        # 6. Formulate user prompt
        user_prompt = f"""Proposed Belief Statement:
\"\"\"
{proposal.provisional_statement}
\"\"\"

Active beliefs already in Symbia's database:
{json.dumps(active_beliefs_list, indent=2)}
"""

        params = {**self.default_params(), **payload.get("params", {})}

        # 7. Call LLM
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
                "decision": "error",
                "error": "Failed to generate valid JSON decision",
                "content": content,
                "model": model_used
            }

        suggested_label = data.get("suggested_label", "").strip()
        suggested_statement = data.get("suggested_statement", "").strip()
        potential_merge_target = data.get("potential_merge_target")

        # Resolve target label or name to ID if needed
        resolved_target_id = None
        if potential_merge_target:
            target_str = str(potential_merge_target).strip()
            for b in active_beliefs:
                if b.id == target_str or b.label.lower() == target_str.lower():
                    resolved_target_id = b.id
                    break

        # Math fallback check: if no target ID resolved, check cosine similarities
        from backend.modules.belief_engine import parse_vector_16d
        from backend.utils.similarity import cosine_similarity
        prop_vec = parse_vector_16d(proposal.initial_signature)
        if prop_vec is not None:
            best_sim = -1.0
            best_id = None
            for b in active_beliefs:
                if b.lifecycle_stage in ("crystallized", "senescence", "accretion"):
                    b_vec = parse_vector_16d(b.vector_16d)
                    if b_vec is not None:
                        sim = cosine_similarity(prop_vec, b_vec)
                        if sim > best_sim:
                            best_sim = sim
                            best_id = b.id
            if best_sim >= 0.70 and not resolved_target_id:
                resolved_target_id = best_id
                logger.info(f"Mathematical overlap threshold reached (similarity={best_sim:.2f}) for belief ID {best_id}. Auto-nominated target.")

        # Update the proposal with daemon suggestions
        belief_repo.update_proposal_suggestions(
            proposal_id=proposal_id,
            suggested_label=suggested_label,
            suggested_statement=suggested_statement,
            potential_merge_target=resolved_target_id,
            status="refined"
        )
        if data.get("rationale"):
            belief_repo.update_proposal_symbia_reflection(
                proposal_id=proposal_id,
                symbia_reflection=data.get("rationale").strip()
            )
        logger.info(f"Successfully refined belief proposal {proposal_id} with label: {suggested_label}")

        return {
            "status": "refined",
            "suggested_label": suggested_label,
            "suggested_statement": suggested_statement,
            "potential_merge_target": resolved_target_id,
            "model": model_used
        }
