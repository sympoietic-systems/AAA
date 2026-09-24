"""Single-step execution engine for the research pipeline."""

import asyncio
import contextlib
import json
import logging
from typing import Any

from backend.services.research.steps.base import ResearchStepRegistry
from backend.services.research.task_state import StepOutput

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

    async def execute(self, task_id: str) -> dict[str, Any]:
        orchestrator = self._orchestrator
        """Execute exactly ONE phase of the research pipeline.

        Returns unified debug info: inputs, outputs, prompts, next_phase.
        Persists orchestrator_state after every step.
        """
        if task_id not in orchestrator._state_mgr.locks:
            orchestrator._state_mgr.locks[task_id] = asyncio.Lock()

        async with orchestrator._state_mgr.locks[task_id]:
            s = orchestrator._get_state(task_id)
            phase = s["phase"]
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
                        orchestrator.task_repo.transition_status(task_id, "completed")
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

            try:
                # 2. Retrieve step from ResearchStepRegistry and execute
                step_processor = ResearchStepRegistry.get_step(phase)
                logger.info("Executing modular step: %s", phase)
                output: StepOutput = await step_processor.execute(orchestrator, envelope)

                # Merge findings
                if output.new_findings:
                    s["all_findings"].extend(output.new_findings)

                # Apply output payloads back to legacy task state dict
                orchestrator.apply_step_output(s, phase, output)

                # Metabolize research findings into belief system
                await orchestrator._metabolize_step(task_id, phase, output.new_findings or [])

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
                s["phase"] = next_phase

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
                                step_data["next_phase"] = next_phase
                                orchestrator.step_repo.update(
                                    sid, step_data=json.dumps(step_data, default=str, ensure_ascii=False)
                                )
                        except Exception as ex:
                            logger.warning("Failed to update transition rationale for step %s: %s", sid, ex)

            except Exception as e:
                logger.exception("Step %s failed for task %s", phase, task_id)

                # Mark running steps as failed so they're visible in the UI for rerun
                if orchestrator.step_repo:
                    try:
                        all_steps = orchestrator.step_repo.get_by_task(task_id) or []
                        for st in all_steps:
                            if st["status"] == "running":
                                orchestrator.step_repo.update(
                                    st["id"], status="failed", result_summary=f"Step failed: {e}"
                                )
                    except Exception:
                        pass

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
            result["accumulated_findings"] = len(s.get("all_findings", []))

            # Persist state to DB after every step
            orchestrator._persist_state(task_id)

            return result

    # ── Sedimentation Crystallization ──────────────────────────────────
