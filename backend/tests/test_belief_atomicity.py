import json
import uuid

import pytest

from backend.storage.database import init_db
from backend.storage.repository import BeliefRepository


def _create_proposal(repository: BeliefRepository, proposal_id: str) -> None:
    repository.create_proposal(
        id=proposal_id,
        agent_id="symbia",
        provisional_statement="A provisional belief.",
        source_trace="[]",
        initial_signature=json.dumps({"v16d": [0.1] * 16}),
    )


def test_atomic_belief_mutation_rolls_back_nested_repository_commits(tmp_path):
    db_path = str(tmp_path / "belief_atomic_test.db")
    init_db(db_path).close()
    repository = BeliefRepository(db_path)
    proposal_id = str(uuid.uuid4())
    _create_proposal(repository, proposal_id)

    with pytest.raises(RuntimeError, match="injected failure"), repository.atomic():
        repository.update_proposal_status(proposal_id, "adopted")
        repository.create_belief(
            id=proposal_id,
            agent_id="symbia",
            label="provisional",
            statement="A provisional belief.",
            origin="emergent",
            confidence=0.2,
            ontological_mass=0.1,
            somatic_anchor="none",
            vector_16d=json.dumps({"v16d": [0.1] * 16}),
        )
        raise RuntimeError("injected failure")

    proposal = repository.get_proposal(proposal_id)
    assert proposal is not None
    assert proposal.status == "pending"
    assert repository.get_belief("symbia", proposal_id) is None


def test_atomic_belief_mutation_commits_as_one_unit(tmp_path):
    db_path = str(tmp_path / "belief_atomic_commit_test.db")
    init_db(db_path).close()
    repository = BeliefRepository(db_path)
    proposal_id = str(uuid.uuid4())
    _create_proposal(repository, proposal_id)

    with repository.atomic():
        repository.update_proposal_status(proposal_id, "adopted")
        repository.create_belief(
            id=proposal_id,
            agent_id="symbia",
            label="provisional",
            statement="A provisional belief.",
            origin="emergent",
            confidence=0.2,
            ontological_mass=0.1,
            somatic_anchor="none",
            vector_16d=json.dumps({"v16d": [0.1] * 16}),
        )

    proposal = repository.get_proposal(proposal_id)
    assert proposal is not None
    assert proposal.status == "adopted"
    assert repository.get_belief("symbia", proposal_id) is not None
