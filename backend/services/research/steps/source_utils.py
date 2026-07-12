"""Shared source utility functions migrated from legacy tools.py.

These are pure helper functions with no step-class dependency,
used across ParseStep, DigestStep, ConsolidateStep, and SynthesizeStep.
"""

import logging
import re

logger = logging.getLogger("aaa.research_orchestrator")


def classify_source_status(raw_content: str | None) -> str:
    """Classify the quality of scraped raw content."""
    if not raw_content or not raw_content.strip():
        return "empty"
    c = raw_content.strip()
    if c.startswith("Error:"):
        err = c[6:].strip().lower()
        if "timeout" in err:
            return "failed (timeout)"
        if "dns" in err or "resolve" in err:
            return "failed (dns error)"
        return f"failed ({err[:40]})"
    if len(c) < 200:
        return "too short"
    junk_patterns = ["security check required", "cloudflare", "enable javascript", "please complete the security check"]
    c_lower = c[:1000].lower()
    if any(p in c_lower for p in junk_patterns):
        return "blocked (anti-bot)"
    if re.match(r"^(skip|close|open navigation|sign in|sign up)", c[:100].strip(), re.IGNORECASE):
        return "paywall"
    return "ok"


def apply_unified_references(
    parsed_urls_list: list[dict],
    findings: list[str],
    followups: list[str] = None,
    gaps: list[str] = None,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Build a unified source ID map (S1, S2, ...) from parsed_urls_list,
    then replace source titles in findings/followups/gaps with [S1], [S2] etc.

    Returns:
        parsed_urls_formatted: formatted lines with [S##] prefix.
        compressed_findings: findings with source titles replaced by [S##].
        compressed_followups: followups with source titles replaced by [S##].
        compressed_gaps: gaps with source titles replaced by [S##].
    """
    # If parsed_urls_list is empty, dynamically extract source keys from findings
    if not parsed_urls_list:
        seen_srcs = []
        for f in findings:
            match = re.match(r"^\[(.*?)\]:\s*(.*)$", f)
            if match:
                src_key = match.group(1)
                if src_key not in seen_srcs:
                    seen_srcs.append(src_key)
        parsed_urls_list = [{"url": s, "title": s, "status": ""} for s in seen_srcs]

    # Build source mapping: title -> S##, url -> S##
    source_map = {}
    parsed_urls_formatted = []

    for idx, u in enumerate(parsed_urls_list, 1):
        sid = f"S{idx}"
        title = u.get("title") or u["url"]
        url = u["url"]
        status = u.get("status", "")

        source_map[title] = sid
        source_map[url] = sid
        if len(title) > 80:
            source_map[title[:80]] = sid

        status_suffix = f" — {status}" if status else ""
        if title and title != url:
            parsed_urls_formatted.append(f"- [{sid}] [{title}]({url}){status_suffix}")
        else:
            parsed_urls_formatted.append(f"- [{sid}] {url}{status_suffix}")

    def compress_item(item_str: str) -> str:
        match = re.match(r"^\[(.*?)\]:\s*(.*)$", item_str)
        if match:
            src_key = match.group(1)
            content = match.group(2)
            if src_key in source_map:
                return f"[{source_map[src_key]}]: {content}"
            for key, sid in source_map.items():
                if src_key.startswith(key) or key.startswith(src_key):
                    return f"[{sid}]: {content}"
        return item_str

    compressed_findings = [compress_item(f) for f in findings]
    compressed_followups = [compress_item(f) for f in (followups or [])]
    compressed_gaps = [compress_item(g) for g in (gaps or [])]

    return parsed_urls_formatted, compressed_findings, compressed_followups, compressed_gaps
