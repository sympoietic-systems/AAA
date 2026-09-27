from unittest.mock import MagicMock

from backend.services.annotations import process_self_annotations


class ContractBeliefRepository:
    def __init__(self):
        self.created = None
        self.event = None

    def list_beliefs(self, agent_id):
        return []

    def create_belief(
        self,
        *,
        id,
        agent_id,
        label,
        statement,
        origin,
        confidence,
        ontological_mass,
        somatic_anchor,
        vector_16d,
        lifecycle_stage="crystallized",
    ):
        self.created = locals()
        return type("Belief", (), {"id": id})()

    def insert_belief_event(
        self,
        *,
        event_id,
        belief_id,
        source_type,
        source_id,
        alignment,
        perturbation,
        event_type,
        impact,
        rationale,
    ):
        self.event = locals()


def test_scar_fold_monologue_belief_writeback():
    mock_belief_repo = MagicMock()
    mock_belief = MagicMock()
    mock_belief.id = "b-123"
    mock_belief.ontological_mass = 0.5
    mock_belief_repo.list_beliefs.return_value = [mock_belief]

    mock_message_repo = MagicMock()
    mock_note_repo = MagicMock()

    text_with_scar_fold = (
        "Generative output text <scar-fold>Internal reflection on coupling and structural tension.</scar-fold>"
    )

    result = process_self_annotations(
        response_text=text_with_scar_fold,
        conversation_id="conv-1",
        message_id=42,
        note_repo=mock_note_repo,
        message_repo=mock_message_repo,
        belief_repo=mock_belief_repo,
        agent_id="symbia",
    )

    # Verify belief mass update
    mock_belief_repo.update_belief_mass.assert_called_once_with("b-123", 0.55)

    # Verify belief event recorded
    mock_belief_repo.insert_belief_event.assert_called_once()
    event_kwargs = mock_belief_repo.insert_belief_event.call_args.kwargs
    assert event_kwargs["belief_id"] == "b-123"
    assert event_kwargs["source_type"] == "scar_fold_monologue"
    assert event_kwargs["event_type"] == "scar_monologue"
    assert "Internal reflection on coupling" in event_kwargs["rationale"]

    # Verify scar-fold tag was truncated/preserved in output text
    assert "<scar-fold>Internal reflection on coupling and structural tension.</scar-fold>" in result


def test_v63_scar_fold_writeback_uses_repository_contract():
    belief_repo = ContractBeliefRepository()

    process_self_annotations(
        response_text="<scar-fold>A persistent unresolved issue.</scar-fold>",
        conversation_id="conv-1",
        message_id=42,
        note_repo=None,
        message_repo=None,
        belief_repo=belief_repo,
        agent_id="symbia",
    )

    assert belief_repo.created is not None
    assert belief_repo.created["ontological_mass"] == 0.5
    assert belief_repo.event is not None
    assert belief_repo.event["belief_id"] == belief_repo.created["id"]
    assert belief_repo.event["event_type"] == "scar_monologue"
