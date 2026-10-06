import asyncio
import contextlib
import logging
import uuid
from datetime import datetime
from pathlib import Path

from backend.services.research.sensory_affordances import (
    fetch_via_crawl4ai,
    is_crawl4ai_available,
    select_and_fetch,
)
from backend.services.research.steps.base import BaseResearchStep
from backend.services.research.task_state import ParsePayload, StepEnvelope, StepOutput
from backend.storage.research_evidence import ParserQuality
from backend.utils.research_logger import now_utc_str

logger = logging.getLogger("aaa.research_orchestrator")


def _archive_content(task_id: str, content: str, limit: int) -> str:
    base = Path(__file__).resolve().parent.parent.parent.parent
    task_dir = base / "data" / "uploads" / "research" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    path = task_dir / f"page_{uuid.uuid4().hex[:8]}.html"
    path.write_text(content[:limit], encoding="utf-8")
    return str(path)


async def parallel_parse_grouped(
    orch, task_id: str, group_steps: dict, search_results: list[dict], plan_id: str
) -> list[dict]:
    """Fetch all search result URLs in parallel, saving HTML to disk.

    Skips already-fetched URLs via DB cache lookup to avoid redundant requests.
    Migrated from legacy tools._tool_parallel_parse_grouped.
    """
    sem = orch._get_semaphore()
    acquisition_enabled = hasattr(orch, "acquisition_enabled") and orch.acquisition_enabled(task_id) is True
    if acquisition_enabled and len(search_results) > 128:
        raise ValueError("Acquisition phase exceeds source candidate limit")

    # Dedup: reuse content already stored in step_result table
    new_urls: list[dict] = []
    reused: list[dict] = []

    for r in search_results:
        url = r.get("url", "")
        q_group = r.get("query_group", 1)
        step_id = group_steps.get(q_group) or (list(group_steps.values())[0] if group_steps else None)
        cached_content = None

        if orch.step_result_repo and not acquisition_enabled:
            try:
                task_results = await asyncio.to_thread(orch.step_result_repo.get_by_task, task_id)
                for er in task_results:
                    if (
                        er.get("source_url") == url
                        and er.get("raw_content")
                        and not er["raw_content"].startswith("Error:")
                    ):
                        cached_content = er["raw_content"]
                        break
            except Exception:
                pass

        if cached_content:
            logger.info("DB cache hit, reusing content for URL: %s", url[:80])
            if orch.step_result_repo and step_id:
                try:
                    result_id = str(uuid.uuid4())
                    await asyncio.to_thread(
                        orch.step_result_repo.create,
                        {
                            "id": result_id,
                            "step_id": step_id,
                            "task_id": task_id,
                            "source_url": url,
                            "source_title": r.get("title", url),
                            "raw_content": cached_content,
                            "raw_file_path": "",
                        },
                    )
                    reused.append(
                        {
                            "id": result_id,
                            "url": url,
                            "title": r.get("title", url),
                            "content": cached_content,
                            "query_group": q_group,
                            "reused": True,
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to create reused step_result for %s: %s", url[:80], e)
        else:
            new_urls.append(r)

    if reused:
        logger.info(
            "Reused %d cached pages, fetching %d new URLs — %s",
            len(reused),
            len(new_urls),
            orch._log_context(task_id, "parsing"),
        )

    async def fetch_one(url: str, title: str, q_group: int) -> dict | None:
        step_id = group_steps.get(q_group) or list(group_steps.values())[0]
        async with sem:
            try:
                acquisition = None
                if acquisition_enabled:
                    acquisition = await orch.acquire(
                        task_id,
                        url,
                        lambda: select_and_fetch(url_or_query=url, task_type="single_url", config=orch._state.config),
                    )
                    content = acquisition.content
                    store = orch.evidence_store_for(task_id)
                    if store is not None:
                        await asyncio.to_thread(
                            store.record_text,
                            task_id,
                            url,
                            content,
                            quality=ParserQuality(
                                method=(acquisition.providers or (None,))[-1],
                                config_hash=acquisition.config_hash,
                                warnings=("original_bytes_unavailable",),
                            ),
                            observed_at=acquisition.observed_at,
                        )
                else:
                    content = await select_and_fetch(
                        url_or_query=url, task_type="single_url", config=orch._state.config
                    )
                if not acquisition_enabled and not content and is_crawl4ai_available():
                    with contextlib.suppress(RuntimeError):
                        content = await fetch_via_crawl4ai(url, config=orch._state.config)
                if not content:
                    logger.warning("All backends returned empty content for %s", url[:80])
                    if orch.step_result_repo:
                        try:
                            await asyncio.to_thread(
                                orch.step_result_repo.create,
                                {
                                    "id": str(uuid.uuid4()),
                                    "step_id": step_id,
                                    "task_id": task_id,
                                    "source_url": url,
                                    "source_title": title,
                                    "raw_content": "Error: Empty content returned from all backends",
                                    "raw_file_path": None,
                                },
                            )
                        except Exception as db_err:
                            logger.warning("Failed to save parse empty result to DB: %s", db_err)
                    return None

                # Optionally archive HTML to disk
                file_path = ""
                if orch.html_archive:
                    try:
                        file_path = await asyncio.to_thread(
                            _archive_content, task_id, content, orch._TRUNC_HTML_ARCHIVE
                        )
                    except Exception:
                        logger.warning("Failed to archive HTML for %s", url[:80])

                result_id = str(uuid.uuid4())
                await asyncio.to_thread(
                    orch.step_result_repo.create,
                    {
                        "id": result_id,
                        "step_id": step_id,
                        "task_id": task_id,
                        "source_url": url,
                        "source_title": title,
                        "raw_content": content[: orch._TRUNC_STEP_RESULT],
                        "raw_file_path": file_path,
                    },
                )
                parsed_source = {
                    "id": result_id,
                    "url": url,
                    "title": title,
                    "content": content,
                    "query_group": q_group,
                }
                if acquisition is not None:
                    parsed_source["acquisition"] = {
                        "observed_at": acquisition.observed_at.isoformat(),
                        "accessed_at": acquisition.accessed_at.isoformat(),
                        "valid_until": acquisition.valid_until.isoformat(),
                        "cache_hit": acquisition.cache_hit,
                        "config_hash": acquisition.config_hash,
                        "providers": list(acquisition.providers),
                        "origin_acquisition_id": acquisition.origin_acquisition_id,
                        "access_acquisition_id": acquisition.access_acquisition_id,
                    }
                return parsed_source
            except Exception as e:
                logger.warning("Fetch failed for %s: %s", url[:80], e)
                if orch.step_result_repo:
                    try:
                        await asyncio.to_thread(
                            orch.step_result_repo.create,
                            {
                                "id": str(uuid.uuid4()),
                                "step_id": step_id,
                                "task_id": task_id,
                                "source_url": url,
                                "source_title": title,
                                "raw_content": f"Error: Fetch failed: {str(e)[:300]}",
                                "raw_file_path": None,
                            },
                        )
                    except Exception as db_err:
                        logger.warning("Failed to save parse error result to DB: %s", db_err)
                return None

    tasks = []
    seen_urls_in_batch: set[str] = set()
    for r in new_urls:
        url = r["url"]
        if url not in seen_urls_in_batch:
            seen_urls_in_batch.add(url)
            tasks.append(fetch_one(url, r.get("title", url), r.get("query_group", 1)))

    gathered = await asyncio.gather(*tasks)
    fetched = [g for g in gathered if g is not None]
    return reused + fetched


class ParseStep(BaseResearchStep):
    @property
    def step_type(self) -> str:
        return "parse"

    async def preview(self, orch, envelope: StepEnvelope, state: dict) -> dict:
        payload: ParsePayload = envelope.payload
        search_cache = payload.search_results_cache or []
        urls = [
            {"url": r.get("url", ""), "title": r.get("title", r.get("url", "")), "query_group": r.get("query_group")}
            for r in search_cache
        ]
        return {
            "phase": "parsing",
            "urls_to_fetch": urls,
            "cached_at": now_utc_str(),
        }

    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        task_id = envelope.task_id
        plan_id = envelope.plan_id

        payload: ParsePayload = envelope.payload
        search_cache = payload.search_results_cache

        query_groups = sorted({r.get("query_group", 1) for r in search_cache}) or [1]

        s = orch._get_state(task_id)
        group_steps = {}

        for q_group in query_groups:
            step_id = await asyncio.to_thread(
                orch._create_or_update_step, s, task_id, "parallel_parse", query_group=q_group, query_text=""
            )
            group_steps[q_group] = step_id

        # Call local parallel_parse_grouped directly rather than through orch delegate
        parsed = await parallel_parse_grouped(
            orch,
            task_id,
            group_steps,
            search_cache,
            plan_id,
        )
        store = orch.evidence_store_for(task_id) if hasattr(orch, "evidence_store_for") else None
        evidence_packets = []
        if store is not None:
            for source in parsed:
                acquisition = source.get("acquisition") or {}
                quality = (
                    ParserQuality(
                        method=(acquisition.get("providers") or [None])[-1],
                        config_hash=acquisition.get("config_hash"),
                        warnings=("original_bytes_unavailable",),
                    )
                    if acquisition
                    else None
                )
                artifact, segments = await asyncio.to_thread(
                    store.record_text,
                    task_id,
                    source["url"],
                    source.get("content", ""),
                    reused=source.get("reused", False),
                    quality=quality,
                    observed_at=datetime.fromisoformat(acquisition["observed_at"]) if acquisition else None,
                )
                source.update(
                    source_id=artifact.source_id,
                    source_version=artifact.source_version,
                    segment_ids=[segment.segment_id for segment in segments],
                )
                packet = store.packet(artifact, segments=segments)
                if acquisition:
                    packet = packet.model_copy(
                        update=dict(
                            acquisition_id=acquisition["access_acquisition_id"],
                            observed_at=datetime.fromisoformat(acquisition["observed_at"]),
                            accessed_at=datetime.fromisoformat(acquisition["accessed_at"]),
                            valid_until=datetime.fromisoformat(acquisition["valid_until"]),
                            cache_hit=acquisition["cache_hit"],
                        )
                    )
                evidence_packets.append(packet)
            available_urls = {source["url"] for source in parsed}
            missing_urls = {source["url"] for source in search_cache} - available_urls
            for url in sorted(missing_urls):
                artifact, _ = await asyncio.to_thread(
                    store.record_text, task_id, url, "", unavailable_reason="no_available_extracted_text"
                )
                evidence_packets.append(store.packet(artifact))

        if orch.step_repo:
            for q_group, step_id in group_steps.items():
                parsed_for_group = [p for p in parsed if p.get("query_group") == q_group]
                await asyncio.to_thread(
                    orch.step_repo.update,
                    step_id,
                    status="completed",
                    result_summary=f"parsed {len(parsed_for_group)} sources",
                )

        urls = [
            {"url": p["url"], "title": p.get("title", p["url"]), "query_group": p.get("query_group")} for p in parsed
        ]

        cache = await asyncio.to_thread(orch._load_cache, task_id)
        cache["parsing"] = {"phase": "parsing", "urls": urls, "cached_at": now_utc_str()}
        await asyncio.to_thread(orch._save_cache, task_id, cache)

        out_payload = ParsePayload(search_results_cache=search_cache, parsed_sources=parsed)

        signal_flags = {"has_parsed_content": len(parsed) > 0}
        if hasattr(orch, "acquisition_enabled") and orch.acquisition_enabled(task_id) is True:
            from backend.storage.repositories.research.acquisition import ResearchAcquisitionRepository

            records = await asyncio.to_thread(
                ResearchAcquisitionRepository(orch.task_repo._db_path).list_action, task_id, s["active_action_id"]
            )
            signal_flags["acquisition_degraded"] = any(
                item.outcome in {"failed", "cancelled", "unavailable"} for item in records
            )

        all_step_ids = list(group_steps.values())
        if parsed:
            rationale = f"Successfully parsed and extracted text content from {len(parsed)} source URLs."
        else:
            rationale = "Attempted to parse search results, but no valid content could be extracted from any sources."

        return StepOutput(
            status="completed",
            message=f"parsed {len(parsed)} sources",
            payload=out_payload,
            signal_flags=signal_flags,
            step_ids=all_step_ids,
            evidence_packets=tuple(evidence_packets),
            transition_rationale=rationale,
        )
