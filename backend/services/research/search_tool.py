"""Web search tools for research orchestration.

Provides DuckDuckGo search via Crawl4AI with Jina fallback,
plus URL extraction from raw markdown / HTML content.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


# ── URL cleaning ─────────────────────────────────────────────────────


def clean_ddg_url(url: str) -> str:
    """Extract real URL from DuckDuckGo redirect links (uddg= parameter).

    Handles both the /l/ redirect path and direct uddg= query parameter forms.
    """
    if "uddg=" in url or "duckduckgo.com/l/" in url:
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            real = qs.get("uddg", qs.get("u", qs.get("url", [""])))[0]
            if real and real.startswith("http"):
                return real
        except Exception:
            pass
    return url


# ── URL extraction from raw content ──────────────────────────────────


def extract_urls_from_content(content: str, n: int = 3, query: str = "") -> list[dict]:
    """Extract URLs from markdown or HTML content with layered fallback strategies.

    Handles both formats:
    - Markdown: [title](url), bare https:// URLs
    - HTML: <a href="url">title</a>
    - DuckDuckGo redirect URLs: extract uddg= parameter
    - DuckDuckGo result snippet lines: title followed by description then URL
    """
    results: list[dict] = []

    # Strategy 1: Markdown link pattern [text](url)
    md_links = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', content)
    for title, url in md_links[:n * 3]:
        if "duckduckgo.com" not in url and "localhost" not in url:
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            results.append({"url": url, "title": title_clean[:120], "snippet": ""})

    # Strategy 2: HTML <a href="url"> pattern
    if not results:
        html_links = re.findall(
            r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            content,
            re.IGNORECASE | re.DOTALL,
        )
        for url, title in html_links[:n * 3]:
            if "duckduckgo.com" not in url and "localhost" not in url:
                results.append({
                    "url": url,
                    "title": re.sub(r'<[^>]+>', '', title).strip()[:120],
                    "snippet": "",
                })

    # Strategy 3: Bare URLs in text
    if not results:
        bare_urls = re.findall(r'(?:^|\s)(https?://[^\s<>"]+?)(?:$|\s|[,.?!;:])', content)
        for url in bare_urls[:n]:
            if "duckduckgo.com" not in url and "localhost" not in url:
                results.append({"url": url, "title": url[:80], "snippet": ""})

    # Strategy 4: DuckDuckGo result snippet lines
    if not results:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith("#") and "http" not in line:
                for j in range(i + 1, min(i + 4, len(lines))):
                    url_match = re.search(r'(https?://[^\s<>"]+)', lines[j])
                    if url_match and "duckduckgo" not in url_match.group(1):
                        title = re.sub(r'^[\d.\s*#>-]+', '', line).strip()[:120]
                        if title and title != query:
                            results.append({
                                "url": url_match.group(1),
                                "title": title,
                                "snippet": "",
                            })
                        break

    return results[:n]


# ── Crawl4AI structured search ───────────────────────────────────────


async def search_via_crawl4ai(search_url: str, n: int = 3) -> list[dict]:
    """Use Crawl4AI's structured link extraction with layered fallback strategies.

    Four strategies in order:
    1. Crawl4AI structured external + internal links
    2. Markdown link pattern extraction from rendered markdown
    3. Bare URL extraction from raw text
    4. Fallback to extract_urls_from_content
    """
    try:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=search_url)

            if not result:
                return []

            results: list[dict] = []
            seen_urls: set[str] = set()

            # Strategy 1: Crawl4AI's structured links
            if result.links:
                external = result.links.get("external", [])
                internal = result.links.get("internal", [])
                for link in external + internal:
                    href = link.get("href", "")
                    if not href.startswith("http"):
                        continue
                    real_url = clean_ddg_url(href)
                    if any(skip in real_url for skip in ["duckduckgo.com", "spread.", "y.js", ".js?", ".css"]):
                        continue
                    if real_url in seen_urls:
                        continue
                    seen_urls.add(real_url)
                    title = link.get("text", "") or link.get("title", "") or real_url[:80]
                    results.append({
                        "url": real_url,
                        "title": title[:120],
                        "snippet": link.get("description", link.get("snippet", ""))[:200],
                    })
                    if len(results) >= n:
                        break

            # Strategy 2: Markdown links
            if not results and result.markdown:
                md_links = re.findall(r'\[([^\]]{3,120})\]\((https?://[^\)]+)\)', result.markdown)
                for title, url in md_links:
                    real_url = clean_ddg_url(url)
                    if any(skip in real_url for skip in ["duckduckgo.com", "spread.", ".js", ".css"]):
                        continue
                    if real_url in seen_urls:
                        continue
                    seen_urls.add(real_url)
                    title_clean = re.sub(r'<[^>]+>', '', title).strip()
                    results.append({"url": real_url, "title": title_clean[:120], "snippet": ""})
                    if len(results) >= n:
                        break

            # Strategy 3: Bare URLs from raw text
            if not results and result.markdown:
                bare_urls = re.findall(r'https?://[^\s<>"\'\)\]\#]{10,300}', result.markdown)
                for url in bare_urls:
                    real_url = clean_ddg_url(url)
                    if any(skip in real_url for skip in ["duckduckgo", "spread.", ".js", ".css", "schema.org"]):
                        continue
                    if real_url in seen_urls:
                        continue
                    seen_urls.add(real_url)
                    results.append({"url": real_url, "title": real_url[:80], "snippet": ""})
                    if len(results) >= n:
                        break

            # Strategy 4: Fallback to extract_urls_from_content
            if not results and result.markdown:
                results = extract_urls_from_content(result.markdown, n)

            return results[:n]
    except ImportError:
        return []
    except Exception as e:
        logger.warning("Crawl4AI structured search exception: %s", str(e)[:120])
        return []


# ── Jina fetch ───────────────────────────────────────────────────────


async def fetch_via_jina(url: str, config: dict) -> str:
    """Fetch page content via Jina through sensory affordances."""
    from backend.services.research.sensory_affordances import select_and_fetch
    return (await select_and_fetch(url_or_query=url, task_type="single_url", config=config)) or ""


# ── Main entry point ─────────────────────────────────────────────────


async def web_search(query: str, n: int = 3, config: dict | None = None) -> list[dict]:
    """Search DuckDuckGo and return top N result URLs with titles and snippets.

    Strategy: Crawl4AI → extract structured links from search result object.
    Falls back to Jina + markdown URL pattern extraction.

    Args:
        query: Search query string.
        n: Maximum number of results to return (default 3).
        config: Application config dict, required for Jina fallback.

    Returns:
        List of dicts with 'url', 'title', and 'snippet' keys.
    """
    try:
        from backend.services.research.sensory_affordances import is_crawl4ai_available

        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"

        if is_crawl4ai_available():
            try:
                results = await search_via_crawl4ai(search_url, n)
                if results:
                    return results
            except (RuntimeError, Exception) as e:
                logger.warning("Crawl4AI search failed, falling back: %s", str(e)[:80])

        # Jina fallback — get raw content and extract URLs
        raw = await fetch_via_jina(search_url, config or {})
        if raw:
            return extract_urls_from_content(raw, n, query)

        return []
    except Exception as e:
        logger.warning("Web search failed for '%s': %s", query[:60], e)
        return []
