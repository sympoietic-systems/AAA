"""Idle structure-extraction migration — ADR-062 Migration of Existing Sediment.

Backfills ``heading_path`` onto already-digested chunks that predate ADR-062.
Runs during idle via the BackgroundTaskEngine. Per file, in order of cheapness:

1. If any chunk already carries ``heading_path`` → the file is done, skip.
2. If the original file still exists on disk → re-extract structure with the
   current digester (authoritative), map heading-paths back by chunk_index.
   Reuses stored ``summary`` and embeddings; ``chunk_text`` is not rewritten.
3. Else if the stored ``chunk_text`` already carries ``#`` markers (HTML family)
   → reconstruct heading-paths from the markers already in the database.
4. Else (no signal, no original) → pass; the file stays flat (backward compat).

This action performs no LLM calls and no re-embedding: it only adds the
``heading_path`` key to each chunk's ``opacity_meta`` JSON.
"""

import json
import logging
import re
from pathlib import Path

from backend.modules.llm_client import BaseLLMProvider
from backend.utils.filesystem import get_upload_path

from ..base import BackgroundAction

logger = logging.getLogger(__name__)

_HEADING_LINE_RE = re.compile(r'^(#{1,6})\s+(.*)$')


def _running_paths_from_chunk_texts(chunk_texts: list[str]) -> list[list[str]]:
    """Reconstruct a heading-path per chunk by scanning the ``#`` markers
    already present in stored text, maintaining a running stack across chunks."""
    stack: dict[int, str] = {}
    paths: list[list[str]] = []
    for text in chunk_texts:
        path_at_start = [stack[lvl] for lvl in sorted(stack)]
        for line in text.split("\n"):
            m = _HEADING_LINE_RE.match(line.strip())
            if not m:
                continue
            level = len(m.group(1))
            title = m.group(2).strip()
            for deeper in [lvl for lvl in stack if lvl >= level]:
                del stack[deeper]
            if title:
                stack[level] = title
        paths.append(path_at_start)
    return paths


class StructureExtractionAction(BackgroundAction):
    @property
    def action_type(self) -> str:
        return "structure_extraction"

    async def execute(self, provider: BaseLLMProvider, payload: dict) -> dict:
        perception_repo = payload.get("perception_repo")
        conversation_id = payload.get("conversation_id")
        file_name = payload.get("file_name")

        if not perception_repo or not conversation_id or not file_name:
            return {"status": "skipped", "reason": "missing repo/conversation/file"}

        chunks = perception_repo.get_by_file(conversation_id, file_name)
        if not chunks:
            return {"status": "skipped", "reason": "no chunks"}

        for c in chunks:
            if c.opacity_meta:
                try:
                    if json.loads(c.opacity_meta).get("heading_path"):
                        return {"status": "skipped", "reason": "already has heading_path"}
                except Exception:
                    pass

        index_to_path: dict[int, list[str]] = {}
        source = "none"

        file_path = get_upload_path(conversation_id, file_name)
        if Path(file_path).exists():
            try:
                from backend.modules.digester import RhizomaticDigester
                file_type = chunks[0].file_type
                digester = RhizomaticDigester()
                text = digester.extract(Path(file_path), file_type)
                meta_chunks = digester.chunk_with_metadata(text)
                for idx, mc in enumerate(meta_chunks):
                    index_to_path[idx] = mc.get("heading_path", [])
                source = "reextract"
            except Exception as e:
                logger.warning("Re-extraction failed for %s; trying DB markers: %s", file_name, e)

        if not index_to_path:
            ordered = sorted(chunks, key=lambda c: c.chunk_index)
            if any("#" in (c.chunk_text or "") for c in ordered):
                paths = _running_paths_from_chunk_texts([c.chunk_text or "" for c in ordered])
                for c, p in zip(ordered, paths):
                    index_to_path[c.chunk_index] = p
                source = "db_markers"

        if not index_to_path:
            return {"status": "skipped", "reason": "no signal, no original"}

        updated = 0
        for c in chunks:
            path = index_to_path.get(c.chunk_index)
            if not path:
                continue
            try:
                meta = json.loads(c.opacity_meta) if c.opacity_meta else {}
            except Exception:
                meta = {}
            meta["heading_path"] = path
            perception_repo.update_chunk_opacity(
                chunk_id=c.id,
                opacity=getattr(c, "opacity", 0) or 0,
                opacity_meta=json.dumps(meta),
            )
            updated += 1

        return {
            "status": "completed",
            "source": source,
            "file_name": file_name,
            "conversation_id": conversation_id,
            "chunks_updated": updated,
        }
