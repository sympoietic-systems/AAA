import json
import logging
import uuid

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import DocDigestPayload, StepEnvelope, StepOutput
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")


def _chunk_with_breadcrumb(chunk) -> str:
    """Prefix a chunk with its heading-path so research learnings inherit
    section-level provenance (ADR-062). Falls back to bare text when no
    heading-path is stored."""
    text = chunk.chunk_text
    meta_raw = getattr(chunk, "opacity_meta", None)
    if not meta_raw:
        return text
    try:
        path = json.loads(meta_raw).get("heading_path", [])
    except Exception:
        return text
    if not path:
        return text
    return f"[§ {' › '.join(str(p) for p in path)}]\n{text}"


class DocumentDigestionStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "document_digestion"

    async def preview(self, orch, envelope: StepEnvelope, state: dict) -> dict:
        task_id = envelope.task_id
        objective = envelope.objective

        payload: DocDigestPayload = envelope.payload
        inject_file_id = payload.inject_file_id
        inject_conv_id = payload.inject_conversation_id
        doc_mode = payload.document_mode
        chunk_limit = payload.document_chunk_limit

        doc_summary = ""
        doc_chunks: list[dict] = []

        if inject_file_id:
            conversation_id = None
            task_row = orch.task_repo.get(task_id) if orch.task_repo else None
            if task_row:
                conversation_id = task_row.get("conversation_id")
            effective_conv_id = inject_conv_id or conversation_id

            perception_repo = getattr(orch._state, "perception_repo", None)
            if perception_repo and effective_conv_id:
                try:
                    db_chunks = perception_repo.get_by_file(effective_conv_id, inject_file_id)
                    doc_chunks = [{"content": c.chunk_text, "sim": 0} for c in db_chunks if c.chunk_text]
                    file_info = perception_repo.find_file_by_name(inject_file_id)
                    if file_info and file_info.get("summary"):
                        doc_summary = f"[Document: {inject_file_id}]\n{file_info['summary']}"
                except Exception as e:
                    logger.warning("Document chunk preview retrieval failed: %s", e)

            if doc_mode == "chunks":
                doc_chunks = doc_chunks[:chunk_limit]

        return {
            "phase": "document_digestion",
            "file_id": inject_file_id,
            "mode": doc_mode,
            "chunk_limit": chunk_limit if doc_mode == "chunks" else None,
            "document_digested": state.get("document_digested", False),
            "objective": objective,
            "doc_summary": doc_summary,
            "doc_chunks": doc_chunks,
            "cached_at": now_utc_str(),
        }

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth

        payload: DocDigestPayload = envelope.payload
        inject_file_id = payload.inject_file_id
        inject_conv_id = payload.inject_conversation_id
        doc_mode = payload.document_mode
        chunk_limit = payload.document_chunk_limit

        if not inject_file_id:
            return StepOutput(
                status="completed",
                message="no document to digest",
                payload=payload
            )

        s = orch._get_state(task_id)
        step_id = orch._create_or_update_step(s, task_id, "document_digestion")

        conversation_id = None
        task_row = orch.task_repo.get(task_id) if orch.task_repo else None
        if task_row:
            conversation_id = task_row.get("conversation_id")

        effective_conv_id = inject_conv_id or conversation_id
        perception_repo = getattr(orch._state, "perception_repo", None)

        if not effective_conv_id and perception_repo:
            file_info = perception_repo.find_file_by_name(inject_file_id)
            if file_info:
                effective_conv_id = file_info.get("conversation_id")

        if not effective_conv_id:
            if orch.step_repo:
                orch.step_repo.update(step_id, status="completed",
                    result_summary="Cannot resolve conversation for document; skipping digestion")
            return StepOutput(
                status="completed",
                message="no conversation for document",
                payload=payload
            )

        if perception_repo:
            file_status = perception_repo.find_file_by_name(inject_file_id)
            if file_status and file_status.get("status") != "ready":
                logger.info("Document %s not yet ready (status=%s); retrying next tick",
                            inject_file_id, file_status.get("status"))
                return StepOutput(
                    status="failed",
                    message="document not yet indexed",
                    payload=payload
                )

        doc_summary = ""
        doc_chunks: list[str] = []

        if perception_repo:
            try:
                db_chunks = perception_repo.get_by_file(effective_conv_id, inject_file_id)
                doc_chunks = [_chunk_with_breadcrumb(c) for c in db_chunks if c.chunk_text]
                file_info = perception_repo.find_file_by_name(inject_file_id)
                if file_info and file_info.get("summary"):
                    doc_summary = f"[Document: {inject_file_id}]\n{file_info['summary']}"
            except Exception as e:
                logger.warning("Document chunk retrieval failed: %s", e)

        if doc_mode == "chunks":
            doc_chunks = doc_chunks[:chunk_limit]

        if not doc_chunks:
            if orch.step_repo:
                orch.step_repo.update(step_id, status="completed",
                    result_summary="No relevant document chunks found for digestion",
                    step_data=json.dumps({"depth": current_depth}, ensure_ascii=False))
            return StepOutput(
                status="completed",
                message="no relevant chunks",
                payload=payload
            )

        combined_content = "\n\n---\n\n".join(doc_chunks)
        combined_content = combined_content[:orch._TRUNC_LLM_CONTENT * 2]

        goal = objective
        from backend.services.research.steps.digest import analyze_source_content
        analysis = await analyze_source_content(
            orch, task_id, f"document:{inject_file_id}", str(inject_file_id),
            combined_content, objective, goal, 0, max_depth, step_id=step_id
        )

        learnings = analysis.get("learnings", [])
        followups = analysis.get("followups", [])
        gaps = analysis.get("gaps", [])

        if orch.step_repo:
            orch.step_repo.update(step_id, status="completed",
                result_summary=f"{len(learnings)} learnings, {len(followups)} followups from doc {inject_file_id} ({len(doc_chunks)} chunks)",
                step_data=json.dumps({
                    "depth": current_depth,
                    "learnings": learnings,
                    "followups": followups,
                    "gaps": gaps,
                    "file_id": inject_file_id,
                    "mode": doc_mode
                }, default=str, ensure_ascii=False),
            )

        if orch.step_result_repo:
            orch.step_result_repo.create({
                "id": str(uuid.uuid4()),
                "step_id": step_id,
                "task_id": task_id,
                "source_url": f"document:{inject_file_id}",
                "source_title": str(inject_file_id),
                "raw_content": combined_content[:5000],
                "relevance_score": 0.0,
                "novelty_score": 0.0,
                "analyzed_json": json.dumps(analysis, ensure_ascii=False),
            })

        orch._log_meta(task_id, "orchestrator_document_digest_complete", {
            "file_id": inject_file_id,
            "chunks_analyzed": len(doc_chunks),
            "learnings": len(learnings),
            "followups": len(followups),
            "gaps": len(gaps),
        }, step_id=step_id)

        try:
            from backend.utils.structural_demand import detect_structural_demand
            demand_text = "\n".join(str(x) for x in (learnings + followups + gaps))
            demand = detect_structural_demand(demand_text)
            if demand["demanded"]:
                orch._log_meta(task_id, "structural_demand_detected", demand, step_id=step_id)
        except Exception as e:
            logger.warning("Structural-demand detection failed: %s", e)

        new_findings = [f"[{inject_file_id}]: " + l for l in learnings]

        out_payload = DocDigestPayload(
            inject_file_id=inject_file_id,
            inject_conversation_id=inject_conv_id,
            document_mode=doc_mode,
            document_chunk_limit=chunk_limit,
            learnings=learnings,
            followups=followups,
            gaps=gaps
        )

        rationale = f"Successfully digested uploaded document {inject_file_id} in {doc_mode} mode, extracting {len(learnings)} key learnings."

        return StepOutput(
            status="completed",
            message=f"{len(learnings)} learnings from document",
            payload=out_payload,
            new_findings=new_findings,
            step_ids=[step_id],
            transition_rationale=rationale
        )
