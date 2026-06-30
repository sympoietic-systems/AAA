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


def _is_valid_http_url(url: str) -> bool:
    """Reject obviously malformed URLs (missing hostname, no TLD, etc.)."""
    if not url.startswith("http://") and not url.startswith("https://"):
        return False
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        return "." in host and len(host) >= 4
    except Exception:
        return False


def clean_ddg_url(url: str) -> str:
    """Extract real URL from DuckDuckGo redirect links (uddg= parameter).

    Also resolves protocol-relative URLs to https.
    Handles both the /l/ redirect path and direct uddg= query parameter forms.
    """
    if url.startswith("//"):
        url = "https:" + url
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
        if not _is_valid_http_url(url):
            continue
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
            if not _is_valid_http_url(url):
                continue
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
            if not _is_valid_http_url(url):
                continue
            if "duckduckgo.com" not in url and "localhost" not in url:
                results.append({"url": url, "title": url[:80], "snippet": ""})

    # Strategy 4: DuckDuckGo result snippet lines
    if not results:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith("#") and "http" not in line:
                for j in range(i + 1, min(i + 4, len(lines))):
                    url_match = re.search(r'(https?://[^\s<>"]+)', lines[j])
                    if url_match:
                        url = url_match.group(1)
                        if not _is_valid_http_url(url):
                            continue
                        if "duckduckgo" not in url:
                            title = re.sub(r'^[\d.\s*#>-]+', '', line).strip()[:120]
                            if title and title != query:
                                results.append({
                                    "url": url,
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
                print(f">>> search_via_crawl4ai: result is None/falsy", flush=True)
                return []

            results: list[dict] = []
            seen_urls: set[str] = set()

            print(f">>> search_via_crawl4ai: has_links={result.links is not None}, has_markdown={bool(result.markdown)}, markdown_len={len(result.markdown) if result.markdown else 0}", flush=True)

            # Strategy 1: Crawl4AI's structured links
            if result.links:
                external = result.links.get("external", [])
                internal = result.links.get("internal", [])
                print(f">>> search_via_crawl4ai: links_keys={list(result.links.keys()) if isinstance(result.links, dict) else type(result.links).__name__}", flush=True)
                print(f">>> search_via_crawl4ai: external_links={len(external)}, internal_links={len(internal)}", flush=True)
                if external:
                    sample_hrefs = [l.get("href", "")[:120] for l in external[:5]]
                    print(f">>> search_via_crawl4ai: sample external hrefs={sample_hrefs}", flush=True)
                if internal:
                    sample_ihrefs = [l.get("href", "")[:120] for l in internal[:5]]
                    print(f">>> search_via_crawl4ai: sample internal hrefs={sample_ihrefs}", flush=True)
                for link in external + internal:
                    href = link.get("href", "")
                    # Accept http, https, and protocol-relative URLs
                    if not (href.startswith("http") or href.startswith("//")):
                        continue
                    real_url = clean_ddg_url(href)
                    if not _is_valid_http_url(real_url):
                        continue
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
                print(f">>> search_via_crawl4ai: strat2 md_links_found={len(md_links)}, markdown_len={len(result.markdown)}", flush=True)
                if md_links:
                    print(f">>> search_via_crawl4ai: strat2 sample={[(t[:60], u[:120]) for t,u in md_links[:3]]}", flush=True)
                for title, url in md_links:
                    real_url = clean_ddg_url(url)
                    if not _is_valid_http_url(real_url):
                        continue
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
                print(f">>> search_via_crawl4ai: strat3 bare_urls_found={len(bare_urls)}", flush=True)
                if bare_urls:
                    print(f">>> search_via_crawl4ai: strat3 sample={bare_urls[:3]}", flush=True)
                for url in bare_urls:
                    real_url = clean_ddg_url(url)
                    if not _is_valid_http_url(real_url):
                        continue
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

            print(f">>> search_via_crawl4ai: final result count={len(results)}", flush=True)
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


async def _search_ddg_lite(query: str, n: int = 3) -> list[dict]:
    """Fetch DuckDuckGo Lite directly via HTTP POST and parse HTML for result links.

    DuckDuckGo Lite returns clean HTML with direct result links in <a> tags.
    No redirect URLs — plain, parseable HTML.
    """
    import html.parser

    search_url = "https://lite.duckduckgo.com/lite/"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.post(
                search_url,
                data={"q": query},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://lite.duckduckgo.com/",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
            html_text = resp.text
    except Exception as e:
        logger.warning("DDG Lite fetch failed: %s", e)
        return []

    if not html_text:
        print(f">>> _search_ddg_lite: empty response", flush=True)
        return []

    print(f">>> _search_ddg_lite: got {len(html_text)} bytes HTML", flush=True)

    results: list[dict] = []
    seen: set[str] = set()

    class _ResultParser(html.parser.HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_link = False
            self.pending_href = ""
            self.pending_title = ""

        def handle_starttag(self, tag, attrs):
            attrs_d = dict(attrs)
            href = attrs_d.get("href", "")
            if tag == "a" and href.startswith("http") and "duckduckgo.com" not in href:
                self.in_link = True
                self.pending_href = href
                self.pending_title = ""

        def handle_data(self, data):
            if self.in_link:
                self.pending_title += data

        def handle_endtag(self, tag):
            if tag == "a" and self.in_link:
                self.in_link = False
                if self.pending_href and self.pending_href not in seen:
                    seen.add(self.pending_href)
                    results.append({
                        "url": self.pending_href,
                        "title": self.pending_title.strip()[:200] or self.pending_href[:80],
                        "snippet": "",
                    })

    parser = _ResultParser()
    try:
        parser.feed(html_text)
    except Exception:
        pass

    print(f">>> _search_ddg_lite: parsed {len(results)} result links", flush=True)
    for r in results[:3]:
        print(f">>> _search_ddg_lite:   {r['url'][:100]} | {r['title'][:60]}", flush=True)

    return results[:n]


async def web_search(query: str, n: int = 3, config: dict | None = None) -> list[dict]:
    """Search DuckDuckGo and return top N result URLs with titles and snippets.

    Strategy: Direct DuckDuckGo Lite HTML parse → Crawl4AI → Jina fallback.

    Args:
        query: Search query string.
        n: Maximum number of results to return (default 3).
        config: Application config dict, required for Jina fallback.

    Returns:
        List of dicts with 'url', 'title', and 'snippet' keys.
    """
    try:
        # Strategy 1: Direct DuckDuckGo Lite (fast, reliable, no deps)
        results = await _search_ddg_lite(query, n)
        if results:
            print(f">>> web_search: DDG Lite direct found {len(results)} results", flush=True)
            return results

        from backend.services.research.sensory_affordances import is_crawl4ai_available

        # Crawl4AI fallback uses the HTML version (more structured links)
        html_search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"

        if is_crawl4ai_available():
            try:
                results = await search_via_crawl4ai(html_search_url, n)
                if results:
                    return results
            except (RuntimeError, Exception) as e:
                logger.warning("Crawl4AI search failed, falling back: %s", str(e)[:80])

        # Jina fallback — get raw content and extract URLs
        raw = await fetch_via_jina(html_search_url, config or {})
        if raw:
            return extract_urls_from_content(raw, n, query)

        return []
    except Exception as e:
        logger.warning("Web search failed for '%s': %s", query[:60], e)
        return []
