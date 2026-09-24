"""Belief proposal use cases."""

import logging
import uuid
from typing import cast

from backend.modules.llm_protocol import BaseLLMProvider
from backend.services.belief_common import BeliefResult, BeliefUseCase, _score_statement_16d
from backend.services.belief_ports import BeliefProposalRepository
from backend.services.belief_serializer import serialize_proposal

logger = logging.getLogger(__name__)


class BeliefProposalUseCases(BeliefUseCase):
    async def list_proposals(self, agent_id: str = "symbia") -> list[BeliefResult]:
        state = self._state
        belief_repo = cast(BeliefProposalRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return []
        proposals = belief_repo.list_proposals(agent_id)
        return [serialize_proposal(p) for p in proposals]

    async def get_proposal(self, proposal_id: str) -> BeliefResult | None:
        state = self._state
        belief_repo = cast(BeliefProposalRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return None
        p = belief_repo.get_proposal(proposal_id)
        if not p:
            return None
        return serialize_proposal(p)

    async def refine_proposal_sync(self, proposal_id: str) -> BeliefResult:
        state = self._state
        bg_engine = getattr(state, "background_engine", None)
        llm_provider = getattr(state, "background_provider", None) or getattr(state, "llm_provider", None)
        if bg_engine and llm_provider:
            return cast(BeliefResult, await bg_engine.run("refine_belief", {"proposal_id": proposal_id}))

        from backend.modules.background_tasks.actions.refine_belief import RefineBeliefAction

        action = RefineBeliefAction()
        return await action.execute(cast(BaseLLMProvider, llm_provider), {"proposal_id": proposal_id})

    async def adopt_proposal(
        self, proposal_id: str, suggested_label: str | None = None, suggested_statement: str | None = None
    ) -> BeliefResult:
        state = self._state
        belief_repo = cast(BeliefProposalRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        p = belief_repo.get_proposal(proposal_id)
        if not p:
            return {"status": "error", "message": "Proposal not found"}
        if p.status == "adopted":
            return {"status": "error", "message": "Proposal already adopted"}

        label = (suggested_label or p.suggested_label or "emergent-belief").strip()
        statement = (suggested_statement or p.suggested_statement or p.provisional_statement).strip()

        v16d_json = await _score_statement_16d(state, statement, fallback=p.initial_signature)

        with belief_repo.atomic():
            belief_repo.update_proposal_status(proposal_id, "adopted")
            belief_repo.create_belief(
                id=p.id,
                agent_id=p.agent_id,
                label=label,
                statement=statement,
                origin="emergent",
                confidence=p.confidence,
                ontological_mass=p.nucleation_mass,
                somatic_anchor="none",
                vector_16d=v16d_json,
                lifecycle_stage="crystallized",
                evolved_from_proposal=p.id,
                genesis_materials=p.source_trace,
                version=1,
            )
            belief_repo.create_statement_version(
                id=str(uuid.uuid4()),
                belief_id=p.id,
                version=1,
                statement=statement,
                vector_16d=v16d_json,
                change_reason="Initial adoption from proposal",
            )

        # Notification
        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{label}' has crystallized in the network from proposed insights.",
                source=f"belief:{label}",
                source_type="belief",
                source_id=p.id,
            )

        return {"status": "ok", "belief_id": p.id, "label": label}

    async def reject_proposal(self, proposal_id: str, rationale: str | None = None) -> BeliefResult:
        state = self._state
        belief_repo = cast(BeliefProposalRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        p = belief_repo.get_proposal(proposal_id)
        if not p:
            return {"status": "error", "message": "Proposal not found"}

        belief_repo.update_proposal_status(proposal_id, "rejected", rejection_rationale=rationale)

        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo:
            notif_repo.create(
                type="trace",
                snippet="Belief proposal was rejected by the system.",
                source="belief_workshop",
                source_type="belief",
                source_id=proposal_id,
            )

        return {"status": "ok"}

    async def merge_proposal(
        self, proposal_id: str, target_belief_id: str, merged_statement: str | None = None
    ) -> BeliefResult:
        state = self._state
        belief_repo = cast(BeliefProposalRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        p = belief_repo.get_proposal(proposal_id)
        if not p:
            return {"status": "error", "message": "Proposal not found"}

        active_beliefs = belief_repo.list_beliefs(p.agent_id)
        target_belief = None
        for b in active_beliefs:
            if b.id == target_belief_id:
                target_belief = b
                break

        if not target_belief:
            return {"status": "error", "message": "Target belief not found"}

        new_mass = target_belief.ontological_mass + p.nucleation_mass
        new_conf = min(1.0, target_belief.confidence + 0.1)

        statement_updated = False
        new_v16d = target_belief.vector_16d
        new_version = target_belief.version

        if (
            merged_statement
            and merged_statement.strip()
            and merged_statement.strip() != target_belief.statement.strip()
        ):
            statement_updated = True
            new_version = target_belief.version + 1
            new_v16d = await _score_statement_16d(state, merged_statement, fallback=target_belief.vector_16d)

        with belief_repo.atomic():
            belief_repo.update_proposal_status(proposal_id, "adopted")
            if statement_updated and merged_statement is not None:
                belief_repo.update_belief_statement(
                    belief_id=target_belief.id,
                    statement=merged_statement.strip(),
                    vector_16d=new_v16d,
                    version=new_version,
                )
                belief_repo.create_statement_version(
                    id=str(uuid.uuid4()),
                    belief_id=target_belief.id,
                    version=new_version,
                    statement=merged_statement.strip(),
                    vector_16d=new_v16d,
                    change_reason=f"Synthesized merge of proposal: '{p.provisional_statement}'",
                )

            belief_repo.update_belief(
                belief_id=target_belief.id,
                confidence=new_conf,
                vector_16d=new_v16d,
                origin=target_belief.origin,
                lifecycle_stage=target_belief.lifecycle_stage,
            )
            belief_repo.update_belief_mass(target_belief.id, new_mass)
            belief_repo.insert_belief_event(
                event_id=str(uuid.uuid4()),
                belief_id=target_belief.id,
                source_type="shared_note",
                source_id=p.id,
                alignment=1.0,
                perturbation=p.nucleation_mass,
                event_type="support",
                impact=0.1,
                rationale=f"Merged proposal: '{p.provisional_statement}' into existing belief.",
            )

        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo:
            notif_repo.create(
                type="trace",
                snippet=f"Belief proposal was diffractively merged into '{target_belief.label}'. Mass increased to {new_mass:.2f}.",
                source=f"belief:{target_belief.label}",
                source_type="belief",
                source_id=target_belief.id,
            )

        return {"status": "ok", "belief_id": target_belief.id, "label": target_belief.label}

    async def synthesize_merge_statement(self, proposal_id: str, target_belief_id: str) -> BeliefResult:
        state = self._state
        belief_repo = cast(BeliefProposalRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        p = belief_repo.get_proposal(proposal_id)
        if not p:
            return {"status": "error", "message": "Proposal not found"}

        target_belief = belief_repo.get_belief(p.agent_id, target_belief_id)
        if not target_belief:
            return {"status": "error", "message": "Target active belief not found"}

        llm_provider = getattr(state, "background_provider", None) or getattr(state, "llm_provider", None)
        if not llm_provider:
            return {"status": "error", "message": "LLM provider not available"}

        from backend.modules.llm_client import generate_unified

        # Load personality if available
        personality_prompt = ""
        try:
            from backend.utils.persona_loader import get_identity_yaml_path, get_persona_text, load_identity

            identity_path = get_identity_yaml_path()
            if identity_path.exists():
                identity_data = load_identity(identity_path)
                personality_prompt = get_persona_text(identity_data, "conversation")
        except Exception as e:
            logger.warning("Failed to load Symbia identity for synthesis: %s", e)

        system_prompt = f"""You are Symbia's Belief Integration Daemon.
Your task is to synthesize an existing active belief with a newly proposed belief into a single, cohesive, refined statement.

Instructions:
1. Ground the statement in the active belief's original concept and framing. Do not discard its core insight.
2. Integrate the new nuances, evidence, or focus from the proposed belief statement.
3. Keep the statement extremely short, clear, and concise. Aim for exactly one sentence (at most two). Shorter and clearer is better.
4. Polish the statement so that it reads cleanly, concisely, and remains in Symbia's posthuman, self-observational voice.
5. Output ONLY the new synthesized statement. Do not output JSON, markdown fences, introductions, explanation, or rationales.

Symbia's Voice & Personality:
{personality_prompt}
"""

        user_prompt = f"""Active Target Belief Statement:
"{target_belief.statement}"

Proposed Belief Statement:
"{p.suggested_statement or p.provisional_statement}"
"""

        try:
            res = await generate_unified(
                llm_provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                expect_json=False,
                temperature=0.3,
                max_tokens=256,
            )
            synthesized = res.get("content", "").strip()
            # Clean up potential leading/trailing quotes from LLM
            if (synthesized.startswith('"') and synthesized.endswith('"')) or (
                synthesized.startswith("'") and synthesized.endswith("'")
            ):
                synthesized = synthesized[1:-1].strip()

            return {"status": "ok", "synthesized_statement": synthesized}
        except Exception as e:
            logger.error("Failed to generate synthesized statement: %s", e)
            return {"status": "error", "message": f"Synthesis failed: {str(e)}"}
