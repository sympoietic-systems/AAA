"""Email-safe HTML for daily review data, with links to supported application routes."""

from html import escape
from typing import Any
from urllib.parse import urlencode, urlsplit

from markdown_it import MarkdownIt

BASE_URL = "https://aaa.sympoietic.systems"


def app_link(path: str, **query: str) -> str:
    return f"{BASE_URL}{path}?{urlencode(query)}"


def render_review(details: dict[str, Any]) -> str:
    date = str(details["date"])
    review_url = app_link("/agent", tab="daily", date=date)
    markdown = MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("linkify").enable("table")
    # Reviews are text: never embed remote images or content-supplied HTML in mail.
    markdown.disable("image")

    def rich(value: object) -> str:
        tokens = markdown.parse(str(value or ""))
        for token in tokens:
            for child in token.children or []:
                if child.type == "link_open":
                    href = str(child.attrGet("href") or "")
                    scheme = urlsplit(href).scheme.lower()
                    if scheme not in {"https", "http", "mailto"}:
                        child.attrSet("href", review_url)
        rendered = str(markdown.renderer.render(tokens, markdown.options, {}))
        styles = {
            "p": "margin:0 0 14px;line-height:1.65",
            "h1": "font-size:24px;margin:22px 0 12px",
            "h2": "font-size:21px;margin:22px 0 12px",
            "h3": "font-size:18px;margin:20px 0 10px",
            "li": "margin-bottom:8px;line-height:1.6",
            "blockquote": "margin:16px 0;padding-left:16px;border-left:3px solid #999;color:#444",
            "table": "border-collapse:collapse;width:100%;margin:16px 0",
            "td": "border:1px solid #ccc;padding:8px;text-align:left",
            "th": "border:1px solid #ccc;padding:8px;text-align:left",
            "pre": "white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f4f4;padding:12px",
        }
        for tag, style in styles.items():
            rendered = rendered.replace(f"<{tag}>", f'<{tag} style="{style}">')
        return rendered.replace("<a ", '<a style="color:#111;text-decoration:underline;overflow-wrap:anywhere" ')

    def link(label: object, url: str) -> str:
        return (
            f'<a href="{escape(url, quote=True)}" style="color:#111;text-decoration:underline">{escape(str(label))}</a>'
        )

    def section(title: str, sub: str, content: str) -> str:
        url = app_link("/agent", tab="daily", date=date, sub=sub)
        return (
            f'<h2 style="font-size:20px;margin:32px 0 16px;padding-top:24px;border-top:1px solid #ccc">'
            f"{link(title, url)}</h2>{content}"
        )

    metrics = "".join(
        f'<tr><td style="padding:5px 16px 5px 0;color:#555">{escape(key.replace("_", " ").title())}</td>'
        f'<td style="padding:5px 0;text-align:right;font-weight:bold">{escape(str(value))}</td></tr>'
        for key, value in details["metrics"].items()
    )
    summary = rich(details.get("summary") or "No summary recorded.")
    nodes = (
        "".join(
            f'<p style="margin:20px 0 6px;color:#555;font-size:12px">{escape(str(node["node_type"]).upper())}'
            f" · intensity {escape(str(node['intensity']))}</p>{rich(node['intra_active_text'])}"
            for node in details["memory_nodes"]
        )
        or "<p>No memory nodes recorded.</p>"
    )
    evolution = []
    for kind, events in details["evolution"].items():
        evolution.append(f'<h3 style="font-size:16px;margin:20px 0 12px">{escape(kind.title())} · {len(events)}</h3>')
        for event in events:
            label = event.get("label") or event.get("name") or "Untitled"
            entity_id = event.get("belief_id") if kind == "beliefs" else event.get("skill_id")
            url = app_link("/agent", tab="personality", sub=kind, **({"id": str(entity_id)} if entity_id else {}))
            evolution.append(
                f'<p style="margin:16px 0 6px"><strong>{link(label, url)}</strong>'
                f" — {escape(str(event['event_type']))}</p>"
            )
            evolution.append(rich(event.get("statement")))
            if event.get("rationale"):
                evolution.append(rich(event["rationale"]))
    activity = []
    for conversation in details["conversations"]:
        url = app_link("/nodes", c=str(conversation["id"])) if conversation.get("id") else review_url
        activity.append(
            f"<p>{link(conversation['title'], url)} · {escape(str(conversation['message_count']))} messages</p>"
        )
    for task in details["research_tasks"]:
        url = app_link("/research", id=str(task["id"])) if task.get("id") else review_url
        activity.append(
            f"<p><strong>{link(task['title'], url)}</strong> · {escape(str(task['status']))}</p>"
            f"{rich(task['objective'])}"
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        '<body style="margin:0;padding:0;background:#fff;color:#111">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:680px">'
        '<tr><td style="padding:32px 24px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;overflow-wrap:anywhere">'
        '<p style="font-size:12px;letter-spacing:2px;margin:0 0 12px">AAA / SYMBIA</p>'
        f'<h1 style="font-size:30px;line-height:1.2;margin:0 0 8px">Daily review</h1>'
        f'<p style="color:#555;margin:0 0 20px">{escape(date)} · UTC review day</p>'
        f"<p>{link('Open the full daily review →', review_url)}</p>"
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0">{metrics}</table>'
        f"{section('Summary', 'summary', summary)}{section('Memory nodes', 'nodes', nodes)}"
        f"{section('Evolution', 'evolution', ''.join(evolution))}"
        f"{section('Activity', 'activity', ''.join(activity) or '<p>No activity recorded.</p>')}"
        '<p style="margin:32px 0 0;padding-top:20px;border-top:1px solid #ccc;color:#666;font-size:12px">'
        "Generated from AAA’s daily review. Item links open the authenticated application.</p>"
        "</td></tr></table></td></tr></table></body></html>"
    )
