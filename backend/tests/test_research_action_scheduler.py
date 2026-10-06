import json

import pytest

from backend.services.research import action_scheduler as scheduler
from backend.services.research.envelope_mapper import ResearchEnvelopeMapper
from backend.services.research.task_state import (
    ReflectionPayload,
    StepOutput,
    make_initial_state,
    serialize_research_state,
)


def state():
    return {
        "objective": "Check disputed mechanism",
        "contract_revision": 1,
        "action_journal_policy": {"enabled": True, "scheduler_version": 1},
    }


def trace(content="abc", version="1"):
    return [
        {
            "source_id": "source",
            "source_version": version,
            "content_hash": content,
            "segment_ids": [content],
            "acquisition_id": "durable-origin",
        }
    ]


def test_v111_framing_then_narration_only_routes_to_acquisition():
    s = state()
    scheduler.admit("reflection", s, trace())
    s["refined_queries"] = ["A model authored rewording"]
    assert scheduler.route("reflection", "pure_reflection", s, trace()) == "searching"
    assert s["scheduler_state"]["decisions"][-1]["rejection"] == "zero_afferent_cut_change"
    assert s["scheduler_state"]["internal_pass_evidential_weight"] == 0


def test_v111_refetch_same_content_cannot_warrant_second_reflection():
    s = state()
    scheduler.admit("reflection", s, trace())
    assert scheduler.reason("pure_reflection", s, trace(version="2")) == "zero_afferent_cut_change"


def test_v111_new_anchor_content_permits_second_but_never_third():
    s = state()
    scheduler.admit("reflection", s, trace())
    changed = trace() + trace("new", "2")
    changed[1]["cut_witnesses"] = ["contradiction:new-content-hash"]
    scheduler.admit("pure_reflection", s, changed)
    assert scheduler.reason("reflection", s, changed + trace("third", "3")) == "reflection_ceiling"


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("arbitrary", "unregistered_action"),
        ("parsing", "missing_candidates"),
        ("digesting", "missing_source_content"),
        ("consolidating", "missing_findings"),
        ("document_digestion", "missing_document"),
    ],
)
def test_v110_prerequisites_reject_before_work(kind, expected):
    with pytest.raises(scheduler.ActionPrerequisiteError, match=expected):
        scheduler.admit(kind, state(), [])


def test_v112_action_and_no_progress_ceilings_force_partial():
    s = state()
    s["scheduler_state"] = {"actions": 64}
    assert scheduler.route("evaluating", "planning", s, []) == "complete"
    assert s["delivery_degraded"]
    s = state()
    s["scheduler_state"] = {"no_progress": 2}
    assert scheduler.route("digesting", "searching", s, []) == "complete"
    assert s["stop_reason"] == "no_progress_ceiling"


def test_v116_scheduler_and_routing_survive_restart():
    s = state()
    scheduler.admit("reflection", s, trace())
    s["active_routing_patches"] = [{"target_phase": "searching"}]
    s["patch_reroute_count"] = 2
    raw = serialize_research_state(s)
    restarted = make_initial_state(
        {"objective": s["objective"], "max_depth": 3, "budget_limit_usd": 0.5, "orchestrator_state": raw}
    )
    assert restarted["scheduler_state"] == s["scheduler_state"]
    assert restarted["active_routing_patches"] == s["active_routing_patches"]
    assert restarted["patch_reroute_count"] == 2
    assert scheduler.reason("reflection", restarted, trace()) == "zero_afferent_cut_change"
    assert json.loads(raw)["scheduler_state"]["actions"] == 1


def test_v112_pure_reflection_mapping_preserves_critique_and_disagreement():
    s = state()
    s.update(
        critique_log=[{"contrary": "keep"}],
        diffractive_audit="SUBSTANTIVE",
        diffractive_audit_description="disagreement remains",
    )
    envelope = ResearchEnvelopeMapper.reconstruct_step_input("task", s, "pure_reflection")
    assert isinstance(envelope.payload, ReflectionPayload)
    assert envelope.payload.critique_log == s["critique_log"]
    ResearchEnvelopeMapper.apply_step_output(s, "pure_reflection", StepOutput(payload=envelope.payload))
    assert s["diffractive_audit_description"] == "disagreement remains"


def test_v111_new_content_without_category_failure_does_not_warrant_reflection():
    s = state()
    scheduler.admit("reflection", s, trace())
    assert scheduler.reason("pure_reflection", s, trace() + trace("new", "2")) == "zero_afferent_cut_change"
