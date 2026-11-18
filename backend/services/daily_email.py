"""Opt-in daily review delivery using the same data as the daily agent tab."""

import asyncio
import logging
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import format_datetime
from typing import Any
from zoneinfo import ZoneInfo

from backend.services.daily_email_rendering import render_review
from backend.services.daily_summary import DailySummaryService
from backend.storage.repositories.telemetry.daily_email_repository import DailyEmailRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailyEmailConfig:
    host: str
    sender: str
    recipient: str
    password: str = field(repr=False)
    timezone: str = "Asia/Shanghai"
    hour: int = 8
    port: int = 465

    @classmethod
    def from_env(cls) -> "DailyEmailConfig | None":
        if os.getenv("AAA_DAILY_EMAIL_ENABLED", "false").lower() != "true":
            return None
        config = cls(
            host=os.getenv("AAA_SMTP_HOST", "smtp.titan.email"),
            sender=os.getenv("AAA_SMTP_USER", "info@sympoietic.systems"),
            recipient=os.getenv("AAA_DAILY_EMAIL_TO", "b@vasily.onl"),
            password=os.environ["AAA_SMTP_PASSWORD"],
            timezone=os.getenv("AAA_DAILY_EMAIL_TIMEZONE", "Asia/Shanghai"),
            hour=int(os.getenv("AAA_DAILY_EMAIL_HOUR", "8")),
            port=int(os.getenv("AAA_SMTP_PORT", "465")),
        )
        ZoneInfo(config.timezone)
        if not 0 <= config.hour <= 23 or config.port not in (465, 587):
            raise ValueError("Daily email requires hour 0..23 and SMTP port 465 or 587")
        if not config.password or any(c in config.sender + config.recipient for c in "\r\n"):
            raise ValueError("Invalid daily email credentials or addresses")
        return config


def build_message(details: dict[str, Any], config: DailyEmailConfig) -> EmailMessage:
    date = details["date"]
    link = f"https://aaa.sympoietic.systems/agent?tab=daily&date={date}"
    lines = [
        f"AAA Daily Review — {date}",
        link,
        "",
        "SUMMARY",
        details.get("summary") or "No summary.",
        "",
        "MEMORY NODES",
    ]
    for node in details["memory_nodes"]:
        lines.append(f"- [{node['node_type']}] {node['intra_active_text']} (intensity: {node['intensity']})")
    if not details["memory_nodes"]:
        lines.append("No memory nodes recorded.")
    lines.extend(["", "EVOLUTION"])
    for kind, events in details["evolution"].items():
        lines.append(f"{kind.title()}: {len(events)}")
        for event in events:
            lines.append(
                f"- [{event['event_type']}] {event.get('label') or event.get('name')}: "
                f"{event.get('statement') or ''} {event.get('rationale') or ''}"
            )
    lines.extend(["", "ACTIVITY"])
    for key, value in details["metrics"].items():
        lines.append(f"{key.replace('_', ' ').title()}: {value}")
    for conversation in details["conversations"]:
        lines.append(f"- Conversation: {conversation['title']} ({conversation['message_count']} messages)")
    for task in details["research_tasks"]:
        lines.append(f"- Research [{task['status']}]: {task['title']} — {task['objective']}")
    message = EmailMessage()
    message["From"] = config.sender
    message["To"] = config.recipient
    message["Subject"] = f"AAA Daily Review — {date}"
    message["Date"] = format_datetime(datetime.now(UTC))
    # Stable identifier aids duplicate recognition after ambiguous SMTP acknowledgement.
    message["Message-ID"] = f"<aaa-daily-{date}@{config.sender.split('@')[-1]}>"
    message.set_content("\n".join(lines))
    message.add_alternative(render_review(details), subtype="html")
    return message


def send_message(message: EmailMessage, config: DailyEmailConfig) -> None:
    context = ssl.create_default_context()
    if config.port == 465:
        with smtplib.SMTP_SSL(config.host, config.port, timeout=60, context=context) as smtp:
            smtp.login(config.sender, config.password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(config.host, config.port, timeout=60) as smtp:
            smtp.starttls(context=context)
            smtp.login(config.sender, config.password)
            smtp.send_message(message)


class DailyEmailWorker:
    def __init__(self, state: Any, config: DailyEmailConfig):
        # Any is the compatibility boundary to the legacy daily-summary service.
        self.service = DailySummaryService(state)
        self.repo = DailyEmailRepository(state.daily_summary_repo.db_path)
        self.config = config

    async def deliver_due(self, now: datetime) -> bool:
        local = now.astimezone(ZoneInfo(self.config.timezone))
        if local.hour < self.config.hour:
            return False
        # Review queries use UTC calendar dates. Never summarize an unfinished UTC day.
        date = min(local.date() - timedelta(days=1), now.astimezone(UTC).date() - timedelta(days=1)).isoformat()
        if not await asyncio.to_thread(self.repo.claim, date, self.config.recipient, now.timestamp()):
            return False
        try:
            async with asyncio.timeout(1800):
                details = await self.service.get_daily_details(date)
                if not details.get("summary"):
                    generated = await self.service.generate_summary(date)
                    details["summary"] = generated["summary"]
                await asyncio.to_thread(send_message, build_message(details, self.config), self.config)
            await asyncio.to_thread(self.repo.mark_sent, date, self.config.recipient, datetime.now(UTC).timestamp())
        except Exception:
            await asyncio.to_thread(self.repo.release, date, self.config.recipient)
            raise
        logger.info("Daily review email sent for %s", date)
        return True

    async def run(self) -> None:
        while True:
            try:
                await self.deliver_due(datetime.now(UTC))
            except Exception:
                logger.exception("Daily review email failed; retrying in five minutes")
            await asyncio.sleep(300)
