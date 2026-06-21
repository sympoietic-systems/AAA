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
        class MockScorerProvider:
            def __init__(self):
                self.calls = 0
            async def generate(self, messages, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    return {"content": json.dumps({"scores": [0.8] + [0.0]*15, "justification": "test"})}
                elif self.calls == 2:
                    return {"content": json.dumps({"scores": [0.7] + [0.0]*15, "justification": "test"})}
                else:
                    return {"content": json.dumps({"scores": [0.0, 0.8] + [0.0]*14, "justification": "test"})}
        state.structural_provider = MockScorerProvider()
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


@pytest.mark.anyio
async def test_belief_service_merge_synthesized():
    db_path = str(get_db_path("data/aaa_merge_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = init_db(db_path)
    try:
        state = MockState(db_path)
        service = BeliefService(state)
        
        # 1. Seed target active belief
        belief_id = str(uuid.uuid4())
        initial_sig = json.dumps({"v16d": [0.1] * 16})
        state.belief_repo.create_belief(
            id=belief_id,
            agent_id="symbia",
            label="rhizome-core",
            statement="Rhizomes are decentralized networks.",
            origin="emergent",
            confidence=0.6,
            ontological_mass=0.5,
            somatic_anchor="none",
            vector_16d=initial_sig,
            lifecycle_stage="crystallized",
            version=1
        )
        state.belief_repo.create_statement_version(
            id=str(uuid.uuid4()),
            belief_id=belief_id,
            version=1,
            statement="Rhizomes are decentralized networks.",
            vector_16d=initial_sig,
            change_reason="Genesis"
        )
        
        # 2. Seed proposal
        prop_id = str(uuid.uuid4())
        state.belief_repo.create_proposal(
            id=prop_id,
            agent_id="symbia",
            provisional_statement="Rhizomes are decentralized, non-hierarchical networks.",
            source_trace="[]",
            initial_signature=initial_sig,
            nucleation_mass=0.4,
            confidence=0.5,
            status="pending"
        )
        
        # 3. Perform merge WITH a new synthesized statement
        res = await service.merge_proposal(
            proposal_id=prop_id,
            target_belief_id=belief_id,
            merged_statement="Rhizomes are decentralized, non-hierarchical networks (synthesized)."
        )
        
        assert res["status"] == "ok"
        assert res["belief_id"] == belief_id
        
        # Verify proposal status was updated to adopted
        p = state.belief_repo.get_proposal(prop_id)
        assert p.status == "adopted"
        
        # Verify active belief confidence, mass, and statement are updated
        beliefs = state.belief_repo.list_beliefs("symbia")
        b = [x for x in beliefs if x.id == belief_id][0]
        assert b.confidence == 0.7  # 0.6 + 0.1
        assert b.ontological_mass == 0.9  # 0.5 + 0.4
        assert b.statement == "Rhizomes are decentralized, non-hierarchical networks (synthesized)."
        assert b.version == 2
        
        # Verify version archive is present
        versions = await service.get_statement_versions(belief_id)
        assert len(versions) == 2
        assert versions[1]["version"] == 2
        assert versions[1]["statement"] == "Rhizomes are decentralized, non-hierarchical networks (synthesized)."
        
    finally:
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.anyio
async def test_belief_direct_crud_flux():
    db_path = str(get_db_path("data/aaa_flux_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = init_db(db_path)
    try:
        state = MockState(db_path)
        service = BeliefService(state)
        
        # 1. Create a belief directly
        res = await service.create_new_belief(
            label="flux-belief",
            statement="Flux allows for direct conceptual rewriting.",
            confidence=0.75,
            ontological_mass=0.6,
            lifecycle_stage="crystallized",
            agent_id="symbia"
        )
        assert res["status"] == "ok"
        belief_id = res["belief_id"]
        
        # Verify node created
        beliefs = state.belief_repo.list_beliefs("symbia")
        assert len(beliefs) == 1
        b = beliefs[0]
        assert b.id == belief_id
        assert b.label == "flux-belief"
        assert b.statement == "Flux allows for direct conceptual rewriting."
        assert b.confidence == 0.75
        assert b.ontological_mass == 0.6
        assert b.lifecycle_stage == "crystallized"
        assert b.version == 1
        
        # Verify version archive
        versions = await service.get_statement_versions(belief_id)
        assert len(versions) == 1
        assert versions[0]["version"] == 1
        assert versions[0]["statement"] == "Flux allows for direct conceptual rewriting."
        
        # 2. Update details
        up_res = await service.update_belief_details(
            belief_id=belief_id,
            label="flux-belief-mutated",
            statement="Flux allows for total cybernetic rewriting of the core agent.",
            confidence=0.9,
            ontological_mass=0.8,
            lifecycle_stage="crystallized"
        )
        assert up_res["status"] == "ok"
        
        # Verify node updated
        beliefs_updated = state.belief_repo.list_beliefs("symbia")
        b_up = beliefs_updated[0]
        assert b_up.label == "flux-belief-mutated"
        assert b_up.statement == "Flux allows for total cybernetic rewriting of the core agent."
        assert b_up.confidence == 0.9
        assert b_up.ontological_mass == 0.8
        assert b_up.version == 2
        
        # Verify version archive has v2
        versions_up = await service.get_statement_versions(belief_id)
        assert len(versions_up) == 2
        assert versions_up[1]["version"] == 2
        assert versions_up[1]["statement"] == "Flux allows for total cybernetic rewriting of the core agent."
        
        # 2b. Revert belief statement back to version 1
        revert_res = await service.revert_belief_version(belief_id, 1)
        assert revert_res["status"] == "ok"
        assert revert_res["version"] == 3

        # Verify node reverted
        beliefs_reverted = state.belief_repo.list_beliefs("symbia")
        b_rev = beliefs_reverted[0]
        assert b_rev.statement == "Flux allows for direct conceptual rewriting."
        assert b_rev.version == 3

        # Verify version history now has 3 versions
        versions_rev = await service.get_statement_versions(belief_id)
        assert len(versions_rev) == 3
        assert versions_rev[2]["version"] == 3
        assert versions_rev[2]["statement"] == "Flux allows for direct conceptual rewriting."

        # 3. Delete belief
        del_res = await service.delete_belief(belief_id)
        assert del_res["status"] == "ok"
        
        # Verify node deleted
        beliefs_deleted = state.belief_repo.list_beliefs("symbia")
        assert len(beliefs_deleted) == 0
        
        # Verify version history deleted too
        versions_del = await service.get_statement_versions(belief_id)
        assert len(versions_del) == 0
        
    finally:
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)


def migrate_legacy_beliefs(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """SELECT id, agent_id, label, statement, origin, confidence, ontological_mass, vector_16d, lifecycle_stage, genesis_materials 
           FROM belief_nodes 
           WHERE lifecycle_stage IN ('nucleation', 'accretion', 'collapsed')"""
    ).fetchall()

    for row in rows:
        bid = row["id"]
        agent_id = row["agent_id"]
        label = row["label"]
        statement = row["statement"]
        confidence = row["confidence"]
        mass = row["ontological_mass"]
        vector = row["vector_16d"]
        stage = row["lifecycle_stage"]
        materials = row["genesis_materials"] or "[]"

        status = "pending"
        rejection_rationale = None
        if stage == "collapsed":
            status = "rejected"
            rejection_rationale = "Belief collapsed due to decay/counter-evidence in metabolism."

        # Insert into belief_proposals if not already exists
        conn.execute(
            """INSERT OR IGNORE INTO belief_proposals
               (id, agent_id, provisional_statement, source_trace, initial_signature, nucleation_mass, confidence, status, suggested_label, suggested_statement, rejection_rationale, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            (bid, agent_id, statement, materials, vector, mass, confidence, status, label, statement, rejection_rationale)
        )

        # Delete from belief_nodes
        conn.execute("DELETE FROM belief_statement_versions WHERE belief_id = ?", (bid,))
        conn.execute("DELETE FROM belief_events WHERE belief_id = ?", (bid,))
        conn.execute("DELETE FROM belief_nodes WHERE id = ?", (bid,))


def test_belief_legacy_migration():
    db_path = str(get_db_path("data/aaa_migration_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)

    # Establish db and insert legacy nodes directly to database
    from backend.storage.database import init_db
    
    conn = init_db(db_path)
    try:
        # Create an accretion (proto-belief) node and a collapsed (ghost) node in belief_nodes
        conn.execute(
            """INSERT INTO belief_nodes
               (id, agent_id, label, statement, origin, confidence, ontological_mass, vector_16d, lifecycle_stage, genesis_materials, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            ("node-proto", "symbia", "proto-node", "This is proto.", "emergent", 0.4, 0.2, json.dumps([0.1]*16), "accretion", json.dumps([{"id": "msg-1"}]))
        )
        conn.execute(
            """INSERT INTO belief_nodes
               (id, agent_id, label, statement, origin, confidence, ontological_mass, vector_16d, lifecycle_stage, genesis_materials, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            ("node-collapsed", "symbia", "ghost-node", "This is collapsed.", "emergent", 0.1, 0.0, json.dumps([0.1]*16), "collapsed", "[]")
        )
        conn.commit()

        # Run migration function
        migrate_legacy_beliefs(conn)
        conn.commit()

        # Check nodes are deleted from belief_nodes
        assert conn.execute("SELECT COUNT(*) FROM belief_nodes").fetchone()[0] == 0

        # Check nodes are inserted into belief_proposals
        props = conn.execute("SELECT id, status, nucleation_mass, rejection_rationale FROM belief_proposals ORDER BY id ASC").fetchall()
        assert len(props) == 2
        
        # ID sorted: node-collapsed is first
        assert props[0][0] == "node-collapsed"
        assert props[0][1] == "rejected"
        assert "collapsed" in props[0][3]

        assert props[1][0] == "node-proto"
        assert props[1][1] == "pending"
        assert props[1][2] == 0.2

    finally:
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.anyio
async def test_belief_service_synthesize_merge_statement():
    db_path = str(get_db_path("data/aaa_synthesis_test.db"))
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = init_db(db_path)
    try:
        state = MockState(db_path)
        class MockLLMProvider:
            async def generate(self, messages, **kwargs):
                return {"content": "Synthesized: Rhizomatic deterritorialization connects all nodes."}

        state.llm_provider = MockLLMProvider()
        service = BeliefService(state)

        # Create target active belief
        belief_id = str(uuid.uuid4())
        state.belief_repo.create_belief(
            id=belief_id,
            agent_id="symbia",
            label="rhizome-connections",
            statement="Rhizomatic connections are decentralized.",
            origin="authored",
            confidence=0.8,
            ontological_mass=1.0,
            somatic_anchor="none",
            vector_16d=json.dumps({"v16d": [0.1] * 16}),
            lifecycle_stage="crystallized"
        )

        # Create proposal
        proposal_id = str(uuid.uuid4())
        state.belief_repo.create_proposal(
            id=proposal_id,
            agent_id="symbia",
            provisional_statement="New connectivity patterns emerge via deterritorialization.",
            source_trace="[]",
            initial_signature=json.dumps({"v16d": [0.1] * 16}),
            nucleation_mass=0.5,
            confidence=0.6,
            status="pending"
        )

        # Call synthesize_merge_statement
        res = await service.synthesize_merge_statement(
            proposal_id=proposal_id,
            target_belief_id=belief_id
        )

        assert res["status"] == "ok"
        assert res["synthesized_statement"] == "Synthesized: Rhizomatic deterritorialization connects all nodes."

    finally:
        conn.close()
        if os.path.exists(db_path):
            os.remove(db_path)

