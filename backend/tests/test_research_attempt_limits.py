import asyncio
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from backend.modules.llm_pool import ModelPoolProvider
from backend.modules.llm_protocol import RateLimitError
from backend.modules.provider_attempts import AttemptBudgetExceeded, AttemptScope, attempt_scope, invoke_attempt
from backend.services.research.action_journal import ResearchActionJournal
from backend.services.research.attempt_sink import DurableAttemptSink
from backend.storage.database import init_db
from backend.storage.repositories.research.action_receipt import ReceiptConflictError, ResearchActionReceiptRepository
from backend.storage.repositories.research.provider_attempt import ResearchProviderAttemptRepository
from backend.storage.repositories.research.research_task import ResearchTaskRepository


@pytest.fixture
def setup_attempts(tmp_path: Path):
    db = str(tmp_path / "attempt_test.db")
    init_db(db).close()
    ResearchTaskRepository(db).create(
        {
            "id": "task",
            "title": "Attempts",
            "objective": "Verify",
            "trigger_source": "test",
            "status": "active",
            "priority": 1,
            "max_depth": 1,
            "max_breadth": 1,
            "budget_limit_usd": 1,
        }
    )
    state = {"phase": "planning", "action_journal_policy": {"contract_hash": "c", "policy_hash": "p"}}
    journal = ResearchActionJournal(ResearchActionReceiptRepository(db))
    action = journal.begin("task", state, "planning", {})
    repo = ResearchProviderAttemptRepository(db)
    records = []
    sink = DurableAttemptSink(repo, action, records, 2)
    scope = AttemptScope(sink, datetime.now(UTC) + timedelta(seconds=2), 0.03, 2)
    return scope, repo, action, records


@pytest.mark.asyncio
async def test_pending_is_durable_before_invocation_and_terminal_is_immutable(setup_attempts):
    scope, repo, action, records = setup_attempts

    class Provider:
        async def generate(self, messages):
            pending = await asyncio.to_thread(repo.list_by_action, "task", action.action_id)
            assert len(pending) == 1 and pending[0].outcome == "pending"
            return {"content": "ok", "finish_reason": "stop", "usage": {"total_tokens": 3}}

    with attempt_scope(scope):
        assert (await invoke_attempt(Provider(), []))["content"] == "ok"
    assert records[0].outcome == "complete"
    stored = await asyncio.to_thread(repo.get, "task", action.action_id, records[0].attempt_id)
    assert stored == records[0]
    changed = records[0].model_copy(update={"outcome": "partial"})
    with pytest.raises(ReceiptConflictError, match="Stale"):
        await asyncio.to_thread(repo.finish, changed)


@pytest.mark.asyncio
async def test_cancel_resistant_late_delivery_cannot_overwrite_timeout(setup_attempts):
    scope, repo, action, records = setup_attempts
    exited = asyncio.Event()

    class Provider:
        async def generate(self, messages):
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                await asyncio.sleep(0.02)
                exited.set()
                return {"content": "late", "finish_reason": "stop"}

    clock = time.perf_counter()
    with attempt_scope(scope), pytest.raises(TimeoutError):
        await invoke_attempt(Provider(), [])
    assert time.perf_counter() - clock < 0.3
    await asyncio.wait_for(exited.wait(), 0.5)
    assert len(records) == 1 and records[0].error_category == "timeout"
    stored = await asyncio.to_thread(repo.list_by_action, "task", action.action_id)
    assert stored == records and stored[0].outcome == "failed"


@pytest.mark.asyncio
async def test_task_budget_survives_new_request_scope_and_restart(setup_attempts):
    scope, repo, action, records = setup_attempts

    class Provider:
        async def generate(self, messages):
            return {"content": "partial", "finish_reason": "length"}

    with attempt_scope(scope):
        await invoke_attempt(Provider(), [])
        await invoke_attempt(Provider(), [])
        with pytest.raises(AttemptBudgetExceeded):
            await invoke_attempt(Provider(), [])
    restarted = ResearchProviderAttemptRepository(repo._db_path)
    another = AttemptScope(DurableAttemptSink(restarted, action, [], 2), scope.deadline, 0.03, 2)
    with attempt_scope(another), pytest.raises(ReceiptConflictError, match="budget"):
        await invoke_attempt(Provider(), [])
    assert all(r.outcome == "partial" and r.truncated for r in records)


@pytest.mark.asyncio
async def test_cancellation_and_provider_timeout_leave_terminal_receipts(setup_attempts):
    scope, repo, action, records = setup_attempts

    class Provider:
        async def generate(self, messages):
            raise TimeoutError("private credential text")

    with attempt_scope(scope), pytest.raises(TimeoutError):
        await invoke_attempt(Provider(), [])
    assert records[0].error_category == "TimeoutError"
    assert "private" not in records[0].model_dump_json()

    class CancelledProvider:
        async def generate(self, messages):
            raise asyncio.CancelledError()

    with attempt_scope(scope), pytest.raises(asyncio.CancelledError):
        await invoke_attempt(CancelledProvider(), [])
    assert records[1].outcome == "cancelled"


@pytest.mark.asyncio
async def test_expired_deadline_invokes_nothing(setup_attempts):
    scope, repo, action, records = setup_attempts
    scope.deadline = datetime.now(UTC) - timedelta(seconds=1)

    class Provider:
        async def generate(self, messages):
            pytest.fail("Provider must not run")

    with attempt_scope(scope), pytest.raises(AttemptBudgetExceeded):
        await invoke_attempt(Provider(), [])
    assert not await asyncio.to_thread(repo.list_by_action, "task", action.action_id)


@pytest.mark.asyncio
async def test_pool_leaf_failover_shares_request_and_records_each_attempt(setup_attempts, monkeypatch):
    scope, repo, action, records = setup_attempts
    scope.timeout_seconds = 1

    class Leaf:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0
            self._model = kwargs["model"]
            self.provider_name = kwargs["provider_name"]

        async def generate(self, messages, **params):
            rows = await asyncio.to_thread(repo.list_by_action, "task", action.action_id)
            assert rows[-1].outcome == "pending"
            if self._model == "first":
                raise RateLimitError("private provider detail")
            return {"content": "delivered", "finish_reason": "stop"}

    monkeypatch.setattr("backend.modules.llm_pool.OpenAICompatibleProvider", Leaf)
    pool = ModelPoolProvider(
        api_key="",
        models=["nvidia_router/first", "nvidia_router/second"],
        fallback_model="",
        nvidia_keys=["fixture-key"],
    )
    # Model failures reuse the same key only for the next model after cooldown.
    pool._nvidia_key_mgr.cooldown_seconds = 0
    with attempt_scope(scope):
        assert (await pool.generate([]))["content"] == "delivered"
    assert [r.outcome for r in records] == ["failed", "complete"]
    assert records[0].request_id == records[1].request_id
    assert [r.attempt_number for r in records] == [1, 2]
    assert [r.model for r in records] == ["first", "second"]
    assert all(r.provider == "model_pool_nvidia" for r in records)


@pytest.mark.asyncio
async def test_stale_action_cannot_spend_another_attempt(setup_attempts):
    scope, repo, action, records = setup_attempts
    actions = ResearchActionReceiptRepository(repo._db_path)
    from backend.storage.research_receipts import ActionObservation

    terminal = action.transition("complete", datetime.now(UTC), ActionObservation())
    await asyncio.to_thread(actions.transition, terminal, expected_status="running")

    class Provider:
        async def generate(self, messages):
            pytest.fail("Stale action must not invoke provider")

    with attempt_scope(scope), pytest.raises(ReceiptConflictError, match="current running"):
        await invoke_attempt(Provider(), [])


@pytest.mark.asyncio
async def test_phase_deadline_bounds_cancel_resistant_work():
    from backend.modules.provider_attempts import bounded_call

    exited = asyncio.Event()

    async def work():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(0.02)
            exited.set()
            return "late"

    with pytest.raises(AttemptBudgetExceeded):
        await bounded_call(work, 0.02)
    await asyncio.wait_for(exited.wait(), 0.5)


@pytest.mark.asyncio
async def test_outstanding_limit_is_reserved_before_async_storage():
    from backend.modules.provider_attempts import MAX_OUTSTANDING

    gate = asyncio.Event()
    started = []

    class Sink:
        async def start(self, *args):
            started.append(args[0])
            await gate.wait()

        async def finish(self, *args, **kwargs):
            return None

    class Provider:
        async def generate(self, messages):
            return {"content": "ok", "finish_reason": "stop"}

    async def call():
        scope = AttemptScope(Sink(), datetime.now(UTC) + timedelta(seconds=2), 1, 1)
        with attempt_scope(scope):
            return await invoke_attempt(Provider(), [])

    tasks = [asyncio.create_task(call()) for _ in range(MAX_OUTSTANDING)]
    try:
        await asyncio.sleep(0)
        assert len(started) == MAX_OUTSTANDING
        with pytest.raises(AttemptBudgetExceeded):
            await call()
    finally:
        gate.set()
        await asyncio.gather(*tasks)
    assert len(started) == MAX_OUTSTANDING


def test_terminal_action_closes_pending_attempt_atomically(setup_attempts):
    _, repo, action, _ = setup_attempts
    from backend.storage.research_receipts import ActionObservation, ProviderAttemptReceipt

    pending = ProviderAttemptReceipt(
        attempt_id="orphan",
        task_id="task",
        action_id=action.action_id,
        request_id="request",
        provider="nvidia",
        model="fixture",
        attempt_number=1,
        started_at=datetime.now(UTC),
    )
    repo.reserve(pending, 2)
    actions = ResearchActionReceiptRepository(repo._db_path)
    terminal = action.transition("failed", datetime.now(UTC), ActionObservation())
    actions.checkpoint(
        terminal,
        json.dumps(
            {
                "phase": "complete",
                "active_action_id": None,
                "action_journal_policy": {"contract_hash": "c", "policy_hash": "p"},
            }
        ),
    )
    attempt = repo.get("task", action.action_id, "orphan")
    assert attempt.outcome == "cancelled" and attempt.error_category == "action_ended"
    assert actions.get("task", action.action_id).observation.provider_attempts == (attempt,)
    with pytest.raises(ReceiptConflictError):
        repo.finish(attempt.model_copy(update={"outcome": "complete"}))
