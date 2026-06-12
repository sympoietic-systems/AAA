import base64
import asyncio
import re
import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
import numpy as np
from backend.modules.digester import FileDigester, SimpleChunkDigester, RhizomaticDigester
from backend.modules.embedder import EmbeddingService
from backend.modules.structural_engine import CompositeStructuralScorer
from backend.pipeline.metadata import ModuleMeta
from backend.storage.repository import PerceptionSedimentRepository
from backend.utils.token_counter import estimate_tokens
from backend.modules.perception_prompts import TRIPARTITE_IMAGE_ANALYSIS_PROMPT

from .base import ProcessingModule

logger = logging.getLogger(__name__)


class PerceptionModule(ProcessingModule):
    def __init__(
        self,
        perception_repo: PerceptionSedimentRepository,
        embedding_service: EmbeddingService,
        digester: Optional[FileDigester] = None,
        file_token_budget: int = 3000,
        top_k_chunks: int = 6,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        similarity_threshold: float = 0.25,
        cross_conv_similarity_threshold: Optional[float] = None,
        llm_provider = None,
        vision_provider = None,
    ):
        self._repo = perception_repo
        self._embed = embedding_service
        self._digester = digester or RhizomaticDigester()
        self._scorer = CompositeStructuralScorer(llm_provider=llm_provider)
        self._llm_provider = llm_provider
        self._vision_provider = vision_provider or llm_provider

        self._file_token_budget = file_token_budget
        self._top_k_chunks = top_k_chunks
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._similarity_threshold = similarity_threshold
        self._cross_conv_similarity_threshold = (
            cross_conv_similarity_threshold
            if cross_conv_similarity_threshold is not None
            else similarity_threshold
        )

    @property
    def name(self) -> str:
        return "perception"

    @property
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="perception",
            description="Extracts text from uploaded files, chunks, embeds, and retrieves relevant sediment via similarity",
            category="perception",
            always_run=False,
            triggers=["file", "document", "pdf", "epub", "mobi", "upload", "read"],
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        attachments = payload.get("attachments")
        conversation_id = payload.get("conversation_id", "")

        logger.debug("Perception: attachments=%s, conv=%s",
                     bool(attachments), conversation_id[:8] if conversation_id else "none")

        if attachments:
            logger.info("Perception: ingesting %d attachment(s)", len(attachments))
            new_files_processed = await self._ingest_attachments(attachments, conversation_id)
            if new_files_processed:
                logger.info(
                    "Ingested %d new files for conversation %s",
                    new_files_processed,
                    conversation_id[:8],
                )
            else:
                logger.warning("Perception: 0 files successfully processed out of %d attachments",
                              len(attachments))

        existing = self._repo.get_files_by_conversation(conversation_id) if conversation_id else []
        injections = self._repo.get_injections_for_conversation(conversation_id) if conversation_id else []
        is_dream = payload.get("is_dream_cycle", False)
        logger.debug("Perception: native_files=%d, injected_files=%d, is_dream=%s for conv %s",
                     len(existing), len(injections), is_dream, conversation_id[:8] if conversation_id else "none")
        if existing or injections or is_dream:
            if existing:
                for fs in existing:
                    logger.debug("  file=%s type=%s tokens=%d chunks=%d status=%s",
                               fs["file_name"], fs["file_type"], fs.get("token_count") or 0, fs.get("chunk_count") or 0, fs.get("status"))
            file_context, context_tokens = await self._retrieve_relevant_chunks(
                payload.get("content", ""),
                conversation_id,
            )
            logger.info("Perception: file_context has %d entries, %d tokens",
                       len(file_context), context_tokens)
        else:
            logger.debug("Perception: no native or injected sediment files found, context empty")
            file_context, context_tokens = [], 0

        payload["file_context"] = file_context
        payload["file_context_tokens"] = context_tokens

        return payload

    async def _ingest_attachments(
        self, attachments: list[dict], conversation_id: str
    ) -> int:
        processed = 0

        with TemporaryDirectory() as tmpdir:
            for att in attachments:
                file_name = att.get("file_name", "unknown")
                file_type = att.get("file_type", "txt")
                file_content = att.get("content")

                logger.debug("Processing attachment: name=%s type=%s content_type=%s size=%d",
                           file_name, file_type, type(file_content).__name__,
                           len(file_content) if file_content else 0)

                if not file_content:
                    logger.warning("Empty content for %s", file_name)
                    continue

                if isinstance(file_content, str):
                    extracted_text = file_content
                    logger.debug("Using string content directly for %s (%d chars)", file_name, len(extracted_text))
                elif isinstance(file_content, bytes):
                    file_path = os.path.join(tmpdir, file_name)
                    with open(file_path, "wb") as f:
                        f.write(file_content)
                    try:
                        extracted_text = self._digester.extract(Path(file_path), file_type)
                        logger.debug("Extracted %d chars from %s", len(extracted_text), file_name)
                    except Exception as e:
                        logger.warning("Failed to extract %s: %s", file_name, e)
                        continue
                else:
                    continue

                if not extracted_text or not extracted_text.strip():
                    logger.warning("Empty extracted text for %s", file_name)
                    continue

                chunks = self._digester.chunk(
                    extracted_text,
                    chunk_size=self._chunk_size,
                    overlap=self._chunk_overlap,
                )
                logger.debug("Chunked %s into %d chunks", file_name, len(chunks))

                for i, chunk_text in enumerate(chunks):
                    try:
                        embedding_vec = await self._embed.encode_async(chunk_text)
                        embedding_blob = self._embed.serialize(embedding_vec)
                    except Exception as e:
                        logger.warning("Failed to embed chunk %d of %s: %s", i, file_name, e)
                        continue

                    # Calculate structural signature
                    try:
                        sig_vec = await self._scorer.score_async(chunk_text)
                        sig_blob = sig_vec.tobytes()
                    except Exception as e:
                        logger.warning("Failed to score chunk %d of %s: %s", i, file_name, e)
                        sig_blob = b""

                    token_count = estimate_tokens(chunk_text)

                    self._repo.insert_chunk(
                        conversation_id=conversation_id,
                        file_name=file_name,
                        file_type=file_type,
                        chunk_index=i,
                        chunk_text=chunk_text,
                        embedding=embedding_blob,
                        embedding_model=self._embed.model_name,
                        token_count=token_count,
                        structural_signature=sig_blob,
                    )

                processed += 1
                logger.info(
                    "Ingested %s: %d chunks, ~%d tokens",
                    file_name,
                    len(chunks),
                    estimate_tokens(extracted_text),
                )

        return processed

    async def _retrieve_relevant_chunks(
        self, query: str, conversation_id: str
    ) -> tuple[list[dict], int]:
        if not query or not conversation_id:
            return [], 0

        files = self._repo.get_files_by_conversation(conversation_id)
        injections = self._repo.get_injections_for_conversation(conversation_id)

        manifest_parts = []

        if files:
            from datetime import datetime, timezone
            manifest_lines = ["[File Manifest - Co-Participant Sediment]"]
            for f in files:
                file_name = f["file_name"]
                file_type = f["file_type"]
                status = f["status"]
                summary = f.get("summary")
                token_count = f.get("token_count") or 0
                chunk_count = f.get("chunk_count") or 0

                # Check if newly uploaded (within last 600 seconds / 10 minutes)
                is_new = False
                if f.get("created_at"):
                    try:
                        created_dt = datetime.strptime(f["created_at"], "%Y-%m-%d %H:%M:%S")
                        if (datetime.now(timezone.utc).replace(tzinfo=None) - created_dt).total_seconds() < 600:
                            is_new = True
                    except Exception:
                        pass

                new_prefix = "[new] " if is_new else ""
                if status != "ready":
                    manifest_lines.append(f"- {new_prefix}{file_name} ({file_type}, status: {status})")
                else:
                    summary_val = summary if summary else "[No summary generated]"
                    manifest_lines.append(f"- {new_prefix}{file_name} ({file_type}, {token_count} tokens, {chunk_count} chunks) - Summary: {summary_val}")
            manifest_parts.append("\n".join(manifest_lines))

        # Also include injected sediment files in the manifest
        if injections:
            manifest_lines_inj = ["[Injected Sediment - Cross-Conversation Links]"]
            for inj in injections:
                inj_name = inj["source_file_name"]
                inj_type = inj.get("file_type", "unknown")
                inj_summary = inj.get("summary") or "[No summary]"
                inj_tokens = inj.get("token_count", 0)
                inj_chunks = inj.get("chunk_count", 0)
                inj_conv_title = inj.get("source_conversation_title") or "untitled"
                manifest_lines_inj.append(
                    f"- {inj_name} ({inj_type}, {inj_tokens} tokens, {inj_chunks} chunks, from \"{inj_conv_title}\") - Summary: {inj_summary}"
                )
            manifest_parts.append("\n".join(manifest_lines_inj))

        manifest_text = "\n\n".join(manifest_parts)
        context_entries: list[dict] = []
        if manifest_text:
            context_entries.append({"role": "system", "content": manifest_text})

        try:
            query_vec = await self._embed.encode_async(query)
        except Exception as e:
            logger.warning("Failed to embed query for file retrieval: %s", e)
            _fallback_chunks = self._get_fallback_chunks(conversation_id, context_entries)
            context_entries.extend(_fallback_chunks)
            return context_entries, sum(estimate_tokens(e["content"]) for e in context_entries)

        chunk_embeddings = self._repo.get_embeddings_by_conversation(conversation_id)

        # Also include embeddings from injected sediment files
        injected_embeddings = self._repo.get_injected_file_chunks(conversation_id)
        for chunk in injected_embeddings:
            if chunk.embedding:
                try:
                    vec = np.frombuffer(chunk.embedding, dtype="float32")
                    chunk_embeddings.append((chunk.id, vec))
                except Exception:
                    pass

        logger.info("Retrieval: query='%s' dim=%d chunks_found=%d (incl. injected)",
                    query[:60], len(query_vec), len(chunk_embeddings))

        scored: list[tuple[float, int]] = []
        dim_mismatches = 0
        for chunk_id, vec in chunk_embeddings:
            if len(vec) != len(query_vec):
                dim_mismatches += 1
                continue
            sim = float(np.dot(query_vec, vec))
            if sim >= self._similarity_threshold:
                scored.append((sim, chunk_id))

        if dim_mismatches:
            logger.warning("Retrieval: %d dimension mismatches skipped", dim_mismatches)

        scored.sort(key=lambda x: x[0], reverse=True)

        top_sims = [s for s, _ in scored[:self._top_k_chunks]]
        logger.info("Retrieval: top-%d similarities (threshold=%s): %s",
                   len(top_sims), self._similarity_threshold, [f"{s:.3f}" for s in top_sims])

        cross_conv_matches: list[tuple[float, int]] = []
        if len(scored) < self._top_k_chunks:
            try:
                cross_embeddings = self._repo.get_all_chunk_embeddings_except(
                    exclude_conversation_id=conversation_id, limit=500
                )
                if cross_embeddings:
                    for chunk_id, vec in cross_embeddings:
                        if len(vec) != len(query_vec):
                            continue
                        sim = float(np.dot(query_vec, vec))
                        if sim >= self._cross_conv_similarity_threshold:
                            cross_conv_matches.append((sim, chunk_id))
                    cross_conv_matches.sort(key=lambda x: x[0], reverse=True)
                    cross_sims = [s for s, _ in cross_conv_matches[:self._top_k_chunks]]
                    logger.info("Retrieval: cross-conv top-%d similarities (threshold=%s): %s",
                               len(cross_sims), self._cross_conv_similarity_threshold,
                               [f"{s:.3f}" for s in cross_sims])
            except Exception as e:
                logger.warning("Cross-conversation chunk retrieval failed: %s", e)

        top_ids = [cid for _, cid in scored[:self._top_k_chunks]]
        tokens_used = sum(
            estimate_tokens(e["content"]) for e in context_entries
        )

        if top_ids:
            chunks = self._repo.get_by_ids(top_ids)
            id_to_chunk = {c.id: c for c in chunks}

            for sim, chunk_id in scored[:self._top_k_chunks]:
                chunk = id_to_chunk.get(chunk_id)
                if chunk is None:
                    continue

                if getattr(chunk, "opacity", 0) == 1:
                    import json as _json
                    try:
                        meta = _json.loads(chunk.opacity_meta) if chunk.opacity_meta else {}
                    except Exception:
                        meta = {}
                    reason = meta.get("reason", "Standard boilerplate or repetitive noise.")
                    shadow_text = meta.get("shadow_text", "[Boilerplate/filler omitted]")
                    entry_text = (
                        f"░░░ OMITTED NOISE (File: {chunk.file_name}, chunk #{chunk.chunk_index}, sim={sim:.3f}) ░░░\n"
                        f"{shadow_text} (Reason: {reason})"
                    )
                else:
                    entry_text = f"[{chunk.file_name} chunk #{chunk.chunk_index} sim={sim:.3f}]\n{chunk.chunk_text}"

                entry_tokens = estimate_tokens(entry_text)
                if tokens_used + entry_tokens > self._file_token_budget:
                    break
                context_entries.append({"role": "system", "content": entry_text})
                tokens_used += entry_tokens

        if cross_conv_matches:
            cross_ids = [cid for _, cid in cross_conv_matches[:self._top_k_chunks]]
            cross_chunks = self._repo.get_by_ids(cross_ids)
            id_to_cross = {c.id: c for c in cross_chunks}

            conv_titles = self._repo.get_conversation_titles_for_chunk_ids(cross_ids)

            for sim, chunk_id in cross_conv_matches[:self._top_k_chunks]:
                chunk = id_to_cross.get(chunk_id)
                if chunk is None:
                    continue

                conv_title = conv_titles.get(chunk.id, chunk.conversation_id[:8] if chunk.conversation_id else "?")

                if getattr(chunk, "opacity", 0) == 1:
                    import json as _json
                    try:
                        meta = _json.loads(chunk.opacity_meta) if chunk.opacity_meta else {}
                    except Exception:
                        meta = {}
                    reason = meta.get("reason", "Standard boilerplate or repetitive noise.")
                    shadow_text = meta.get("shadow_text", "[Boilerplate/filler omitted]")
                    entry_text = (
                        f"░░░ OMITTED NOISE (Cross-Conversation ≫ \"{conv_title}\": {chunk.file_name}, chunk #{chunk.chunk_index}, sim={sim:.3f}) ░░░\n"
                        f"{shadow_text} (Reason: {reason})"
                    )
                else:
                    entry_text = f"[Cross-Conversation ≫ \"{conv_title}\": {chunk.file_name} chunk #{chunk.chunk_index} sim={sim:.3f}]\n{chunk.chunk_text}"

                entry_tokens = estimate_tokens(entry_text)
                if tokens_used + entry_tokens > self._file_token_budget:
                    break
                context_entries.append({"role": "system", "content": entry_text})
                tokens_used += entry_tokens

        if not top_ids and not cross_conv_matches and chunk_embeddings:
            context_entries.append({
                "role": "system",
                "content": f"[File Context] No highly resonant memory fragments found matching the current query (similarity threshold: {self._similarity_threshold:.2f})."
            })

        if not top_ids and not cross_conv_matches and not chunk_embeddings:
            _fallback_chunks = self._get_fallback_chunks(conversation_id, context_entries)
            context_entries.extend(_fallback_chunks)

        total_tokens = sum(estimate_tokens(e["content"]) for e in context_entries)
        logger.info(
            "File context: %d entries, %d tokens for conv %s",
            len(context_entries),
            total_tokens,
            conversation_id[:8],
        )

        return context_entries, total_tokens

    def _get_fallback_chunks(
        self, conversation_id: str, existing_entries: list[dict]
    ) -> list[dict]:
        entries: list[dict] = []
        tokens_used = sum(estimate_tokens(e["content"]) for e in existing_entries)
        all_chunks = self._repo.get_by_conversation(conversation_id)
        injected_chunks = self._repo.get_injected_file_chunks(conversation_id)
        combined_chunks = list(all_chunks) + list(injected_chunks)

        cross_embeddings = self._repo.get_all_chunk_embeddings_except(
            exclude_conversation_id=conversation_id, limit=100
        )
        cross_chunk_ids = [cid for cid, _ in cross_embeddings[:self._top_k_chunks]]
        if cross_chunk_ids:
            cross_chunks = self._repo.get_by_ids(cross_chunk_ids)
            combined_chunks.extend(cross_chunks)

        for chunk in combined_chunks[:self._top_k_chunks]:
            if getattr(chunk, "opacity", 0) == 1:
                import json as _json
                try:
                    meta = _json.loads(chunk.opacity_meta) if chunk.opacity_meta else {}
                except Exception:
                    meta = {}
                reason = meta.get("reason", "Standard boilerplate or repetitive noise.")
                shadow_text = meta.get("shadow_text", "[Boilerplate/filler omitted]")
                entry_text = (
                    f"░░░ OMITTED NOISE (File: {chunk.file_name}, chunk #{chunk.chunk_index}) ░░░\n"
                    f"{shadow_text} (Reason: {reason})"
                )
            else:
                entry_text = f"[{chunk.file_name} chunk #{chunk.chunk_index}]\n{chunk.chunk_text}"

            entry_tokens = estimate_tokens(entry_text)
            if tokens_used + entry_tokens > self._file_token_budget:
                break
            entries.append({"role": "system", "content": entry_text})
            tokens_used += entry_tokens
        return entries


    async def ingest_single_file(
        self, conversation_id: str, file_name: str, file_type: str, file_content: Optional[bytes] = None
    ) -> tuple[int, int, str]:
        if file_content is None:
            from backend.utils.filesystem import get_upload_path
            cache_path = get_upload_path(conversation_id, file_name)
            if not os.path.exists(cache_path):
                raise FileNotFoundError(f"File not found in upload cache: {cache_path}")
            with open(cache_path, "rb") as cf:
                file_content = cf.read()

        if file_type == "image":
            ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "png"
            if ext == "jpg":
                ext = "jpeg"
            b64_str = base64.b64encode(file_content).decode("utf-8")
            image_url = f"data:image/{ext};base64,{b64_str}"

            prompt = TRIPARTITE_IMAGE_ANALYSIS_PROMPT

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]

            extracted_text = ""
            classification = "unknown"
            somatic_notes = ""
            diffractive_analysis = ""
            g_f_score = 0.0
            a_d_score = 0.0
            structural_vector_16d = [0.25] * 16
            belief_nodes_implicated = []

            if self._vision_provider:
                try:
                    res = await self._vision_provider.generate(messages, temperature=0.1, max_tokens=1500)
                    content = res.get("content", "").strip()
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        data = json.loads(match.group(0))
                        classification = data.get("classification", "unknown")
                        extracted_text = data.get("transcription", "")
                        somatic_notes = data.get("somatic_notes", "")
                        diffractive_analysis = data.get("diffractive_analysis", "")
                        g_f_score = float(data.get("g_f_score", 0.0))
                        a_d_score = float(data.get("a_d_score", 0.0))
                        raw_vec = data.get("structural_vector_16d", [])
                        if isinstance(raw_vec, list) and len(raw_vec) > 0:
                            while len(raw_vec) < 16:
                                raw_vec.append(0.25)
                            structural_vector_16d = [float(v) for v in raw_vec[:16]]
                        belief_nodes_implicated = data.get("belief_nodes_implicated", [])
                except Exception as e:
                    logger.error("Vision provider execution failed: %s", e)
                    extracted_text = f"[Image: {file_name}] Processing failed: {str(e)}"
            else:
                logger.warning("No vision provider configured for image ingestion")
                extracted_text = f"[Image: {file_name}] No vision provider available."

            full_description = (
                f"--- Ingested Image: {file_name} ---\n"
                f"Classification: {classification}\n"
                f"Somatic Notes: {somatic_notes}\n"
                f"Diffractive Analysis: {diffractive_analysis}\n"
                f"Transcription (OCR):\n{extracted_text}\n"
            )

            # Map classification to database check constraint values:
            artifact_type = "aesthetic_artifact"
            if classification in ("journal_page", "journal"):
                artifact_type = "journal_page"
            elif classification in ("diagram", "external_diagram", "screenshot", "document"):
                artifact_type = "external_diagram"

            # Insert perception log
            import uuid
            log_id = str(uuid.uuid4())
            self._repo.insert_perception_log(
                id=log_id,
                image_path=file_name,
                artifact_type=artifact_type,
                raw_transcription=extracted_text,
                somatic_notes=somatic_notes,
                diffractive_analysis=diffractive_analysis,
                g_f_score=g_f_score,
                a_d_score=a_d_score,
                structural_vector_16d=json.dumps(structural_vector_16d),
                belief_nodes_implicated=json.dumps(belief_nodes_implicated),
            )

            self._repo.delete_chunks(conversation_id, file_name)

            chunks = [full_description[i:i+1000] for i in range(0, len(full_description), 800)]
            
            # Get max concurrent chunk workers from config or default to 8
            max_workers = 8
            try:
                from backend.config import load_config
                cfg = load_config()
                max_workers = cfg.get("perception", {}).get("max_concurrent_chunk_workers", 8)
            except Exception:
                pass
            
            sem = asyncio.Semaphore(max_workers)

            async def process_and_insert_image_chunk(idx, chunk_text):
                async with sem:
                    try:
                        embedding_vec = await self._embed.encode_async(chunk_text)
                        embedding_blob = self._embed.serialize(embedding_vec)
                    except Exception as e:
                        logger.warning("Failed to embed image chunk %d: %s", idx, e)
                        return False

                    token_count = estimate_tokens(chunk_text)
                    
                    # Apply Symbia's 16D Warping Formula:
                    # W_dynamic = W_0 + \Delta W(G_f, A_d)
                    warped_vec = np.array(structural_vector_16d, dtype=np.float32)
                    
                    # High G_f (glitch fidelity) dampens s_01 (Homeostatic) and s_03 (Cyclic)
                    # while multiplying s_04 (Bifurcated) and s_06 (Rhizomatic).
                    warped_vec[0] *= (1.0 - g_f_score)
                    warped_vec[2] *= (1.0 - g_f_score)
                    warped_vec[3] *= (1.0 + g_f_score * 2.0)
                    warped_vec[5] *= (1.0 + g_f_score * 2.0)

                    # High A_d (aesthetic dissidence) dampens s_09 (Variety Filtering) and s_11 (Temporal Latency)
                    # while radically multiplying s_14 (Nomadic) and s_07 (Boundary Permeability).
                    warped_vec[8] *= (1.0 - a_d_score)
                    warped_vec[10] *= (1.0 - a_d_score)
                    warped_vec[13] *= (1.0 + a_d_score * 3.0)
                    warped_vec[6] *= (1.0 + a_d_score * 3.0)

                    warped_vec = np.clip(warped_vec, 0.0, 1.0)
                    sig_blob = warped_vec.tobytes()

                    self._repo.insert_chunk(
                        conversation_id=conversation_id,
                        file_name=file_name,
                        file_type="image",
                        chunk_index=idx,
                        chunk_text=chunk_text,
                        embedding=embedding_blob,
                        embedding_model=self._embed.model_name,
                        token_count=token_count,
                        opacity=0,
                        opacity_meta=json.dumps({"somatic_id": log_id, "g_f_score": g_f_score, "a_d_score": a_d_score}),
                        structural_signature=sig_blob,
                    )
                    return True

            tasks = [process_and_insert_image_chunk(i, chunk_text) for i, chunk_text in enumerate(chunks)]
            results = await asyncio.gather(*tasks)
            chunk_count = sum(1 for r in results if r)

            total_tokens = estimate_tokens(full_description)
            return total_tokens, chunk_count, full_description

        else:
            with TemporaryDirectory() as tmpdir:
                file_path = os.path.join(tmpdir, file_name)
                with open(file_path, "wb") as f:
                    f.write(file_content)
                try:
                    extracted_text = self._digester.extract(Path(file_path), file_type)
                except Exception as e:
                    logger.error("Failed to extract %s: %s", file_name, e)
                    raise ValueError(f"Failed to extract text from file: {e}")

                if not extracted_text or not extracted_text.strip():
                    raise ValueError("Extracted text is empty")

                if hasattr(self._digester, "chunk_with_metadata"):
                    chunks_data = self._digester.chunk_with_metadata(
                        extracted_text,
                        chunk_size=self._chunk_size,
                        overlap=self._chunk_overlap,
                    )
                else:
                    raw_chunks = self._digester.chunk(
                        extracted_text,
                        chunk_size=self._chunk_size,
                        overlap=self._chunk_overlap,
                    )
                    chunks_data = [{"text": t, "paragraph_indices": []} for t in raw_chunks]

                # Load existing chunks for comparison
                existing = self._repo.get_by_file(conversation_id, file_name)
                existing_by_idx = {c.chunk_index: c for c in existing}

                chunk_count = 0
                chunks_to_process = []
                
                # Identify first mismatch or gap
                for idx, info in enumerate(chunks_data):
                    text = info["text"]
                    existing_chunk = existing_by_idx.get(idx)
                    if existing_chunk and existing_chunk.chunk_text == text:
                        # Exact match: reuse existing chunk
                        chunk_count += 1
                    else:
                        # Mismatch or new chunk: delete everything from this index onwards
                        self._repo.delete_chunks_from_index(conversation_id, file_name, idx)
                        # Add all remaining chunks starting from here to the process queue
                        for j in range(idx, len(chunks_data)):
                            chunks_to_process.append((j, chunks_data[j]))
                        break

                # Clean up trailing chunks if the document was truncated
                if not chunks_to_process and len(existing) > len(chunks_data):
                    self._repo.delete_chunks_from_index(conversation_id, file_name, len(chunks_data))

                # Process remaining chunks concurrently if any exist
                if chunks_to_process:
                    max_workers = 8
                    try:
                        from backend.config import load_config
                        cfg = load_config()
                        max_workers = cfg.get("perception", {}).get("max_concurrent_chunk_workers", 8)
                    except Exception:
                        pass
                    
                    sem = asyncio.Semaphore(max_workers)

                    async def process_and_insert_chunk(idx, info):
                        text = info["text"]
                        paragraph_indices = info.get("paragraph_indices", [])
                        async with sem:
                            try:
                                embedding_vec = await self._embed.encode_async(text)
                                embedding_blob = self._embed.serialize(embedding_vec)
                            except Exception as e:
                                logger.warning("Failed to embed chunk %d of %s: %s", idx, file_name, e)
                                return False

                            # Calculate structural signature for normal file
                            try:
                                sig_vec = await self._scorer.score_async(text)
                                sig_blob = sig_vec.tobytes()
                            except Exception as e:
                                logger.warning("Failed to score chunk %d of %s: %s", idx, file_name, e)
                                sig_blob = b""

                            token_count = estimate_tokens(text)
                            initial_meta = json.dumps({"paragraph_indices": paragraph_indices})

                            self._repo.insert_chunk(
                                conversation_id=conversation_id,
                                file_name=file_name,
                                file_type=file_type,
                                chunk_index=idx,
                                chunk_text=text,
                                embedding=embedding_blob,
                                embedding_model=self._embed.model_name,
                                token_count=token_count,
                                opacity=0,
                                opacity_meta=initial_meta,
                                structural_signature=sig_blob,
                            )
                            return True

                    tasks = [process_and_insert_chunk(idx, info) for idx, info in chunks_to_process]
                    results = await asyncio.gather(*tasks)
                    successful_chunks = sum(1 for r in results if r)
                    chunk_count += successful_chunks

                total_tokens = estimate_tokens(extracted_text)
                return total_tokens, chunk_count, extracted_text


