import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BeliefService:
    def __init__(self, state):
        self._state = state

    async def get_beliefs(self, conversation_id: Optional[str] = None, agent_id: str = "symbia") -> dict:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        engine = getattr(state, "belief_metabolism", None)
        if not belief_repo:
            return {"beliefs": [], "proto_beliefs": [], "ghosts": [], "somatic": None,
                    "attractor_window": [], "spectral_margin": [], "ecosystem": None}

        raw_beliefs = belief_repo.list_beliefs(agent_id)
        beliefs_list = []
        proto_beliefs_list = []
        ghosts_list = []

        for b in raw_beliefs:
            events = belief_repo.get_events_for_belief(b.id)
            if b.ontological_mass >= 1.5:
                cat = "foundational"
            elif b.ontological_mass >= 1.2:
                cat = "ontological"
            else:
                cat = "methodological"

            belief_data = {
                "id": b.id,
                "label": b.label,
                "statement": b.statement,
                "category": cat,
                "confidence": b.confidence,
                "ontological_mass": b.ontological_mass,
                "version": b.version,
                "vector_16d": b.vector_16d,
                "origin": b.origin,
                "lifecycle_stage": b.lifecycle_stage,
                "last_reinforced_at": b.last_reinforced_at.isoformat() if b.last_reinforced_at else None,
                "updated_at": b.updated_at.isoformat() if b.updated_at else None,
                "events": [
                    {
                        "id": e.id, "timestamp": e.timestamp.isoformat(),
                        "source_id": e.source_id, "source_type": e.source_type,
                        "delta_confidence": e.impact_score, "description": e.rationale,
                    }
                    for e in events
                ],
            }

            stage = b.lifecycle_stage
            if stage in ("crystallized", "senescence"):
                beliefs_list.append(belief_data)
            elif stage in ("nucleation", "accretion"):
                proto_beliefs_list.append(belief_data)
            elif stage == "collapsed":
                ghosts_list.append(belief_data)

        somatic_state = None
        attractor_window = []
        spectral_margin = []

        if conversation_id:
            somatic = belief_repo.get_conversation_somatic_state(conversation_id)
            if somatic:
                somatic_state = {
                    "somatic_reservoir_ad": somatic.get("somatic_reservoir_ad", 0.0),
                    "matrix_warping": somatic.get("matrix_warping", 0.0),
                    "immunological_directive_active": bool(somatic.get("immunological_directive_active", 0)),
                }

                if engine:
                    try:
                        active = [b for b in raw_beliefs if b.lifecycle_stage not in ("collapsed", "faded") and b.confidence >= 0.20]
                        collapsed = [b for b in raw_beliefs if b.lifecycle_stage in ("collapsed", "faded") or b.confidence < 0.20]

                        if active:
                            slot1 = max(active, key=lambda b: b.ontological_mass)
                            attractors = [slot1]
                            stressed = [b for b in active if b.confidence < 0.50]
                            slot2 = min(stressed, key=lambda b: b.confidence) if stressed else None
                            if slot2:
                                attractors.append(slot2)
                            remaining = [b for b in active if b.id != slot1.id and b.id != (slot2.id if slot2 else None)]
                            if remaining:
                                attractors.append(remaining[0])
                            attractor_window = [a.label for a in attractors]

                        spectral_margin = [b.label for b in collapsed]
                    except Exception as e:
                        logger.error("Error computing UI attractor window: %s", e)

        ecosystem = None
        if engine:
            try:
                ecosystem = await engine.compute_ecosystem_health(agent_id)
            except Exception as e:
                logger.error("Error computing ecosystem health: %s", e)

        return {
            "beliefs": beliefs_list,
            "proto_beliefs": proto_beliefs_list,
            "ghosts": ghosts_list,
            "somatic": somatic_state,
            "attractor_window": attractor_window,
            "spectral_margin": spectral_margin,
            "ecosystem": ecosystem,
        }

    async def list_proposals(self, agent_id: str = "symbia") -> list[dict]:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        if not belief_repo:
            return []
        
        import json
        proposals = belief_repo.list_proposals(agent_id)
        return [
            {
                "id": p.id,
                "agent_id": p.agent_id,
                "provisional_statement": p.provisional_statement,
                "source_trace": json.loads(p.source_trace) if p.source_trace else [],
                "initial_signature": json.loads(p.initial_signature) if p.initial_signature else [],
                "nucleation_mass": p.nucleation_mass,
                "confidence": p.confidence,
                "status": p.status,
                "suggested_label": p.suggested_label,
                "suggested_statement": p.suggested_statement,
                "potential_merge_target": p.potential_merge_target,
                "symbia_reflection": p.symbia_reflection,
                "symbia_friction_rationale": p.symbia_friction_rationale,
                "rejection_rationale": p.rejection_rationale,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in proposals
        ]

    async def get_proposal(self, proposal_id: str) -> Optional[dict]:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        if not belief_repo:
            return None
        p = belief_repo.get_proposal(proposal_id)
        if not p:
            return None
        import json
        return {
            "id": p.id,
            "agent_id": p.agent_id,
            "provisional_statement": p.provisional_statement,
            "source_trace": json.loads(p.source_trace) if p.source_trace else [],
            "initial_signature": json.loads(p.initial_signature) if p.initial_signature else [],
            "nucleation_mass": p.nucleation_mass,
            "confidence": p.confidence,
            "status": p.status,
            "suggested_label": p.suggested_label,
            "suggested_statement": p.suggested_statement,
            "potential_merge_target": p.potential_merge_target,
            "symbia_reflection": p.symbia_reflection,
            "symbia_friction_rationale": p.symbia_friction_rationale,
            "rejection_rationale": p.rejection_rationale,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }

    async def refine_proposal_sync(self, proposal_id: str) -> dict:
        state = self._state
        bg_engine = getattr(state, "background_engine", None)
        llm_provider = getattr(state, "background_provider", None) or getattr(state, "llm_provider", None)
        if not bg_engine or not llm_provider:
            from backend.modules.background_tasks.actions.refine_belief import RefineBeliefAction
            action = RefineBeliefAction()
            return await action.execute(llm_provider, {"proposal_id": proposal_id})
        
        task_id = await bg_engine.dispatch("refine_belief", {"proposal_id": proposal_id})
        res = await bg_engine.wait_for_task(task_id)
        return res

    async def adopt_proposal(self, proposal_id: str, suggested_label: Optional[str] = None, suggested_statement: Optional[str] = None) -> dict:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        p = belief_repo.get_proposal(proposal_id)
        if not p:
            return {"status": "error", "message": "Proposal not found"}
        if p.status == "adopted":
            return {"status": "error", "message": "Proposal already adopted"}

        label = (suggested_label or p.suggested_label or "emergent-belief").strip()
        statement = (suggested_statement or p.suggested_statement or p.provisional_statement).strip()

        # Update proposal status
        belief_repo.update_proposal_status(proposal_id, "adopted")

        import uuid
        import json
        from backend.modules.structural_engine import LexiconScorer
        try:
            scorer = LexiconScorer()
            v16d = scorer.score(statement)
            v16d_json = json.dumps({"v16d": v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)})
        except Exception:
            v16d_json = p.initial_signature

        # Create belief node
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
            version=1
        )

        # Create statement version
        ver_id = str(uuid.uuid4())
        belief_repo.create_statement_version(
            id=ver_id,
            belief_id=p.id,
            version=1,
            statement=statement,
            vector_16d=v16d_json,
            change_reason="Initial adoption from proposal"
        )

        # Notification
        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{label}' has crystallized in the network from proposed insights.",
                source=f"belief:{label}"
            )

        return {"status": "ok", "belief_id": p.id, "label": label}

    async def reject_proposal(self, proposal_id: str, rationale: Optional[str] = None) -> dict:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
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
                snippet=f"Belief proposal was rejected by the system.",
                source="belief_workshop"
            )

        return {"status": "ok"}

    async def merge_proposal(self, proposal_id: str, target_belief_id: str) -> dict:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
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

        belief_repo.update_proposal_status(proposal_id, "adopted")

        new_mass = target_belief.ontological_mass + p.nucleation_mass
        new_conf = min(1.0, target_belief.confidence + 0.1)
        belief_repo.update_belief(
            belief_id=target_belief.id,
            confidence=new_conf,
            vector_16d=target_belief.vector_16d,
            origin=target_belief.origin,
            lifecycle_stage=target_belief.lifecycle_stage
        )
        belief_repo.update_belief_mass(target_belief.id, new_mass)

        import uuid
        belief_repo.insert_belief_event(
            event_id=str(uuid.uuid4()),
            belief_id=target_belief.id,
            source_type="shared_note",
            source_id=p.id,
            alignment=1.0,
            perturbation=p.nucleation_mass,
            event_type="support",
            impact=0.1,
            rationale=f"Merged proposal: '{p.provisional_statement}' into existing belief."
        )

        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo:
            notif_repo.create(
                type="trace",
                snippet=f"Belief proposal was diffractively merged into '{target_belief.label}'. Mass increased to {new_mass:.2f}.",
                source=f"belief:{target_belief.label}"
            )

        return {"status": "ok", "belief_id": target_belief.id, "label": target_belief.label}

    async def update_belief_statement(self, belief_id: str, statement: str, change_reason: Optional[str] = None) -> dict:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        active_beliefs = belief_repo.list_beliefs("symbia")
        target_belief = None
        for b in active_beliefs:
            if b.id == belief_id:
                target_belief = b
                break
        
        if not target_belief:
            return {"status": "error", "message": "Belief not found"}

        import uuid
        import json
        from backend.modules.structural_engine import LexiconScorer
        from backend.modules.belief_engine import parse_vector_16d, compute_cosine_similarity

        try:
            scorer = LexiconScorer()
            v16d = scorer.score(statement)
            new_v16d_json = json.dumps({"v16d": v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)})
        except Exception as e:
            return {"status": "error", "message": f"Failed to score statement: {str(e)}"}

        # Update belief statement and bump version
        new_version = target_belief.version + 1
        belief_repo.update_belief_statement(
            belief_id=target_belief.id,
            statement=statement,
            vector_16d=new_v16d_json,
            version=new_version
        )

        # Archive new statement version
        ver_id = str(uuid.uuid4())
        belief_repo.create_statement_version(
            id=ver_id,
            belief_id=target_belief.id,
            version=new_version,
            statement=statement,
            vector_16d=new_v16d_json,
            change_reason=change_reason or "Statement edited by user/agent"
        )

        old_vec = parse_vector_16d(target_belief.vector_16d)
        new_vec = parse_vector_16d(new_v16d_json)
        
        speciation_triggered = False
        if old_vec is not None and new_vec is not None:
            sim = compute_cosine_similarity(old_vec, new_vec)
            dist = 1.0 - sim
            if dist > 0.4:
                speciation_triggered = True
                notif_repo = getattr(state, "notification_repo", None)
                if notif_repo:
                    notif_repo.create(
                        type="glitch",
                        snippet=f"Speciation Alert: Belief '{target_belief.label}' has drifted significantly (distance={dist:.2f}). Consider forking into multiple concepts.",
                        source=f"belief:{target_belief.label}"
                    )

        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo and not speciation_triggered:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{target_belief.label}' updated statement to version {new_version}.",
                source=f"belief:{target_belief.label}"
            )

        return {
            "status": "ok",
            "belief_id": target_belief.id,
            "version": new_version,
            "speciation_alert": speciation_triggered
        }

    async def get_statement_versions(self, belief_id: str) -> list[dict]:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        if not belief_repo:
            return []
        
        import json
        versions = belief_repo.list_statement_versions(belief_id)
        return [
            {
                "id": v.id,
                "belief_id": v.belief_id,
                "version": v.version,
                "statement": v.statement,
                "vector_16d": json.loads(v.vector_16d) if v.vector_16d else [],
                "change_reason": v.change_reason,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

    async def create_new_belief(
        self,
        label: str,
        statement: str,
        confidence: float = 0.5,
        ontological_mass: float = 0.5,
        lifecycle_stage: str = "crystallized",
        agent_id: str = "symbia",
    ) -> dict:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        import uuid
        import json
        from backend.modules.structural_engine import LexiconScorer
        
        belief_id = str(uuid.uuid4())
        
        # 1. Compute 16D vector
        try:
            scorer = LexiconScorer()
            v16d = scorer.score(statement)
            v16d_json = json.dumps({"v16d": v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)})
        except Exception as e:
            return {"status": "error", "message": f"Failed to score statement: {str(e)}"}

        # 2. Save in database (initial version is 1)
        belief_repo.create_belief(
            id=belief_id,
            agent_id=agent_id,
            label=label,
            statement=statement,
            origin="authored",
            confidence=confidence,
            ontological_mass=ontological_mass,
            somatic_anchor="conceptual",
            vector_16d=v16d_json,
            lifecycle_stage=lifecycle_stage,
        )

        # 3. Create initial statement version record
        belief_repo.create_statement_version(
            id=str(uuid.uuid4()),
            belief_id=belief_id,
            version=1,
            statement=statement,
            vector_16d=v16d_json,
            change_reason="Created manually via Agent FLUX API",
        )

        # 4. Log event
        try:
            belief_repo.insert_belief_event(
                event_id=str(uuid.uuid4()),
                belief_id=belief_id,
                source_type="user_assertion",
                source_id=None,
                alignment=1.0,
                perturbation=1.0,
                event_type="emergence",
                impact=ontological_mass,
                rationale="Created manually via Agent FLUX API",
            )
        except Exception as e:
            logger.warning("Failed to insert event for belief creation: %s", e)

        # 5. Log notification
        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{label}' was manually created.",
                source=f"belief:{label}"
            )

        return {"status": "ok", "belief_id": belief_id, "label": label}

    async def update_belief_details(
        self,
        belief_id: str,
        label: str,
        statement: str,
        confidence: float,
        ontological_mass: float,
        lifecycle_stage: str,
    ) -> dict:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        # Find existing belief
        target_belief = belief_repo.get_belief("symbia", belief_id)
        if not target_belief:
            return {"status": "error", "message": "Belief not found"}

        import uuid
        import json
        from backend.modules.structural_engine import LexiconScorer
        from backend.modules.belief_engine import parse_vector_16d, compute_cosine_similarity

        # 1. Compute 16D vector
        try:
            scorer = LexiconScorer()
            v16d = scorer.score(statement)
            new_v16d_json = json.dumps({"v16d": v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)})
        except Exception as e:
            return {"status": "error", "message": f"Failed to score statement: {str(e)}"}

        statement_changed = (target_belief.statement != statement)
        new_version = target_belief.version
        speciation_triggered = False

        if statement_changed:
            new_version = target_belief.version + 1
            # Archive new statement version
            belief_repo.create_statement_version(
                id=str(uuid.uuid4()),
                belief_id=target_belief.id,
                version=new_version,
                statement=statement,
                vector_16d=new_v16d_json,
                change_reason="Statement edited via Agent FLUX API",
            )

            # Check speciation
            old_vec = parse_vector_16d(target_belief.vector_16d)
            new_vec = parse_vector_16d(new_v16d_json)
            if old_vec is not None and new_vec is not None:
                sim = compute_cosine_similarity(old_vec, new_vec)
                dist = 1.0 - sim
                if dist > 0.4:
                    speciation_triggered = True
                    notif_repo = getattr(state, "notification_repo", None)
                    if notif_repo:
                        notif_repo.create(
                            type="glitch",
                            snippet=f"Speciation Alert: Belief '{label}' has drifted significantly (distance={dist:.2f}) after edit.",
                            source=f"belief:{label}"
                        )

        # 2. Save in database
        belief_repo.update_belief_details(
            belief_id=belief_id,
            label=label,
            statement=statement,
            confidence=confidence,
            ontological_mass=ontological_mass,
            lifecycle_stage=lifecycle_stage,
            vector_16d=new_v16d_json,
            version=new_version,
        )

        # 3. Log event
        try:
            belief_repo.insert_belief_event(
                event_id=str(uuid.uuid4()),
                belief_id=belief_id,
                source_type="user_assertion",
                source_id=None,
                alignment=1.0,
                perturbation=0.5,
                event_type="revision",
                impact=0.1,
                rationale="Updated details via Agent FLUX API",
            )
        except Exception as e:
            logger.warning("Failed to insert event for belief update: %s", e)

        # 4. Log notification
        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo and not speciation_triggered:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{label}' details were updated.",
                source=f"belief:{label}"
            )

        return {
            "status": "ok",
            "belief_id": belief_id,
            "version": new_version,
            "speciation_alert": speciation_triggered
        }

    async def delete_belief(self, belief_id: str) -> dict:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        # Retrieve the belief to verify it exists
        target_belief = belief_repo.get_belief("symbia", belief_id)
        if not target_belief:
            return {"status": "error", "message": "Belief not found"}

        label = target_belief.label
        belief_repo.delete_belief(belief_id)

        # Log notification
        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{label}' was manually deleted.",
                source=f"belief:{label}"
            )

        return {"status": "ok", "message": f"Belief {belief_id} deleted"}

    async def revert_belief_version(self, belief_id: str, version: int) -> dict:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        # Fetch the version from DB
        version_data = belief_repo.get_statement_version(belief_id, version)
        if not version_data:
            return {"status": "error", "message": f"Version {version} for belief {belief_id} not found"}

        # Retrieve the current belief
        target_belief = belief_repo.get_belief("symbia", belief_id)
        if not target_belief:
            return {"status": "error", "message": "Belief not found"}

        import uuid
        from backend.modules.belief_engine import parse_vector_16d, compute_cosine_similarity

        label = target_belief.label
        statement = version_data.statement
        vector_16d_str = version_data.vector_16d

        new_version = target_belief.version + 1

        # Check speciation
        speciation_triggered = False
        old_vec = parse_vector_16d(target_belief.vector_16d)
        new_vec = parse_vector_16d(vector_16d_str)
        if old_vec is not None and new_vec is not None:
            sim = compute_cosine_similarity(old_vec, new_vec)
            dist = 1.0 - sim
            if dist > 0.4:
                speciation_triggered = True
                notif_repo = getattr(state, "notification_repo", None)
                if notif_repo:
                    notif_repo.create(
                        type="glitch",
                        snippet=f"Speciation Alert: Belief '{label}' has drifted significantly (distance={dist:.2f}) after reverting to version {version}.",
                        source=f"belief:{label}"
                    )

        # Archive new statement version
        belief_repo.create_statement_version(
            id=str(uuid.uuid4()),
            belief_id=belief_id,
            version=new_version,
            statement=statement,
            vector_16d=vector_16d_str,
            change_reason=f"Reverted to version {version}",
        )

        # Save in database
        belief_repo.update_belief_details(
            belief_id=belief_id,
            label=label,
            statement=statement,
            confidence=target_belief.confidence,
            ontological_mass=target_belief.ontological_mass,
            lifecycle_stage=target_belief.lifecycle_stage,
            vector_16d=vector_16d_str,
            version=new_version,
        )

        # Log event
        try:
            belief_repo.insert_belief_event(
                event_id=str(uuid.uuid4()),
                belief_id=belief_id,
                source_type="user_assertion",
                source_id=None,
                alignment=1.0,
                perturbation=0.5,
                event_type="revision",
                impact=0.1,
                rationale=f"Reverted statement to version {version} via Agent FLUX API",
            )
        except Exception as e:
            logger.warning("Failed to insert event for belief revert: %s", e)

        # Log notification
        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo and not speciation_triggered:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{label}' reverted statement to version {version}.",
                source=f"belief:{label}"
            )

        return {
            "status": "ok",
            "belief_id": belief_id,
            "version": new_version,
            "speciation_alert": speciation_triggered
        }
