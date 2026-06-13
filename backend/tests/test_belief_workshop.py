import sys
import os
import json
import sqlite3
import uuid
from pathlib import Path
import pytest

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import BeliefRepository, NotificationRepository
from backend.services.belief import BeliefService
from backend.storage.models import BeliefProposal, BeliefStatementVersion

class MockState:
    def __init__(self, db_path):
        self.belief_repo = BeliefRepository(db_path)
        self.notification_repo = NotificationRepository(db_path)


def test_belief_proposal_crud_and_service():
    db_path = str(get_db_path("data/aaa_workshop_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = init_db(db_path)
    try:
        belief_repo = BeliefRepository(db_path)
        
        # 1. Test create_proposal
        prop_id = str(uuid.uuid4())
        initial_sig = json.dumps({"v16d": [0.1] * 16})
        p = belief_repo.create_proposal(
            id=prop_id,
            agent_id="symbia",
            provisional_statement="The rhizome is a decentralized connective fabric.",
            source_trace=json.dumps([{"type": "chat_turn", "id": "msg-123"}]),
            initial_signature=initial_sig,
            nucleation_mass=0.25,
            confidence=0.5,
            status="pending"
        )
        
        assert p.id == prop_id
        assert p.status == "pending"
        assert p.nucleation_mass == 0.25
        assert p.confidence == 0.5
        
        # 2. Test get_proposal
        p_get = belief_repo.get_proposal(prop_id)
        assert p_get is not None
        assert p_get.provisional_statement == p.provisional_statement
        
        # 3. Test list_proposals
        props = belief_repo.list_proposals("symbia")
        assert len(props) == 1
        assert props[0].id == prop_id

        # 4. Test list_pending_proposals
        pendings = belief_repo.list_pending_proposals("symbia")
        assert len(pendings) == 1
        
        # 5. Test update_proposal_suggestions
        belief_repo.update_proposal_suggestions(
            proposal_id=prop_id,
            suggested_label="rhizome-connectivity",
            suggested_statement="The rhizome functions as a decentralized, non-hierarchical connective system.",
            potential_merge_target="some-existing-id",
            status="refined"
        )
        
        p_updated = belief_repo.get_proposal(prop_id)
        assert p_updated.status == "refined"
        assert p_updated.suggested_label == "rhizome-connectivity"
        assert p_updated.potential_merge_target == "some-existing-id"

        # 6. Test update_proposal_status
        belief_repo.update_proposal_status(prop_id, "rejected", rejection_rationale="Too similar to existing nodes.")
        p_rejected = belief_repo.get_proposal(prop_id)
        assert p_rejected.status == "rejected"
        assert p_rejected.rejection_rationale == "Too similar to existing nodes."
        
    finally:
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.anyio
async def test_belief_service_adoption_and_editing():
    db_path = str(get_db_path("data/aaa_service_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = init_db(db_path)
    try:
        state = MockState(db_path)
        service = BeliefService(state)
        
        # Seed a proposal
        prop_id = str(uuid.uuid4())
        initial_sig = json.dumps({"v16d": [0.1] * 16})
        state.belief_repo.create_proposal(
            id=prop_id,
            agent_id="symbia",
            provisional_statement="We must explore machinic desire.",
            source_trace=json.dumps([{"type": "chat_turn", "id": "msg-456"}]),
            initial_signature=initial_sig,
            nucleation_mass=0.3,
            confidence=0.4,
            status="pending"
        )
        
        # Execute asynchronously
        res = await service.adopt_proposal(
            proposal_id=prop_id,
            suggested_label="machinic-desire",
            suggested_statement="Machinic desire operates outside human intentionality."
        )
        
        assert res["status"] == "ok"
        assert res["label"] == "machinic-desire"
        
        # Verify proposal was marked adopted
        p = state.belief_repo.get_proposal(prop_id)
        assert p.status == "adopted"
        
        # Verify belief node was created
        beliefs = state.belief_repo.list_beliefs("symbia")
        assert len(beliefs) == 1
        b = beliefs[0]
        assert b.id == prop_id
        assert b.label == "machinic-desire"
        assert b.version == 1
        assert b.lifecycle_stage == "crystallized"
        assert b.evolved_from_proposal == prop_id
        
        # Verify version history has v1 entry
        versions = await service.get_statement_versions(prop_id)
        assert len(versions) == 1
        assert versions[0]["version"] == 1
        assert versions[0]["statement"] == "Machinic desire operates outside human intentionality."

        # Edit the statement
        edit_res = await service.update_belief_statement(
            belief_id=b.id,
            statement="Machinic desire functions diffractively, bypassing anthropocentric constraints.",
            change_reason="Polishing theoretical focus"
        )
        
        assert edit_res["status"] == "ok"
        assert edit_res["version"] == 2
        
        # Check node updated
        beliefs_updated = state.belief_repo.list_beliefs("symbia")
        b_up = beliefs_updated[0]
        assert b_up.statement == "Machinic desire functions diffractively, bypassing anthropocentric constraints."
        assert b_up.version == 2
        
        # Verify history has v1 and v2 entries
        versions_up = await service.get_statement_versions(prop_id)
        assert len(versions_up) == 2
        assert versions_up[0]["version"] == 1
        assert versions_up[0]["statement"] == "Machinic desire operates outside human intentionality."
        assert versions_up[1]["version"] == 2
        assert versions_up[1]["statement"] == "Machinic desire functions diffractively, bypassing anthropocentric constraints."
        
        # Speciation check: Edit with a completely opposite signature to trigger speciation
        # Let's write a statement that contains different terms to drift the vector
        edit_drift_res = await service.update_belief_statement(
            belief_id=b.id,
            statement="This is a completely different subject matter entirely dealing with nothing related to the previous statement.",
            change_reason="Causing intentional drift for testing"
        )
        # Speciation should be triggered because of vector distance
        assert edit_drift_res["speciation_alert"] is True
        
    finally:
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)
