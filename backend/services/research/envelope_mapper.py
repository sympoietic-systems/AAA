"""Research Envelope Mapper — Data mapping between legacy state dict and typed StepEnvelope/StepOutput."""

from backend.services.research.task_state import (
    ConsolidatePayload,
    DigestPayload,
    DocDigestPayload,
    EvaluatePayload,
    InjectedDocumentSpec,
    ParsePayload,
    PlanPayload,
    ReflectionPayload,
    SearchPayload,
    StepEnvelope,
    StepOutput,
    SynthesizePayload,
)


class ResearchEnvelopeMapper:
    """Translates orchestrator legacy state dictionaries to and from typed StepEnvelope / StepOutput objects."""

    @staticmethod
    def reconstruct_step_input(task_id: str, task_state: dict, phase: str) -> StepEnvelope:
        """Constructs the clean, typed StepEnvelope for the current phase using task state."""
        envelope_data = {
            "task_id": task_id,
            "objective": task_state["objective"],
            "current_depth": task_state.get("current_depth", 0),
            "max_depth": task_state.get("max_depth", 3),
            "budget": task_state.get("budget", 0.50),
            "all_findings": task_state.get("all_findings") or [],
            "digest_signals": task_state.get("digest_signals") or {},
            "inject_file_id": task_state.get("inject_file_id"),
            "document_digested": task_state.get("document_digested", False),
            "plan_id": task_state.get("plan_id"),
        }

        # Build step-specific payload
        if phase == "planning":
            payload = PlanPayload(
                previous_context=task_state.get("previous_context"),
                inject_file_id=task_state.get("inject_file_id"),
            )
        elif phase == "document_digestion":
            raw_docs = task_state.get("injected_documents") or []
            doc_specs = []
            for d in raw_docs:
                if isinstance(d, dict):
                    doc_specs.append(InjectedDocumentSpec(**d))
                elif isinstance(d, InjectedDocumentSpec):
                    doc_specs.append(d)

            payload = DocDigestPayload(
                inject_file_id=task_state.get("inject_file_id"),
                inject_conversation_id=task_state.get("inject_conversation_id"),
                document_mode=task_state.get("document_mode", "chunks"),
                document_chunk_limit=task_state.get("document_chunk_limit", 5),
                documents=doc_specs,
            )
        elif phase == "searching":
            plan_queries = []
            if task_state.get("plan") and isinstance(task_state["plan"], dict):
                plan_queries = task_state["plan"].get("search_queries", [task_state["objective"]])

            last_refl = task_state.get("last_reflection") or {}
            queries = (
                last_refl.get("next_queries")
                if (task_state.get("current_depth", 0) > 0 and last_refl.get("next_queries"))
                else plan_queries
            )
            direct_urls = last_refl.get("next_direct_urls", []) if task_state.get("current_depth", 0) > 0 else []

            payload = SearchPayload(queries=queries, direct_urls=direct_urls)
        elif phase == "parsing":
            search_results = task_state.get("search_results_cache") or []
            payload = ParsePayload(search_results_cache=search_results)
        elif phase == "digesting":
            parsed_sources = task_state.get("parsed_sources_cache") or []
            payload = DigestPayload(parsed_sources_cache=parsed_sources)
        elif phase == "consolidating":
            payload = ConsolidatePayload(last_reflection=task_state.get("last_reflection") or {})
        elif phase == "reflection":
            payload = ReflectionPayload(
                reflection_notes=task_state.get("reflection_notes", ""),
                detected_biases=task_state.get("detected_biases", []),
                knowledge_gaps=task_state.get("knowledge_gaps", []),
                glitch_fidelity=task_state.get("glitch_fidelity", 1.0),
                contradiction_density=task_state.get("contradiction_density", 0.0),
                source_entropy=task_state.get("source_entropy", 0.0),
                signal_flags=task_state.get("signal_flags", []),
                refined_queries=task_state.get("refined_queries", []),
                revised_confidence=task_state.get("revised_confidence", 0.5),
                monologue_trace=task_state.get("monologue_trace", []),
            )
        elif phase == "evaluating":
            payload = EvaluatePayload(
                stagnation_counter=task_state.get("stagnation_counter", 0),
                sources_analyzed=task_state.get("sources_analyzed", 0),
                reflection=task_state.get("last_reflection") or {},
            )
        elif phase == "synthesizing":
            payload = SynthesizePayload(sources_analyzed=task_state.get("sources_analyzed", 0))
        else:
            raise ValueError(f"Unknown phase payload reconstruction: {phase}")

        return StepEnvelope(payload=payload, **envelope_data)

    @staticmethod
    def apply_step_output(task_state: dict, phase: str, output: StepOutput) -> None:
        """Applies a StepOutput's payload back to the legacy task state dictionary."""
        payload = output.payload
        if phase == "planning" and isinstance(payload, PlanPayload):
            task_state["plan"] = {
                "goal": payload.goal or task_state["objective"],
                "search_queries": payload.search_queries,
                "n_results_per_query": payload.n_results_per_query,
                "estimated_depth": payload.estimated_depth,
            }
            if output.signal_flags.get("plan_id"):
                task_state["plan_id"] = output.signal_flags["plan_id"]
        elif phase == "document_digestion" and isinstance(payload, DocDigestPayload):
            task_state["document_digested"] = True
            task_state["document_learnings"] = payload.learnings
            # Merge digest signals
            existing_signals = task_state.get("digest_signals") or {}
            task_state["digest_signals"] = {
                "followups": (existing_signals.get("followups") or []) + payload.followups,
                "direct_urls": existing_signals.get("direct_urls") or [],
                "gaps": (existing_signals.get("gaps") or []) + payload.gaps,
            }
            task_state["sources_analyzed"] = task_state.get("sources_analyzed", 0) + 1
        elif phase == "searching" and isinstance(payload, SearchPayload):
            task_state["search_results_cache"] = payload.search_results
            task_state["parsed_sources_cache"] = []
        elif phase == "parsing" and isinstance(payload, ParsePayload):
            task_state["parsed_sources_cache"] = payload.parsed_sources
        elif phase == "digesting" and isinstance(payload, DigestPayload):
            task_state["sources_analyzed"] = task_state.get("sources_analyzed", 0) + len(payload.parsed_sources_cache)
            if not payload.learnings:
                task_state["stagnation_counter"] = task_state.get("stagnation_counter", 0) + 1
            else:
                task_state["stagnation_counter"] = 0
            # Merge followups/gaps
            task_state["digest_signals"] = {
                "followups": payload.followups,
                "direct_urls": [],
                "gaps": payload.gaps,
            }
        elif phase == "consolidating" and isinstance(payload, ConsolidatePayload):
            task_state["last_reflection"] = {
                "completeness_score": payload.completeness_score,
                "key_insights": payload.key_insights,
                "remaining_gaps": payload.remaining_gaps,
                "next_queries": payload.next_queries,
                "next_direct_urls": payload.next_direct_urls,
            }
        elif phase == "reflection" and isinstance(payload, ReflectionPayload):
            task_state["reflection_notes"] = payload.reflection_notes
            task_state["detected_biases"] = payload.detected_biases
            task_state["knowledge_gaps"] = payload.knowledge_gaps
            task_state["glitch_fidelity"] = payload.glitch_fidelity
            task_state["contradiction_density"] = payload.contradiction_density
            task_state["source_entropy"] = payload.source_entropy
            task_state["signal_flags"] = payload.signal_flags
            task_state["refined_queries"] = payload.refined_queries
            task_state["revised_confidence"] = payload.revised_confidence
            task_state["monologue_trace"] = payload.monologue_trace
            task_state["critique_log"] = payload.critique_log
            task_state["diffractive_audit"] = payload.diffractive_audit
            task_state["diffractive_audit_description"] = payload.diffractive_audit_description
        elif phase == "evaluating" and isinstance(payload, EvaluatePayload):
            task_state["should_stop"] = payload.should_stop
            task_state["stop_reason"] = payload.stop_reason
            if not payload.should_stop:
                task_state["current_depth"] = task_state.get("current_depth", 0) + 1
                task_state["query_index"] = 0
        elif phase == "synthesizing" and isinstance(payload, SynthesizePayload):
            # Persist result_summary into state so auto-mode execute() can retrieve it
            task_state["result_summary"] = payload.result_summary
