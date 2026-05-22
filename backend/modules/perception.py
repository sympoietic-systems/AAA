import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import numpy as np

from backend.modules.digester import FileDigester, SimpleChunkDigester
from backend.modules.embedder import EmbeddingService
from backend.skills.metadata import SkillMeta
from backend.storage.repository import PerceptionSedimentRepository
from backend.utils.token_counter import estimate_tokens

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
    ):
        self._repo = perception_repo
        self._embed = embedding_service
        self._digester = digester or SimpleChunkDigester()
        self._file_token_budget = file_token_budget
        self._top_k_chunks = top_k_chunks
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._similarity_threshold = similarity_threshold

    @property
    def name(self) -> str:
        return "perception"

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="perception",
            description="Extracts text from uploaded files, chunks, embeds, and retrieves relevant sediment via similarity",
            category="perception",
            always_run=False,
            triggers=["file", "document", "pdf", "upload", "read"],
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
        logger.debug("Perception: get_files_by_conversation returned %d file(s) for conv %s",
                     len(existing), conversation_id[:8] if conversation_id else "none")
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
            logger.debug("Perception: no sediment files found, context empty")
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
        if not files:
            return [], 0

        from datetime import datetime
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
                    if (datetime.utcnow() - created_dt).total_seconds() < 600:
                        is_new = True
                except Exception:
                    pass

            new_prefix = "[new] " if is_new else ""
            if status != "ready":
                manifest_lines.append(f"- {new_prefix}{file_name} ({file_type}, status: {status})")
            else:
                summary_val = summary if summary else "[No summary generated]"
                manifest_lines.append(f"- {new_prefix}{file_name} ({file_type}, {token_count} tokens, {chunk_count} chunks) - Summary: {summary_val}")

        manifest_text = "\n".join(manifest_lines)
        context_entries: list[dict] = [{"role": "system", "content": manifest_text}]

        try:
            query_vec = await self._embed.encode_async(query)
        except Exception as e:
            logger.warning("Failed to embed query for file retrieval: %s", e)
            _fallback_chunks = self._get_fallback_chunks(conversation_id, context_entries)
            context_entries.extend(_fallback_chunks)
            return context_entries, sum(estimate_tokens(e["content"]) for e in context_entries)

        chunk_embeddings = self._repo.get_embeddings_by_conversation(conversation_id)
        logger.info("Retrieval: query='%s' dim=%d chunks_found=%d",
                    query[:60], len(query_vec), len(chunk_embeddings))

        if not chunk_embeddings:
            logger.warning("Retrieval: no chunk embeddings found for conv %s", conversation_id[:8])
            _fallback_chunks = self._get_fallback_chunks(conversation_id, context_entries)
            context_entries.extend(_fallback_chunks)
            return context_entries, sum(estimate_tokens(e["content"]) for e in context_entries)

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

        top_ids = [cid for _, cid in scored[:self._top_k_chunks]]

        if top_ids:
            chunks = self._repo.get_by_ids(top_ids)
            id_to_chunk = {c.id: c for c in chunks}

            tokens_used = sum(
                estimate_tokens(e["content"]) for e in context_entries
            )

            for sim, chunk_id in scored[:self._top_k_chunks]:
                chunk = id_to_chunk.get(chunk_id)
                if chunk is None:
                    continue
                entry_text = f"[{chunk.file_name} chunk #{chunk.chunk_index} sim={sim:.3f}]\n{chunk.chunk_text}"
                entry_tokens = estimate_tokens(entry_text)
                if tokens_used + entry_tokens > self._file_token_budget:
                    break
                context_entries.append({"role": "system", "content": entry_text})
                tokens_used += entry_tokens
        elif chunk_embeddings:
            context_entries.append({
                "role": "system",
                "content": f"[File Context] No highly resonant memory fragments found matching the current query (similarity threshold: {self._similarity_threshold:.2f})."
            })

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
        for chunk in all_chunks[:self._top_k_chunks]:
            entry_text = f"[{chunk.file_name} chunk #{chunk.chunk_index}]\n{chunk.chunk_text}"
            entry_tokens = estimate_tokens(entry_text)
            if tokens_used + entry_tokens > self._file_token_budget:
                break
            entries.append({"role": "system", "content": entry_text})
            tokens_used += entry_tokens
        return entries

    async def ingest_single_file(
        self, conversation_id: str, file_name: str, file_type: str, file_content: bytes
    ) -> tuple[int, int, str]:
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

            chunks = self._digester.chunk(
                extracted_text,
                chunk_size=self._chunk_size,
                overlap=self._chunk_overlap,
            )

            # Delete any existing chunks for this specific file in the conversation
            # to avoid duplicates if re-uploaded
            self._repo.delete_chunks(conversation_id, file_name)

            chunk_count = 0
            for i, chunk_text in enumerate(chunks):
                try:
                    embedding_vec = await self._embed.encode_async(chunk_text)
                    embedding_blob = self._embed.serialize(embedding_vec)
                except Exception as e:
                    logger.warning("Failed to embed chunk %d of %s: %s", i, file_name, e)
                    continue

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
                )
                chunk_count += 1

            total_tokens = estimate_tokens(extracted_text)
            return total_tokens, chunk_count, extracted_text

