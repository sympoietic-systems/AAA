from pathlib import Path
import sys
import os
from unittest.mock import MagicMock

root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)
os.chdir(root_path)

from backend.services.chat import process_self_annotations

def test_process_self_annotations():
    # Setup mocks
    note_repo_mock = MagicMock()
    message_repo_mock = MagicMock()

    # Case 1: Standard tags
    text = 'Here is a <mark comment="standard comment">highlighted text</mark>.'
    processed = process_self_annotations(text, "conv-1", 123, note_repo_mock, message_repo_mock)
    
    assert "id=" in processed
    assert "<mark id=" in processed
    assert "highlighted text" in processed
    assert note_repo_mock.create_self_note.called
    args, kwargs = note_repo_mock.create_self_note.call_args
    assert kwargs["selected_text"] == "highlighted text"
    assert kwargs["comment"] == "standard comment"
    assert kwargs["visibility"] == "agent"
    
    # Reset mocks
    note_repo_mock.reset_mock()
    message_repo_mock.reset_mock()

    # Case 2: Swapped attributes and single quotes, with extra spacing
    text = "Let's check <aaa-note visibility='shared'   comment='swapped single quotes'>node contents</aaa-note>."
    processed = process_self_annotations(text, "conv-1", 123, note_repo_mock, message_repo_mock)
    
    assert "id=" in processed
    assert "<aaa-note id=" in processed
    assert note_repo_mock.create_self_note.called
    args, kwargs = note_repo_mock.create_self_note.call_args
    assert kwargs["selected_text"] == "node contents"
    assert kwargs["comment"] == "swapped single quotes"
    assert kwargs["visibility"] == "agent"

    # Reset mocks
    note_repo_mock.reset_mock()
    message_repo_mock.reset_mock()

    # Case 3: Tag already has ID (should skip)
    text = 'This <mark id="existing-id" data-note-id="existing-id">already processed</mark> tag.'
    processed = process_self_annotations(text, "conv-1", 123, note_repo_mock, message_repo_mock)
    assert processed == text
    assert not note_repo_mock.create_self_note.called

    # Reset mocks
    note_repo_mock.reset_mock()
    message_repo_mock.reset_mock()

    # Case 4: Echoed note_entanglement tags (should convert back to <mark> with proper IDs)
    text = 'The LLM said <note_entanglement note_id="abc-123" comment="test">some quoted text</note_entanglement> in its reply.'
    processed = process_self_annotations(text, "conv-1", 123, note_repo_mock, message_repo_mock)
    assert '<mark id="note-highlight-abc-123" data-note-id="abc-123">some quoted text</mark>' in processed
    assert "<note_entanglement" not in processed

    print("All process_self_annotations tests passed!")

if __name__ == "__main__":
    test_process_self_annotations()
