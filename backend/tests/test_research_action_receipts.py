from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.storage.database import init_db
from backend.storage.repositories.research.action_receipt import (
    ReceiptConflictError,
    ResearchActionReceiptRepository,
)
from backend.storage.repositories.research.research_task import ResearchTaskRepository
from backend.storage.research_receipts import (
    ActionObservation,
    EvidencePacket,
    ProviderAttemptReceipt,
    ResearchActionReceipt,
)

NOW = datetime(2026, 10, 5, tzinfo=UTC)


@pytest.fixture
def repo(tmp_path: Path) -> ResearchActionReceiptRepository:
    db_path = str(tmp_path / "receipts.db")
    init_db(db_path).close()
    ResearchTaskRepository(db_path).create(
        {
            "id": "task",
            "title": "Receipts",
            "objective": "Test provenance",
            "trigger_source": "test",
            "status": "queued",
            "priority": 1,
            "max_depth": 1,
            "max_breadth": 1,
            "budget_limit_usd": 1,
        }
    )
    return ResearchActionReceiptRepository(db_path)


def request(**changes) -> ResearchActionReceipt:
    return ResearchActionReceipt.model_validate(
        {
            "action_id": "action",
            "task_id": "task",
            "kind": "searching",
            "intent": "gather",
            "input_version": "v1",
            "dependency_ids": ["plan"],
            "rationale": "Find evidence",
            "budget_reserved": 0.25,
            "deadline": NOW,
            "contract_hash": "contract",
            "policy_hash": "policy",
            **changes,
        }
    )


def test_restart_replay_preserves_request_and_terminal_observation(repo):
    initial = request()
    repo.create(initial)
    running = initial.transition("running", NOW)
    repo.transition(running, expected_status="pending")
    observed = ActionObservation(
        output_refs=("artifact:1",),
        evidence_packets=(
            EvidencePacket(
                source_id="source",
                source_version="hash",
                raw_span_locator="page:2",
                contrary_segment_ids=("segment:2",),
                extraction_quality=0.4,
                excluded_evidence={"copy": "syndicated"},
                unavailable_evidence={"private": "denied"},
                unresolved_gaps=("date unknown",),
            ),
        ),
    )
    terminal = running.transition("partial", NOW, observed)
    repo.transition(terminal, expected_status="running")
    restarted = ResearchActionReceiptRepository(repo._db_path)
    assert restarted.get("task", "action") == terminal
    assert restarted.create(initial) == terminal
    assert restarted.transition(terminal, expected_status="running") == terminal
    assert restarted.get("another-task", "action") is None


@pytest.mark.parametrize(
    "changes",
    [
        {"input_version": "v2"},
        {"dependency_ids": ["different"]},
        {"budget_reserved": 0.5},
        {"contract_hash": "other"},
        {"policy_hash": "other"},
    ],
)
def test_request_identity_cannot_be_rewritten(repo, changes):
    repo.create(request())
    with pytest.raises(ReceiptConflictError):
        repo.create(request(**changes))
    assert repo.get("task", "action") == request()


def test_late_output_cannot_overwrite_terminal_observation(repo):
    initial = repo.create(request())
    running = initial.transition("running", NOW)
    repo.transition(running, expected_status="pending")
    committed = running.transition("partial", NOW, ActionObservation(output_refs=("first",)))
    repo.transition(committed, expected_status="running")
    with pytest.raises(ReceiptConflictError):
        repo.transition(
            running.transition("complete", NOW, ActionObservation(output_refs=("late",))), expected_status="running"
        )
    assert repo.get("task", "action") == committed


def test_unknown_delivery_stays_unknown(repo):
    initial = repo.create(request())
    running = initial.transition("running", NOW)
    repo.transition(running, expected_status="pending")
    failed = running.transition("failed", NOW)
    repo.transition(failed, expected_status="running")
    assert repo.get("task", "action").observation is None
    attempt = ProviderAttemptReceipt(
        task_id="task",
        action_id="action",
        request_id="req",
        provider="fixture",
        model="fixture",
        attempt_number=1,
        started_at=NOW,
    )
    assert attempt.finish_reason is None and attempt.usage is None and attempt.truncated is None


def test_truncated_provider_delivery_cannot_be_complete(repo):
    initial = repo.create(request())
    running = initial.transition("running", NOW)
    repo.transition(running, expected_status="pending")
    attempt = ProviderAttemptReceipt(
        task_id="task",
        action_id="action",
        request_id="req",
        provider="fixture",
        model="fixture",
        attempt_number=1,
        started_at=NOW,
        finish_reason="length",
        truncated=True,
        outcome="partial",
    )
    observation = ActionObservation(provider_attempts=(attempt,))
    with pytest.raises(ReceiptConflictError):
        repo.transition(running.transition("complete", NOW, observation), expected_status="running")
    repo.transition(running.transition("partial", NOW, observation), expected_status="running")


def test_outer_transaction_rollback_removes_receipt(repo):
    with pytest.raises(RuntimeError), repo.atomic():
        repo.create(request())
        raise RuntimeError("abort")
    assert repo.get("task", "action") is None


def test_migration_is_additive_and_repeatable(repo):
    init_db(repo._db_path).close()
    assert ResearchTaskRepository(repo._db_path).get("task")["objective"] == "Test provenance"
    repo.create(request())
    ResearchTaskRepository(repo._db_path).delete("task")
    assert repo.get("task", "action") is None


@pytest.mark.parametrize(
    "changes", [{"budget_reserved": float("nan")}, {"budget_reserved": -1}, {"deadline": datetime(2026, 10, 5)}]
)
def test_invalid_budget_and_naive_time_rejected(changes):
    with pytest.raises(ValidationError):
        request(**changes)
