import pytest
from unittest.mock import MagicMock
from backend.services.annotations import process_self_annotations


def test_scar_fold_monologue_belief_writeback():
    mock_belief_repo = MagicMock()
    mock_belief = MagicMock()
    mock_belief.id = "b-123"
    mock_belief.mass = 0.5
    mock_belief_repo.list_beliefs.return_value = [mock_belief]

    mock_message_repo = MagicMock()
    mock_note_repo = MagicMock()

    text_with_scar_fold = "Generative output text <scar-fold>Internal reflection on coupling and structural tension.</scar-fold>"

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
    mock_belief_repo.record_event.assert_called_once()
    event_kwargs = mock_belief_repo.record_event.call_args.kwargs
    assert event_kwargs["belief_id"] == "b-123"
    assert event_kwargs["source_type"] == "scar_fold_monologue"
    assert event_kwargs["event_type"] == "scar_monologue"
    assert "Internal reflection on coupling" in event_kwargs["rationale"]

    # Verify scar-fold tag was truncated/preserved in output text
    assert "<scar-fold>Internal reflection on coupling and structural tension.</scar-fold>" in result
