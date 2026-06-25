from pathlib import Path
import sys
import os

root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)
os.chdir(root_path)

from backend.storage.repositories.note_markup import (
    split_mark_at_block_boundaries,
    remove_note_marks,
    balance_tags,
)


def test_split_mark_simple_text():
    result = split_mark_at_block_boundaries('<mark>hello world</mark>', 'abc-123')
    assert 'data-note-id="abc-123"' in result
    assert 'id="note-highlight-abc-123"' in result
    assert 'hello world' in result


def test_split_mark_with_bold():
    result = split_mark_at_block_boundaries('<mark>some **bold** text</mark>', 'n1')
    assert 'data-note-id="n1"' in result
    assert '</mark>**<mark' in result


def test_split_mark_with_block_break():
    result = split_mark_at_block_boundaries(
        '<mark>paragraph one\n\nparagraph two</mark>', 'n1'
    )
    assert 'paragraph one' in result
    assert 'paragraph two' in result
    assert '\n\n' in result


def test_remove_note_marks_data_note_id():
    content = '<mark data-note-id="abc">hello</mark> world'
    result = remove_note_marks(content, 'abc')
    assert '<mark' not in result
    assert 'hello' in result


def test_remove_note_marks_legacy_id():
    content = '<mark id="abc">hello</mark> world'
    result = remove_note_marks(content, 'abc')
    assert '<mark' not in result
    assert 'hello' in result


def test_remove_note_marks_note_highlight():
    content = '<mark id="note-highlight-xyz" data-note-id="xyz">text</mark> rest'
    result = remove_note_marks(content, 'xyz')
    assert '<mark' not in result
    assert 'text' in result


def test_remove_note_marks_aaa_note():
    content = '<aaa-note id="n99">note text</aaa-note> more'
    result = remove_note_marks(content, 'n99')
    assert '<aaa-note' not in result
    assert 'note text' in result


def test_balance_tags_removes_orphans():
    content = 'before</mark> after'
    result = balance_tags(content)
    assert '</mark>' not in result
    assert 'before after' in result


def test_balance_tags_preserves_balanced():
    content = '<mark>inside</mark> outside'
    result = balance_tags(content)
    assert result == content


def test_balance_tags_nested():
    content = '<mark><mark>deep</mark></mark>'
    result = balance_tags(content)
    assert result == content


def test_split_mark_no_formatting():
    result = split_mark_at_block_boundaries('<mark>plain text</mark>', 'id1')
    assert '<mark id="note-highlight-id1"' in result
    assert 'plain text' in result


def test_remove_note_marks_no_match():
    content = 'just plain text'
    result = remove_note_marks(content, 'nonexistent')
    assert result == content
