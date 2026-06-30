"""Sensory Affordances — web scraping abstraction layer.

Provides a unified async interface over Jina Reader, Crawl4AI, and Firecrawl.
Implements tiered fallback: free backends first, paid backends as upgrade.

Zero-cost to start — Jina Reader works without API key.
Firecrawl and Crawl4AI are optional upgrades.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 9.
"""

import logging
from typing import Optional, Any

import httpx

logger = logging.getLogger("aaa.sensory_affordances")


# ── Custom Exceptions ───────────────────────────────────────────────

class SensoryAffordanceError(Exception):
    """Base exception for sensory access failures."""
    pass


class ShutterClosedError(SensoryAffordanceError):
    """The target has denied access (403, anti-bot wall)."""
    pass


class RateLimitError(SensoryAffordanceError):
    """Rate limited — try again later or upgrade tier."""
    pass


class BackendUnavailableError(SensoryAffordanceError):
    """A required backend is not configured."""
    pass


# ── Configuration ───────────────────────────────────────────────────

def _get_jina_config(config: dict) -> dict:
    return config.get("sensory_affordances", {}).get("jina_reader", {})


def _get_crawl4ai_config(config: dict) -> dict:
    return config.get("sensory_affordances", {}).get("crawl4ai", {})


def _get_firecrawl_config(config: dict) -> dict:
    return config.get("sensory_affordances", {}).get("firecrawl", {})


# ── Tier 1: Jina Reader (FREE — no API key needed) ──────────────────

async def fetch_via_jina(
    url: str,
    config: Optional[dict] = None,
    api_key: Optional[str] = None,
) -> str:
    """Jina Reader — prepend r.jina.ai to any URL for clean markdown.

    Free tier: No API key needed. Rate-limited (~20 req/min).
    Paid tier: API key enables higher limits, token-based billing.

    This is the DEFAULT backend — zero setup, zero cost to start.
    """
    cfg = _get_jina_config(config or {})
    api_base = cfg.get("api_base", "https://r.jina.ai")
    timeout = cfg.get("timeout_seconds", 15)

    target_url = f"{api_base}/{url}"
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(target_url, headers=headers)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                raise RateLimitError(f"Jina rate limited for {url}")
            elif response.status_code in (403, 401):
                raise ShutterClosedError(f"Jina access denied for {url}")
            else:
                logger.warning("Jina returned %d for %s", response.status_code, url)
                return ""
    except httpx.TimeoutException:
        logger.warning("Jina timeout for %s", url)
        return ""
    except Exception as e:
        logger.warning("Jina fetch failed for %s: %s", url, e)
        return ""


# ── Tier 2: Crawl4AI (SELF-HOSTED — open source, free) ─────────────

def is_crawl4ai_available() -> bool:
    """Check if Crawl4AI is installed and Playwright browsers are available."""
    try:
        import crawl4ai  # noqa: F401
        return True
    except ImportError:
        return False


async def fetch_via_crawl4ai(
    url: str,
    config: Optional[dict] = None,
) -> str:
    """Crawl4AI — self-hosted, Playwright-based web scraper.

    Uses robust browser config: random user agents, network-idle wait,
    user simulation, overlay removal, magic extraction mode.
    Falls back to simpler config if the first attempt returns no content.

    Setup: pip install crawl4ai && python -m playwright install
    Cost: Your own compute — no external API bills.
    """
    cfg = _get_crawl4ai_config(config or {})
    timeout_sec = cfg.get("timeout_seconds", 30)

    if not is_crawl4ai_available():
        raise BackendUnavailableError(
            "Crawl4AI not installed. Run: pip install crawl4ai && "
            "python -m playwright install"
        )

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode

        browser_cfg = BrowserConfig(
            headless=True,
            java_script_enabled=True,
            ignore_https_errors=True,
            user_agent_mode="random",
        )

        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_until="networkidle",
            delay_before_return_html=2.0,
            page_timeout=int(timeout_sec * 1000),
            simulate_user=True,
            magic=True,
            remove_overlay_elements=True,
            scan_full_page=True,
            word_count_threshold=10,
        )

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
            if result and result.markdown and len(result.markdown.strip()) > 50:
                return result.markdown

            # Fallback: simpler config if magic/wait didn't work
            logger.info("Crawl4AI primary attempt returned sparse content for %s, retrying with basic config", url[:80])
            fallback_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_until="load",
                page_timeout=int(timeout_sec * 1000),
            )
            result = await crawler.arun(url=url, config=fallback_cfg)
            return result.markdown if result and result.markdown else ""

    except ImportError:
        raise BackendUnavailableError("Crawl4AI import failed despite availability check")
    except Exception as e:
        logger.warning("Crawl4AI failed for %s: %s", url, e)
        return ""


# ── Tier 3: Firecrawl (FREE TIER → paid upgrade) ───────────────────

async def search_via_firecrawl(
    query: str,
    api_key: str,
    config: Optional[dict] = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Firecrawl Search — web search with structured results.

    Free tier: 1,000 credits/month.
    """
    cfg = _get_firecrawl_config(config or {})
    api_base = cfg.get("api_base", "https://api.firecrawl.dev/v1")
    timeout = cfg.get("timeout_seconds", 20)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                f"{api_base}/search",
                json={"query": query, "limit": limit},
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            logger.warning("Firecrawl search failed: %d", response.status_code)
            return {"success": False, "data": []}
        except Exception as e:
            logger.warning("Firecrawl search error: %s", e)
            return {"success": False, "data": [], "error": str(e)}


async def crawl_via_firecrawl(
    url: str,
    api_key: str,
    config: Optional[dict] = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Firecrawl Crawl — follows internal links, extracts site sections."""
    cfg = _get_firecrawl_config(config or {})
    api_base = cfg.get("api_base", "https://api.firecrawl.dev/v1")
    timeout = cfg.get("timeout_seconds", 30)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                f"{api_base}/crawl",
                json={"url": url, "limit": limit},
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            return {"success": False}
        except Exception as e:
            logger.warning("Firecrawl crawl error: %s", e)
            return {"success": False, "error": str(e)}


# ── Unified Fetch Interface ─────────────────────────────────────────

async def select_and_fetch(
    url_or_query: str,
    task_type: str = "single_url",
    config: Optional[dict] = None,
    api_keys: Optional[dict[str, str]] = None,
) -> str:
    """Tiered backend selection with graceful fallback.

    Strategy (from config.sensory_affordances.strategy):
        "tiered" — try backends in priority order, fall through on failure
        "jina_only" — only use Jina Reader
        "crawl4ai_only" — only use Crawl4AI (self-hosted)

    Task types (from config.sensory_affordances.task_type_routing):
        "single_url" — single page markdown extraction
        "deep_crawl" — multi-page site crawling
        "web_search" — search engine queries

    Returns raw markdown/content as string, or raises SensoryAffordanceError
    if all backends are exhausted.
    """
    cfg = config or {}
    # Check if URL points to a PDF file or PDF task is requested
    if url_or_query.lower().split("?")[0].endswith(".pdf") or task_type == "pdf":
        logger.info("PDF URL detected, downloading and extracting text: %s", url_or_query)
        try:
            from backend.modules.digester import SimpleChunkDigester
            from tempfile import NamedTemporaryFile
            import os
            from pathlib import Path

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url_or_query)
                response.raise_for_status()
                pdf_bytes = response.content

            with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf_bytes)
                tmp_path = Path(tmp_file.name)

            try:
                digester = SimpleChunkDigester()
                extracted_text = digester.extract(tmp_path, "pdf")
                if extracted_text and extracted_text.strip():
                    return extracted_text
                else:
                    logger.warning("Extracted PDF text is empty: %s", url_or_query)
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error("Failed to download and extract PDF from URL %s: %s", url_or_query, e)

    sa_config = cfg.get("sensory_affordances", {})
    strategy = sa_config.get("strategy", "tiered")
    routing = sa_config.get("task_type_routing", {})
    keys = api_keys or {}

    backends = routing.get(task_type, ["jina_reader", "crawl4ai"])

    errors = []

    for backend in backends:
        try:
            if backend == "jina_reader" and task_type == "single_url":
                enabled = sa_config.get("jina_reader", {}).get("enabled", True)
                if not enabled:
                    continue
                result = await fetch_via_jina(url_or_query, config=cfg, api_key=keys.get("jina"))
                if result:
                    return result
                errors.append("Jina Reader returned empty content")

            elif backend == "crawl4ai":
                enabled = sa_config.get("crawl4ai", {}).get("enabled", False)
                if not enabled or not is_crawl4ai_available():
                    continue
                result = await fetch_via_crawl4ai(url_or_query, config=cfg)
                if result:
                    return result
                errors.append("Crawl4AI returned empty content")

            elif backend == "firecrawl":
                enabled = sa_config.get("firecrawl", {}).get("enabled", False)
                if not enabled or "firecrawl" not in keys:
                    continue
                if task_type == "web_search":
                    search_result = await search_via_firecrawl(
                        url_or_query, keys["firecrawl"], config=cfg
                    )
                    if search_result.get("success", True) and search_result.get("data"):
                        # Concatenate search results as text
                        texts = [
                            d.get("markdown", d.get("content", ""))
                            for d in search_result["data"]
                        ]
                        return "\n\n---\n\n".join(filter(None, texts))
                elif task_type == "single_url":
                    crawl_result = await crawl_via_firecrawl(
                        url_or_query, keys["firecrawl"], config=cfg, limit=1
                    )
                    if crawl_result.get("success"):
                        data = crawl_result.get("data", {})
                        if isinstance(data, dict):
                            return data.get("markdown", data.get("content", ""))
                        return str(data)

                errors.append("Firecrawl returned empty content")

        except (ShutterClosedError, RateLimitError) as e:
            errors.append(str(e))
            continue  # Try next backend
        except BackendUnavailableError as e:
            errors.append(str(e))
            continue

    raise SensoryAffordanceError(
        f"All backends exhausted for {url_or_query}: {'; '.join(errors)}"
    )
