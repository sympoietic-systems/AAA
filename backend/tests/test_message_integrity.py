from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.errors import ConstraintViolation
from backend.storage.database import init_db
from backend.storage.repositories import MessageRepository


@pytest.fixture
def repo(tmp_path):
    path = str(tmp_path / "integrity.db")
    init_db(path).close()
    return MessageRepository(path)


def insert(repo, **kwargs):
    return repo.insert("human", "message", b"", "test", 0, **kwargs)


def test_message_insert_obeys_outer_transaction_rollback(repo):
    with pytest.raises(RuntimeError), repo.atomic():
        parent = insert(repo, conversation_id="a")
        insert(repo, conversation_id="a", parent_message_id=parent.id)
        raise RuntimeError("rollback")
    assert repo.get_recent(limit=10, conversation_id="a") == []


def test_invalid_parent_is_structured_and_writes_nothing(repo):
    parent = insert(repo, conversation_id="a")
    for parent_id in (parent.id, 999999):
        with pytest.raises(ConstraintViolation):
            insert(repo, conversation_id="b", parent_message_id=parent_id)
    assert repo.get_recent(limit=10, conversation_id="b") == []


def test_committed_parent_visible_to_other_thread(repo):
    parent = insert(repo, conversation_id="a")
    with ThreadPoolExecutor(max_workers=4) as pool:
        children = list(pool.map(lambda _: insert(repo, conversation_id="a", parent_message_id=parent.id), range(12)))
    assert len({child.id for child in children}) == 12
    assert all(child.parent_message_id == parent.id for child in children)
