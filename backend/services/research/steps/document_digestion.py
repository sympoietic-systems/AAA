import asyncio
import json
import logging
import uuid

from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import DocDigestPayload, InjectedDocumentSpec, StepEnvelope, StepOutput
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
        objective = envelope.objective
        payload: DocDigestPayload = envelope.payload
        documents = payload.get_effective_documents()

        previews = []
        task_id = envelope.task_id
        perception_repo = getattr(orch._state, "perception_repo", None)

        task_row = orch.task_repo.get(task_id) if orch.task_repo else None
        default_conv_id = task_row.get("conversation_id") if task_row else None

        for doc in documents:
            doc_summary = ""
            doc_chunks: list[dict] = []
            effective_conv_id = doc.conversation_id or default_conv_id

            if perception_repo and effective_conv_id:
                try:
                    db_chunks = perception_repo.get_by_file(effective_conv_id, doc.file_id)
                    doc_chunks = [{"content": c.chunk_text, "sim": 0} for c in db_chunks if c.chunk_text]
                    file_info = perception_repo.find_file_by_name(doc.file_id)
                    if file_info and file_info.get("summary"):
                        doc_summary = f"[Document: {doc.file_id}]\n{file_info['summary']}"
                except Exception as e:
                    logger.warning("Document chunk preview retrieval failed for %s: %s", doc.file_id, e)

            if doc.document_mode == "chunks":
                doc_chunks = doc_chunks[: doc.document_chunk_limit]

            previews.append(
                {
                    "file_id": doc.file_id,
                    "mode": doc.document_mode,
                    "chunk_limit": doc.document_chunk_limit if doc.document_mode == "chunks" else None,
                    "doc_summary": doc_summary,
                    "doc_chunks": doc_chunks,
                }
            )

        first_doc = documents[0] if documents else None
        return {
            "phase": "document_digestion",
            "file_id": first_doc.file_id if first_doc else None,
            "mode": first_doc.document_mode if first_doc else "chunks",
            "chunk_limit": (first_doc.document_chunk_limit if first_doc and first_doc.document_mode == "chunks" else None),
            "documents": previews,
            "document_digested": state.get("document_digested", False),
            "objective": objective,
            "cached_at": now_utc_str(),
        }

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        objective = envelope.objective
        current_depth = envelope.current_depth
        max_depth = envelope.max_depth
        payload: DocDigestPayload = envelope.payload

        documents = payload.get_effective_documents()
        if not documents:
            return StepOutput(status="completed", message="no documents to digest", payload=payload)

        s = orch._get_state(task_id)
        step_id = orch._create_or_update_step(s, task_id, "document_digestion")

        task_row = orch.task_repo.get(task_id) if orch.task_repo else None
        default_conv_id = task_row.get("conversation_id") if task_row else None
        perception_repo = getattr(orch._state, "perception_repo", None)

        # First check indexing readiness across all documents
        for doc in documents:
            if perception_repo:
                file_status = perception_repo.find_file_by_name(doc.file_id)
                if file_status and file_status.get("status") != "ready":
                    logger.info(
                        "Document %s not yet ready (status=%s); retrying next tick",
                        doc.file_id,
                        file_status.get("status"),
                    )
                    return StepOutput(status="failed", message=f"document {doc.file_id} not yet indexed", payload=payload)

        async def _digest_single_document(doc: InjectedDocumentSpec):
            effective_conv_id = doc.conversation_id or default_conv_id
            if not effective_conv_id and perception_repo:
                file_info = perception_repo.find_file_by_name(doc.file_id)
                if file_info:
                    effective_conv_id = file_info.get("conversation_id")

            if not effective_conv_id:
                logger.warning("Cannot resolve conversation for document %s; skipping", doc.file_id)
                return {"file_id": doc.file_id, "learnings": [], "followups": [], "gaps": [], "chunks_count": 0}

            doc_chunks: list[str] = []
            if perception_repo:
                try:
                    db_chunks = perception_repo.get_by_file(effective_conv_id, doc.file_id)
                    doc_chunks = [_chunk_with_breadcrumb(c) for c in db_chunks if c.chunk_text]
                except Exception as e:
                    logger.warning("Document chunk retrieval failed for %s: %s", doc.file_id, e)

            if doc.document_mode == "chunks":
                doc_chunks = doc_chunks[: doc.document_chunk_limit]

            if not doc_chunks:
                return {"file_id": doc.file_id, "learnings": [], "followups": [], "gaps": [], "chunks_count": 0}

            combined_content = "\n\n---\n\n".join(doc_chunks)
            combined_content = combined_content[: orch._TRUNC_LLM_CONTENT * 2]

            from backend.services.research.steps.digest import analyze_source_content

            analysis = await analyze_source_content(
                orch,
                task_id,
                f"document:{doc.file_id}",
                str(doc.file_id),
                combined_content,
                objective,
                objective,
                0,
                max_depth,
                step_id=step_id,
            )

            if orch.step_result_repo:
                orch.step_result_repo.create(
                    {
                        "id": str(uuid.uuid4()),
                        "step_id": step_id,
                        "task_id": task_id,
                        "source_url": f"document:{doc.file_id}",
                        "source_title": str(doc.file_id),
                        "raw_content": combined_content[:5000],
                        "relevance_score": 0.0,
                        "novelty_score": 0.0,
                        "analyzed_json": json.dumps(analysis, ensure_ascii=False),
                    }
                )

            return {
                "file_id": doc.file_id,
                "learnings": analysis.get("learnings", []),
                "followups": analysis.get("followups", []),
                "gaps": analysis.get("gaps", []),
                "chunks_count": len(doc_chunks),
            }

        # Run parallel digestion across all documents
        results = await asyncio.gather(*[_digest_single_document(d) for d in documents], return_exceptions=True)

        all_learnings: list[str] = []
        all_followups: list[str] = []
        all_gaps: list[str] = []
        new_findings: list[str] = []
        digested_summaries: list[str] = []

        for doc, res in zip(documents, results):
            if isinstance(res, Exception):
                logger.error("Error digesting document %s: %s", doc.file_id, res, exc_info=res)
                continue
            file_id = res["file_id"]
            learnings = res["learnings"]
            followups = res["followups"]
            gaps = res["gaps"]

            all_learnings.extend(learnings)
            all_followups.extend(followups)
            all_gaps.extend(gaps)

            for l in learnings:
                new_findings.append(f"[{file_id}]: {l}")

            digested_summaries.append(f"doc {file_id}: {len(learnings)} learnings ({res['chunks_count']} chunks)")

        if orch.step_repo:
            orch.step_repo.update(
                step_id,
                status="completed",
                result_summary="; ".join(digested_summaries) or "No learnings extracted",
                step_data=json.dumps(
                    {
                        "depth": current_depth,
                        "learnings": all_learnings,
                        "followups": all_followups,
                        "gaps": all_gaps,
                        "documents": [d.model_dump() for d in documents],
                    },
                    default=str,
                    ensure_ascii=False,
                ),
            )

        orch._log_meta(
            task_id,
            "orchestrator_document_digest_complete",
            {
                "documents_count": len(documents),
                "total_learnings": len(all_learnings),
                "total_followups": len(all_followups),
                "total_gaps": len(all_gaps),
            },
            step_id=step_id,
        )

        try:
            from backend.utils.structural_demand import detect_structural_demand

            demand_text = "\n".join(str(x) for x in (all_learnings + all_followups + all_gaps))
            demand = detect_structural_demand(demand_text)
            if demand["demanded"]:
                orch._log_meta(task_id, "structural_demand_detected", demand, step_id=step_id)
        except Exception as e:
            logger.warning("Structural-demand detection failed: %s", e)

        first_doc = documents[0]
        out_payload = DocDigestPayload(
            inject_file_id=first_doc.file_id,
            inject_conversation_id=first_doc.conversation_id,
            document_mode=first_doc.document_mode,
            document_chunk_limit=first_doc.document_chunk_limit,
            documents=documents,
            learnings=all_learnings,
            followups=all_followups,
            gaps=all_gaps,
        )

        rationale = f"Successfully digested {len(documents)} document(s), extracting {len(all_learnings)} key learnings."

        return StepOutput(
            status="completed",
            message=f"{len(all_learnings)} learnings from {len(documents)} document(s)",
            payload=out_payload,
            new_findings=new_findings,
            step_ids=[step_id],
            transition_rationale=rationale,
        )
