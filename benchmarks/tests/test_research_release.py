import pytest

from benchmarks.suites import research_release


def test_passing_regressions_cannot_certify_release_or_enable_auto():
    assessment = research_release.release_assessment(dict.fromkeys(research_release.CHECKS, "passed"))
    assert assessment["decision"] == "BLOCKED"
    assert not assessment["bounded_auto_allowed"]
    assert assessment["independent_quality"] is None
    assert assessment["known_cost_usd"] is None
    assert "independent_end_to_end_support_review_missing" in assessment["reasons"]


def test_missing_or_failed_checks_remain_visible():
    assessment = research_release.release_assessment({"backend_tests": "failed"})
    assert "backend_tests:failed" in assessment["reasons"]
    assert "research_tests:missing" in assessment["reasons"]


def test_reflection_uses_changed_cut_and_preserves_restart_guard():
    result = research_release.reflection_ablation()
    assert result["unguarded_requested_phase"] == "pure_reflection"
    assert result["guarded_unchanged_phase"] == "searching"
    assert result["guarded_changed_rejection"] is None
    assert result["restart_retained_scheduler"]


@pytest.mark.asyncio
async def test_comparison_rejects_coverage_loss(monkeypatch):
    async def differing(_):
        return {"baseline": {"coverage_hash": "one"}, "bounded_cold": {"coverage_hash": "two"}}

    monkeypatch.setattr(research_release, "replay", differing)
    with pytest.raises(ValueError, match="coverage"):
        await research_release.mechanical_comparison(
            {"queries": ["q"], "sources": [{}], "response_delay_seconds": 0}, 1
        )


@pytest.mark.asyncio
async def test_bounds_precede_replay(monkeypatch):
    async def forbidden(_):
        pytest.fail("No work before valid bounds")

    monkeypatch.setattr(research_release, "replay", forbidden)
    with pytest.raises(ValueError, match="repeats"):
        await research_release.mechanical_comparison({}, 4)


def test_skipped_or_missing_scenario_cannot_claim_verified(tmp_path):
    path = tmp_path / "results.xml"
    path.write_text(
        '<testsuite><testcase name="test_pool_leaf_failover_shares_request_and_records_each_attempt"><skipped/></testcase></testsuite>'
    )
    result = research_release.scenario_summary(path)
    assert result["outage_failover"] == "missing_or_failed"
    assert result["late_completion"] == "missing_or_failed"


def test_parameterized_failure_is_not_hidden_by_pass(tmp_path):
    path = tmp_path / "results.xml"
    name = research_release.SCENARIOS["branch_off"]
    path.write_text(
        f'<testsuite><testcase name="{name}[a]"/><testcase name="{name}[b]"><failure/></testcase></testsuite>'
    )
    assert research_release.scenario_summary(path)["branch_off"] == "missing_or_failed"


def test_authorized_rollout_requires_all_technical_checks_and_scenarios():
    checks = dict.fromkeys(research_release.CHECKS, "passed")
    scenarios = dict.fromkeys(research_release.SCENARIOS, "passed")
    result = research_release.release_assessment(checks, authorized_assumption_rollout=True, scenarios=scenarios)
    assert result["decision"] == "READY_FOR_AUTHORIZED_ROLLOUT"
    assert result["independent_quality"] is None
    assert result["quality_basis"] == "user_authorized_assumption"
    assert result["known_cost_usd"] is None
    checks["backend_tests"] = "failed"
    assert (
        research_release.release_assessment(checks, authorized_assumption_rollout=True, scenarios=scenarios)["decision"]
        == "BLOCKED"
    )
    assert (
        research_release.release_assessment(
            dict.fromkeys(research_release.CHECKS, "passed"), authorized_assumption_rollout=True
        )["decision"]
        == "BLOCKED"
    )
