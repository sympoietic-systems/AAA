"""Single-step execution engine for the research pipeline."""

import asyncio
import contextlib
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any, cast

from backend.modules.provider_attempts import AttemptBudgetExceeded, bounded_call
from backend.services.research import action_scheduler
from backend.services.research.action_journal import ResearchActionJournal
from backend.services.research.provider_observation import ProviderObservations, observe_provider_calls
from backend.services.research.steps.base import ResearchStepRegistry
from backend.services.research.task_state import StepOutput
from backend.storage.repositories.research.provider_attempt import ResearchProviderAttemptRepository
from backend.storage.research_receipts import ActionStatus, EvidencePacket, ResearchActionReceipt

logger = logging.getLogger("aaa.research_orchestrator")


class ResearchStepExecutor:
    """Advance one persisted research phase through the orchestrator facade."""

    def __init__(
        self,
        orchestrator: Any,
        pipeline_graph: dict[str, list[Any]],
        phase_block: dict[str, str],
        phase_sub_sequence: dict[str, int],
    ) -> None:
        self._orchestrator = orchestrator
        self._pipeline_graph = pipeline_graph
        self._phase_block = phase_block
        self._phase_sub_sequence = phase_sub_sequence

    METABOLISM_TIMEOUT_SECONDS = 15.0

    async def _metabolize_bounded(self, task_id: str, phase: str, findings: list[str], state: dict[str, Any]) -> bool:
        """Optional belief processing cannot consume the remaining research window."""
        if not findings or state.get("research_child"):
            return True
        timeout = self.METABOLISM_TIMEOUT_SECONDS
        deadline = ((state.get("action_journal_policy") or {}).get("provider_policy") or {}).get("deadline")
        if deadline:
            timeout = min(timeout, (datetime.fromisoformat(deadline) - datetime.now(UTC)).total_seconds())
        reason = "deadline_exhausted"
        if timeout > 0:
            try:
                await bounded_call(lambda: self._orchestrator._metabolize_step(task_id, phase, findings), timeout)
                return True
            except AttemptBudgetExceeded as exc:
                reason = "execution_capacity" if "capacity exhausted" in str(exc) else "timeout"
        logger.warning("Research belief processing skipped: task=%s phase=%s reason=%s", task_id, phase, reason)
        await asyncio.to_thread(
            self._orchestrator._log_meta,
            task_id,
            "research_metabolism_incomplete",
            {"phase": phase, "reason": reason, "timeout_seconds": max(0, timeout)},
        )
        return False

    async def _resolve_dispatch_consent(self, task_id: str, state: dict[str, Any]) -> None:
        if (
            state.get("phase") != "waiting_for_branch_approval"
            or (state.get("action_journal_policy") or {}).get("subresearch_policy") != "bounded_auto"
        ):
            return
        from backend.storage.repositories.research.branch_proposal import ResearchBranchProposalRepository

        orchestrator = self._orchestrator
        repo = ResearchBranchProposalRepository(orchestrator.task_repo._db_path)
        await asyncio.to_thread(
            repo.resolve,
            task_id,
            state["pending_branch_proposal_id"],
            "approved",
            boundary_acknowledged=True,
            manual=True,
            from_dispatch_covenant=True,
        )
        task = await asyncio.to_thread(orchestrator.task_repo.get, task_id)
        state.update(json.loads(task["orchestrator_state"]))

    async def execute(self, task_id: str) -> dict[str, Any]:
        orchestrator = self._orchestrator
        """Execute exactly ONE phase of the research pipeline.

        Returns unified debug info: inputs, outputs, prompts, next_phase.
        Persists orchestrator_state after every step.
        """
        if task_id not in orchestrator._state_mgr.locks:
            orchestrator._state_mgr.locks[task_id] = asyncio.Lock()

        async with orchestrator._state_mgr.locks[task_id]:
            s = await asyncio.to_thread(orchestrator._get_state, task_id)
            await self._resolve_dispatch_consent(task_id, s)
            phase = s["phase"]
            if phase == "waiting_for_branch_approval":
                return {
                    "task_id": task_id,
                    "phase": phase,
                    "next_phase": phase,
                    "status": phase,
                    "proposal_id": s.get("pending_branch_proposal_id"),
                }
            logger.info(
                "execute_step: phase=%s, depth=%s, phase_group=%s", phase, s.get("current_depth"), s.get("phase_group")
            )

            # ── Block tracking: advance phase_group when entering a new block ──
            block = self._phase_block.get(phase, phase)
            if s.get("last_block") != block:
                s["phase_group"] = s.get("phase_group", 0) + 1
                s["last_block"] = block
            s["sub_sequence"] = self._phase_sub_sequence.get(phase, 0)

            # ── Rerun: delete downstream steps using composite-key scoping ──
            rerun_id = s.pop("_rerun_step_id", None)
            if rerun_id and orchestrator.step_repo:
                rerun_step = orchestrator.step_repo.get(rerun_id)
                if rerun_step:
                    r_pg = rerun_step.get("phase_group", 0)
                    r_qg = rerun_step.get("query_group", 0)
                    r_ss = rerun_step.get("sub_sequence", 0)
                    all_steps = orchestrator.step_repo.get_by_task(task_id)
                    deleted = 0
                    for st in all_steps:
                        spg = st.get("phase_group", 0)
                        sqg = st.get("query_group", 0)
                        sss = st.get("sub_sequence", 0)
                        drop = False
                        if r_qg == 0:
                            # Cycle-level step: delete all later phase_groups
                            if spg > r_pg:
                                drop = True
                        else:
                            # Query substep: subtree scope — same (PG, QG), higher SS
                            if spg == r_pg and sqg == r_qg and sss > r_ss:
                                drop = True
                        if drop:
                            try:
                                orchestrator.step_repo.delete(st["id"])
                                deleted += 1
                            except Exception:
                                pass
                    if deleted:
                        logger.info(
                            "Rerun: deleted %d downstream steps from (pg=%d,qg=%d,ss=%d) — %s",
                            deleted,
                            r_pg,
                            r_qg,
                            r_ss,
                            orchestrator._log_context(task_id, "rerun"),
                        )
                # Clear the rerun flag used for doc digestion
                s["document_digested"] = False
                s["document_learnings"] = []

            if phase == "complete":
                # Safety: force-complete the DB task if it's still stuck at "active"
                try:
                    db_task = orchestrator.task_repo.get(task_id)
                    if db_task and db_task.get("status") == "active":
                        logger.warning(
                            "execute_step called with phase=complete but task %s still active — "
                            "force-transitioning to completed to break stuck loop",
                            task_id[:8],
                        )
                        orchestrator.task_repo.transition_status(
                            task_id, "partial" if s.get("delivery_degraded") else "completed"
                        )
                        result_summary = s.get("result_summary") or db_task.get("result_summary") or ""
                        orchestrator.task_repo.update(task_id, result_summary=result_summary)
                except Exception as e:
                    logger.warning("Failed to force-complete stuck task %s: %s", task_id[:8], e)
                return {"task_id": task_id, "phase": phase, "message": "already complete", "next_phase": "complete"}

            # 1. Reconstruct clean typed StepEnvelope
            envelope = orchestrator.reconstruct_step_input(task_id, s, phase)

            result: dict[str, Any] = {
                "task_id": task_id,
                "phase": phase,
                "query_index": s.get("query_index", 0),
                "current_depth": s.get("current_depth", 0),
            }

            journal = cast(ResearchActionJournal | None, getattr(orchestrator, "_action_journal", None))
            receipt: ResearchActionReceipt | None = None
            journal_enabled = bool((s.get("action_journal_policy") or {}).get("enabled", False))
            if journal_enabled:
                if journal is None:
                    raise RuntimeError("Receipt-enabled task requires a durable action journal")
                # Validate capability before recording or executing any action.
                ResearchStepRegistry.get_step(phase)
                if action_scheduler.enabled(s):
                    from backend.storage.repositories.research.evidence import ResearchEvidenceRepository

                    afferent = await asyncio.to_thread(
                        ResearchEvidenceRepository(journal.repo._db_path).afferent_snapshot, task_id
                    )
                    action_scheduler.admit(phase, s, afferent)
                receipt = await asyncio.to_thread(journal.begin, task_id, s, phase, envelope.model_dump(mode="json"))
                result["action_id"] = receipt.action_id
            phase_started = time.perf_counter()
            output_refs: tuple[str, ...] = ()
            action_status: ActionStatus = "failed"
            useful = False
            provider_attempts = ProviderObservations()
            evidence_packets: tuple[EvidencePacket, ...] = ()

            try:
                # 2. Retrieve step from ResearchStepRegistry and execute
                step_processor = ResearchStepRegistry.get_step(phase)
                logger.info("Executing modular step: %s", phase)
                policy = (s.get("action_journal_policy") or {}).get("provider_policy")
                attempt_repo = (
                    ResearchProviderAttemptRepository(journal.repo._db_path) if receipt and journal and policy else None
                )
                with observe_provider_calls(receipt, attempt_repo, policy) as provider_attempts:
                    if receipt is not None and policy:
                        remaining = (datetime.fromisoformat(policy["deadline"]) - datetime.now(UTC)).total_seconds()
                        output: StepOutput = await bounded_call(
                            lambda: step_processor.execute(orchestrator, envelope), remaining
                        )
                    else:
                        output = await step_processor.execute(orchestrator, envelope)
                output_refs = tuple(output.step_ids)
                evidence_packets = output.evidence_packets
                action_status = (
                    "complete"
                    if output.status == "completed"
                    else "partial"
                    if output.status == "partial"
                    else "failed"
                )
                useful = (phase in {"digesting", "document_digestion"} and bool(output.new_findings)) or (
                    phase == "parsing" and output.signal_flags.get("has_parsed_content", False)
                )

                # Merge findings
                acquisition_degraded = False
                if receipt is not None and journal is not None:
                    from backend.storage.repositories.research.acquisition import ResearchAcquisitionRepository

                    acquisition_records = await asyncio.to_thread(
                        ResearchAcquisitionRepository(journal.repo._db_path).list_action, task_id, receipt.action_id
                    )
                    acquisition_degraded = any(
                        item.outcome in {"pending", "failed", "cancelled", "unavailable"}
                        for item in acquisition_records
                    )
                if action_status == "complete" and (
                    acquisition_degraded
                    or output.signal_flags.get("acquisition_degraded", False)
                    or getattr(provider_attempts, "delivery_failed", False)
                    or any(a.truncated or a.outcome in {"failed", "cancelled", "partial"} for a in provider_attempts)
                ):
                    action_status = "partial"
                if receipt is not None and action_status == "partial":
                    s["delivery_degraded"] = True
                if output.new_findings:
                    output.new_findings = list(
                        dict.fromkeys(finding for finding in output.new_findings if finding not in s["all_findings"])
                    )
                    s["all_findings"].extend(output.new_findings)

                # Apply output payloads back to legacy task state dict
                orchestrator.apply_step_output(s, phase, output)

                # Metabolize research findings into belief system
                if not await self._metabolize_bounded(task_id, phase, output.new_findings or [], s):
                    s["delivery_degraded"] = True
                    action_status = "partial"

                result.update(
                    {
                        "status": output.status,
                        "message": output.message,
                    }
                )
                if hasattr(output.payload, "result_summary") and output.payload.result_summary:
                    result["result_summary"] = output.payload.result_summary

                # Ingest dynamic routing patches emitted by the step output
                if hasattr(output, "routing_patches") and output.routing_patches:
                    s["active_routing_patches"] = s.get("active_routing_patches", [])
                    for patch in output.routing_patches:
                        patch_dict = patch.model_dump()
                        if action_scheduler.enabled(s) and (
                            patch.action != "override"
                            or patch.target_phase not in action_scheduler.KINDS
                            or patch.source_phase not in action_scheduler.KINDS
                            or not 1 <= patch.ttl <= 3
                        ):
                            raise action_scheduler.ActionPrerequisiteError("Invalid finite routing patch")
                        s["active_routing_patches"].append(patch_dict)
                        logger.info(
                            "Ingested RoutingPatch: %s -> %s (action=%s, ttl=%s)",
                            patch_dict.get("source_phase"),
                            patch_dict.get("target_phase"),
                            patch_dict.get("action"),
                            patch_dict.get("ttl"),
                        )

                # Determine next phase via Declarative Membrane (self._pipeline_graph + Active Routing Patches)
                next_phase = "complete"
                patch_applied = False

                # 1. Evaluate Active Routing Patches with Safety Integrity Guards
                active_patches = s.get("active_routing_patches", [])
                remaining_patches = []
                for patch in active_patches:
                    src = patch.get("source_phase")
                    tgt = patch.get("target_phase")
                    cond_flag = patch.get("condition_flag")
                    ttl = patch.get("ttl", 1)

                    # Safety Integrity Guards:
                    # - Cannot override terminal phases (synthesizing, complete)
                    # - Cannot reroute more than max_patch_reroutes limit
                    reroute_count = s.get("patch_reroute_count", 0)
                    if (
                        not patch_applied
                        and src == phase
                        and tgt not in ("synthesizing", "complete")
                        and phase not in ("synthesizing", "complete")
                        and reroute_count < 3
                        and (not cond_flag or output.signal_flags.get(cond_flag, False))
                    ):
                        next_phase = tgt
                        patch_applied = True
                        s["patch_reroute_count"] = reroute_count + 1
                        logger.info(
                            "Plasticity Patch applied: phase=%s -> %s via patch (flag=%s, reroutes=%d)",
                            phase,
                            tgt,
                            cond_flag,
                            s["patch_reroute_count"],
                        )
                        ttl -= 1

                    if ttl > 0:
                        patch["ttl"] = ttl
                        remaining_patches.append(patch)

                s["active_routing_patches"] = remaining_patches

                # 2. Fallback to Static self._pipeline_graph if no dynamic patch matched
                if not patch_applied:
                    for transition in self._pipeline_graph.get(phase, []):
                        if transition.condition(output, envelope):
                            next_phase = transition.target_phase
                            break
                if s.get("research_child"):
                    next_phase = {
                        "searching": "parsing" if output.signal_flags.get("has_results") else "complete",
                        "parsing": "digesting" if output.signal_flags.get("has_parsed_content") else "complete",
                        "digesting": "complete",
                    }.get(phase, "complete")
                if action_scheduler.enabled(s):
                    assert journal is not None
                    from backend.storage.repositories.research.evidence import ResearchEvidenceRepository

                    afferent = await asyncio.to_thread(
                        ResearchEvidenceRepository(journal.repo._db_path).afferent_snapshot, task_id
                    )
                    next_phase = action_scheduler.route(phase, next_phase, s, afferent)
                    result["scheduler_decision"] = s["scheduler_state"]["decisions"][-1]
                s["phase"] = next_phase
                if (
                    output.branch_proposal
                    and not s.get("branch_review_complete")
                    and (s.get("action_journal_policy") or {}).get("subresearch_policy", "off")
                    in {"propose", "bounded_auto"}
                ):
                    assert receipt is not None and journal is not None
                    import uuid
                    from datetime import timedelta

                    from backend.storage.repositories.research.branch_proposal import ResearchBranchProposalRepository
                    from backend.storage.research_branch_proposal import BranchProposal

                    proposal = BranchProposal(
                        proposal_id=str(uuid.uuid4()),
                        task_id=task_id,
                        action_id=receipt.action_id,
                        parent_objective=s["objective"],
                        draft=output.branch_proposal,
                        created_at=datetime.now(UTC),
                        expires_at=min(
                            datetime.now(UTC) + timedelta(seconds=120),
                            datetime.fromisoformat(s["action_journal_policy"]["provider_policy"]["deadline"]),
                        ),
                        resume_phase=next_phase,
                    )
                    await asyncio.to_thread(ResearchBranchProposalRepository(journal.repo._db_path).create, proposal)
                    s["pending_branch_proposal_id"] = proposal.proposal_id
                    s["phase"] = "waiting_for_branch_approval"
                    result["status"] = "waiting_for_branch_approval"
                    result["proposal_id"] = proposal.proposal_id

                if next_phase == "planning":
                    if phase == "evaluating":
                        s["query_index"] = 0
                        logger.info(
                            "Transitioning from evaluating back to planning. current_depth is %d", s["current_depth"]
                        )
                    try:
                        cache = orchestrator._load_cache(task_id)
                        if "planning" in cache:
                            del cache["planning"]
                            orchestrator._save_cache(task_id, cache)
                            logger.info("Cleared planning cache for task %s to force fresh replan.", task_id[:8])
                    except Exception as e:
                        logger.warning("Failed to clear planning cache for task %s: %s", task_id[:8], e)

                # Save transition rationale and next phase to step_data JSON
                if orchestrator.step_repo and hasattr(output, "step_ids") and output.step_ids:
                    rationale = (
                        getattr(output, "transition_rationale", None) or f"Transitioning from {phase} to {next_phase}."
                    )
                    for sid in output.step_ids:
                        try:
                            db_step = orchestrator.step_repo.get(sid)
                            if db_step:
                                step_data = {}
                                if db_step.get("step_data"):
                                    with contextlib.suppress(Exception):
                                        step_data = (
                                            json.loads(db_step["step_data"])
                                            if isinstance(db_step["step_data"], str)
                                            else db_step["step_data"]
                                        )
                                step_data["transition_rationale"] = rationale
                                step_data["next_phase"] = s["phase"]
                                orchestrator.step_repo.update(
                                    sid, step_data=json.dumps(step_data, default=str, ensure_ascii=False)
                                )
                        except Exception as ex:
                            logger.warning("Failed to update transition rationale for step %s: %s", sid, ex)

            except asyncio.CancelledError:
                if receipt is not None:
                    assert journal is not None
                    await asyncio.to_thread(
                        journal.finish,
                        receipt,
                        s,
                        "cancelled",
                        output_refs,
                        time.perf_counter() - phase_started,
                        useful,
                        tuple(provider_attempts),
                        evidence_packets,
                    )
                raise
            except Exception as e:
                action_status = "failed"
                logger.exception("Step %s failed for task %s", phase, task_id)

                # Mark running steps as failed so they're visible in the UI for rerun
                if orchestrator.step_repo:
                    try:
                        all_steps = await asyncio.to_thread(orchestrator.step_repo.get_by_task, task_id) or []
                        failed_type = ResearchStepRegistry.get_step(phase).step_type
                        current_steps = [
                            st
                            for st in all_steps
                            if st.get("phase_group") == s.get("phase_group") and st.get("step_type") == failed_type
                        ]
                        if not current_steps:
                            failed_id = await asyncio.to_thread(
                                orchestrator._create_or_update_step, s, task_id, failed_type
                            )
                            current_steps = [{"id": failed_id, "status": "running"}]
                            output_refs = (failed_id,)
                        for st in current_steps:
                            if st.get("status") not in {"running", "failed"}:
                                continue
                            await asyncio.to_thread(
                                orchestrator.step_repo.update,
                                st["id"],
                                status="failed",
                                result_summary=f"Step failed: {e}",
                            )
                    except Exception:
                        logger.exception("Failed to persist failed phase row for task %s phase %s", task_id, phase)

                # Force phase to complete so the while-loop exits.
                # But preserve the failing phase name so the caller knows which step failed.
                s["phase"] = "complete"
                s["_failed_phase"] = phase
                result.update(
                    {
                        "status": "error",
                        "message": f"Step '{phase}' failed: {e}",
                        "failed_phase": phase,
                    }
                )
                orchestrator.task_repo.update(task_id, status="failed", result_summary=f"Step '{phase}' failed: {e}")

            result["next_phase"] = s["phase"]
            if receipt is not None and s.get("delivery_degraded"):
                result["delivery_status"] = "partial"
                if s["phase"] == "complete" and action_status != "failed":
                    action_status = "partial"
                    result["status"] = "partial"
            result["accumulated_findings"] = len(s.get("all_findings", []))

            # Persist state to DB after every step
            if receipt is not None:
                assert journal is not None
                await asyncio.to_thread(
                    journal.finish,
                    receipt,
                    s,
                    action_status,
                    output_refs,
                    time.perf_counter() - phase_started,
                    useful,
                    tuple(provider_attempts),
                    evidence_packets,
                )
            else:
                orchestrator._persist_state(task_id)
            if (
                s["phase"] == "waiting_for_branch_approval"
                and (s.get("action_journal_policy") or {}).get("subresearch_policy") == "bounded_auto"
            ):
                await self._resolve_dispatch_consent(task_id, s)
                result["next_phase"] = s["phase"]
                result["status"] = "active" if s["phase"] != "complete" else "partial"
                result["branch_authorization"] = "dispatch_covenant"
            if s["phase"] == "waiting_for_branch_approval":
                manager = getattr(orchestrator._state, "research_task_manager", None)
                if manager is not None:
                    await manager.start_branch_watch(force=True)

            return result

    # ── Sedimentation Crystallization ──────────────────────────────────
