from __future__ import annotations

import pytest

from benchmarks.suites.telemetry.causal_intervention import (
    Mode,
    Signals,
    mode_reachability_fixtures,
    new_trial,
    receipt_json,
)


def test_t37_each_selector_mode_has_satisfiable_fixture() -> None:
    fixtures = mode_reachability_fixtures()
    assert set(fixtures) == set(Mode)
    for expected, signals in fixtures.items():
        trial = new_trial(f"reach-{expected.value}", "current")
        receipt = trial.select(signals)
        assert receipt["mode"] == expected.value
        assert isinstance(receipt["predicate_id"], str)
        assert receipt["coverage"] == {expected.value: 1}


def test_t37_sham_writes_without_read_and_matches_current_outcome() -> None:
    signals = Signals(falsifiable=True, terms_clear=True)
    trials = {arm: new_trial(f"conversation-{arm}", arm) for arm in ("current", "sham")}
    for trial in trials.values():
        trial.start_issue("issue-1", "Can this claim be falsified?")
    current = trials["current"].select(signals)
    sham = trials["sham"].select(signals)
    assert current["mode"] == sham["mode"]
    assert current["predicate_id"] == sham["predicate_id"]
    assert current["memory_written"] is False
    assert current["memory_read"] is False
    assert sham["memory_written"] is True
    assert sham["memory_read"] is False


def test_t37_only_active_arm_reads_carried_issue_memory() -> None:
    signals = Signals(falsifiable=True, terms_clear=True)
    trials = {arm: new_trial(f"conversation-{arm}", arm) for arm in ("sham", "active")}
    for trial in trials.values():
        trial.start_issue("issue-1", "Can this claim be falsified?")
    sham = trials["sham"].select(signals)
    active = trials["active"].select(signals)
    assert sham["memory_written"] is True and sham["memory_read"] is False
    assert active["memory_written"] is True and active["memory_read"] is True
    assert active["predicate_id"] == "P-CARRIED-ISSUE"
    assert active["mode"] == "counterexample"
    assert active["issue_digest"] == sham["issue_digest"]
    assert "Can this claim" not in receipt_json(active)


def test_t37_issue_progress_and_terminal_cleanup_are_bounded() -> None:
    trial = new_trial("bounded", "active", max_turns=2)
    trial.start_issue("issue-1", "bounded issue")
    first = trial.select(Signals(issue_advanced=True))
    assert first["issue_version"] == 0
    assert trial.issue is not None and trial.issue.version == 1
    assert trial.issue.status == "advanced"
    trial.close("resolved")
    assert not trial.active and trial.carried_memory is None
    assert trial.issue is not None and trial.issue.status == "resolved"
    with pytest.raises(RuntimeError, match="terminal"):
        trial.select(Signals())


@pytest.mark.parametrize("max_turns", [0, 129])
def test_t37_trial_turn_limit_is_clamped(max_turns: int) -> None:
    with pytest.raises(ValueError, match="max_turns"):
        new_trial("bounded", "current", max_turns=max_turns)


def test_t37_issue_payload_is_bounded_before_hashing() -> None:
    trial = new_trial("bounded", "current")
    with pytest.raises(ValueError, match="8192"):
        trial.start_issue("issue-1", "x" * 8193)
