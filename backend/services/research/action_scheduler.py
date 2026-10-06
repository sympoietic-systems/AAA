"""Finite routing guards grounded in persisted afferent content."""

from typing import Any

from backend.services.research.action_journal import input_hash

KINDS = frozenset(
    {
        "planning",
        "document_digestion",
        "searching",
        "parsing",
        "digesting",
        "consolidating",
        "reflection",
        "pure_reflection",
        "evaluating",
        "synthesizing",
    }
)
REFLECTION = frozenset({"reflection", "pure_reflection"})


class ActionPrerequisiteError(ValueError):
    """A requested finite action has no valid inputs or dependency."""


def enabled(state: dict[str, Any]) -> bool:
    policy = state.get("action_journal_policy") or {}
    return policy.get("enabled") is True and policy.get("scheduler_version") == 1


def boundary(state: dict[str, Any], afferent: list[dict[str, Any]]) -> str:
    """Typed anchor projection; model narration and access timestamps excluded."""
    return input_hash(
        {
            "contract_revision": state.get("contract_revision", 1),
            "anchors": sorted((item["content_hash"], tuple(item.get("segment_ids", []))) for item in afferent),
            "contrary_edges": sorted({witness for item in afferent for witness in item.get("cut_witnesses", [])}),
        }
    )


def reason(kind: str, state: dict[str, Any], afferent: list[dict[str, Any]]) -> str | None:
    if kind == "complete":
        return None
    if kind not in KINDS:
        return "unregistered_action"
    scheduler = state.get("scheduler_state") or {}
    if scheduler.get("actions", 0) >= 64:
        return "action_ceiling"
    if kind == "document_digestion" and not (state.get("inject_file_id") or state.get("injected_documents")):
        return "missing_document"
    if kind == "parsing" and not state.get("search_results_cache"):
        return "missing_candidates"
    if kind == "digesting" and not state.get("parsed_sources_cache"):
        return "missing_source_content"
    if kind == "consolidating" and not state.get("all_findings"):
        return "missing_findings"
    if kind in REFLECTION and scheduler.get("consecutive_reflections", 0):
        if scheduler["consecutive_reflections"] >= 2:
            return "reflection_ceiling"
        prior = set(scheduler.get("reflection_cut_witnesses", []))
        current = {witness for item in afferent for witness in item.get("cut_witnesses", [])}
        if not current - prior or boundary(state, afferent) == scheduler.get("reflection_boundary"):
            return "zero_afferent_cut_change"
    if kind in {"searching", "parsing", "digesting", "document_digestion"} and scheduler.get("no_progress", 0) >= 3:
        return "no_progress_ceiling"
    return None


def admit(kind: str, state: dict[str, Any], afferent: list[dict[str, Any]]) -> None:
    rejection = reason(kind, state, afferent)
    if rejection:
        raise ActionPrerequisiteError(rejection)
    scheduler = dict(state.get("scheduler_state") or {})
    scheduler["actions"] = scheduler.get("actions", 0) + 1
    scheduler["before_content_hashes"] = sorted({item["content_hash"] for item in afferent})
    if kind in REFLECTION:
        scheduler["consecutive_reflections"] = scheduler.get("consecutive_reflections", 0) + 1
        scheduler["reflection_content_hashes"] = scheduler["before_content_hashes"]
        scheduler["reflection_cut_witnesses"] = sorted(
            {witness for item in afferent for witness in item.get("cut_witnesses", [])}
        )
        scheduler["reflection_boundary"] = boundary(state, afferent)
        scheduler["reflection_afferent_refs"] = afferent
        scheduler["internal_pass_evidential_weight"] = 0
    else:
        scheduler["consecutive_reflections"] = 0
    state["scheduler_state"] = scheduler


def route(phase: str, requested: str, state: dict[str, Any], afferent: list[dict[str, Any]]) -> str:
    scheduler = dict(state.get("scheduler_state") or {})
    current = sorted({item["content_hash"] for item in afferent})
    if phase in {"parsing", "digesting", "document_digestion"}:
        scheduler["no_progress"] = (
            0 if set(current) - set(scheduler.get("before_content_hashes", [])) else scheduler.get("no_progress", 0) + 1
        )
    state["scheduler_state"] = scheduler
    rejection = reason(requested, state, afferent)
    selected = requested
    if rejection:
        selected = (
            "searching" if requested in REFLECTION and reason("searching", state, afferent) is None else "complete"
        )
        state["delivery_degraded"] = True
        state["stop_reason"] = rejection
    decisions = scheduler.get("decisions", [])
    scheduler["decisions"] = (
        decisions
        + [
            {
                "from": phase,
                "requested": requested,
                "selected": selected,
                "rejection": rejection,
                "afferent_refs": afferent,
                "boundary_hash": boundary(state, afferent),
            }
        ]
    )[-1:]
    return selected
