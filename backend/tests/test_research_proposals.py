from pathlib import Path
import sys
import os
from unittest.mock import MagicMock

root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)
os.chdir(root_path)

from backend.services.annotations import extract_research_proposals, process_research_proposals

def test_extract_research_proposals():
    # Test extract with no ID
    text = (
        "Some text. <research-proposal>\n"
        "  <objective>Objective text</objective>\n"
        "  <rationale>Rationale text</rationale>\n"
        "  <suggested_depth>2</suggested_depth>\n"
        "  <suggested_breadth>3</suggested_breadth>\n"
        "  <is_agonistic>false</is_agonistic>\n"
        "</research-proposal> More text."
    )
    proposals = extract_research_proposals(text)
    assert len(proposals) == 1
    assert proposals[0]["objective"] == "Objective text"
    assert proposals[0]["rationale"] == "Rationale text"
    assert proposals[0]["suggested_depth"] == 2
    assert proposals[0]["suggested_breadth"] == 3
    assert proposals[0]["is_agonistic"] is False
    assert proposals[0]["id"] is not None

    # Test extract with ID
    text_with_id = (
        'Some text. <research-proposal id="preset-id-123">\n'
        "  <objective>Objective text 2</objective>\n"
        "  <rationale>Rationale text 2</rationale>\n"
        "  <suggested_depth>4</suggested_depth>\n"
        "  <suggested_breadth>5</suggested_breadth>\n"
        "  <is_agonistic>true</is_agonistic>\n"
        "</research-proposal> More text."
    )
    proposals = extract_research_proposals(text_with_id)
    assert len(proposals) == 1
    assert proposals[0]["id"] == "preset-id-123"
    assert proposals[0]["objective"] == "Objective text 2"
    assert proposals[0]["rationale"] == "Rationale text 2"
    assert proposals[0]["suggested_depth"] == 4
    assert proposals[0]["suggested_breadth"] == 5
    assert proposals[0]["is_agonistic"] is True


def test_process_research_proposals():
    task_manager_mock = MagicMock()
    message_repo_mock = MagicMock()

    task_manager_mock.create_task.return_value = "generated-uuid-456"

    text = (
        "Symbia: <research-proposal>\n"
        "  <objective>Analyze WebGPU feature support</objective>\n"
        "  <rationale>The user is building shaders</rationale>\n"
        "  <suggested_depth>2</suggested_depth>\n"
        "  <suggested_breadth>3</suggested_breadth>\n"
        "  <is_agonistic>false</is_agonistic>\n"
        "</research-proposal>"
    )

    processed = process_research_proposals(
        response_text=text,
        conversation_id="conv-abc",
        message_id=987,
        task_manager=task_manager_mock,
        message_repo=message_repo_mock,
    )

    assert 'id="generated-uuid-456"' in processed
    assert "<research-proposal id=\"generated-uuid-456\">" in processed

    # Verify task_manager.create_task was called with correct args
    task_manager_mock.create_task.assert_called_once_with(
        objective="Analyze WebGPU feature support",
        trigger_source="symbia_conversation",
        title="Analyze WebGPU feature support",
        conversation_id="conv-abc",
        status="proposed",
        priority=3,
        max_depth=2,
        max_breadth=3,
        is_agonistic=False,
        budget_limit_usd=0.50,
        proposal_rationale="The user is building shaders",
        proposal_message_id=987,
    )

    # Verify message_repo.update_content was called
    message_repo_mock.update_content.assert_called_once_with(987, processed)

    # Setup for already processed tag
    task_manager_mock.reset_mock()
    message_repo_mock.reset_mock()

    processed_again = process_research_proposals(
        response_text=processed,
        conversation_id="conv-abc",
        message_id=987,
        task_manager=task_manager_mock,
        message_repo=message_repo_mock,
    )

    # Should not create new tasks or update repo
    assert processed_again == processed
    assert not task_manager_mock.create_task.called
    assert not message_repo_mock.update_content.called

    print("All research proposal backend tests passed!")

if __name__ == "__main__":
    test_extract_research_proposals()
    test_process_research_proposals()
