from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.daily_email import DailyEmailConfig, DailyEmailWorker, build_message
from backend.storage.migrations.m071_daily_email import up
from backend.storage.repositories.telemetry.daily_email_repository import DailyEmailRepository


@pytest.fixture
def worker(tmp_path):
    import sqlite3

    path = tmp_path / "daily_test.db"
    with sqlite3.connect(path) as conn:
        up(conn)
    config = DailyEmailConfig("smtp.titan.email", "symbia@sympoietic.systems", "b@vasily.onl", "secret")
    instance = DailyEmailWorker(SimpleNamespace(daily_summary_repo=DailyEmailRepository(path)), config)
    instance.service = SimpleNamespace(
        get_daily_details=AsyncMock(
            return_value={
                "date": "2026-11-17",
                "summary": None,
                "metrics": {"message_count": 2},
                "memory_nodes": [{"node_type": "concept", "intra_active_text": "A memory", "intensity": 0.8}],
                "evolution": {"beliefs": [{"event_type": "created", "label": "Belief", "statement": "Statement"}]},
                "conversations": [{"id": "conversation-1", "title": "Conversation", "message_count": 2}],
                "research_tasks": [
                    {"id": "research-1", "title": "Research", "objective": "Objective", "status": "completed"}
                ],
            }
        ),
        generate_summary=AsyncMock(return_value={"summary": "Daily synthesis"}),
    )
    return instance


@pytest.mark.asyncio
async def test_delivery_generates_full_review_and_survives_restart(worker):
    now = datetime(2026, 11, 18, 0, 5, tzinfo=UTC)
    with patch("backend.services.daily_email.send_message") as send:
        assert await worker.deliver_due(now)
        body = send.call_args.args[0].get_body(preferencelist=("plain",)).get_content()
        for text in ("Daily synthesis", "A memory", "Belief", "Conversation", "Research", "date=2026-11-17"):
            assert text in body
        assert not await worker.deliver_due(now)
        assert send.call_count == 1
    assert not worker.repo.claim("2026-11-17", worker.config.recipient, now.timestamp() + 90000)


@pytest.mark.asyncio
async def test_failure_is_retryable(worker):
    now = datetime(2026, 11, 18, 0, 5, tzinfo=UTC)
    with patch("backend.services.daily_email.send_message", side_effect=OSError("offline")), pytest.raises(OSError):
        await worker.deliver_due(now)
    with patch("backend.services.daily_email.send_message"):
        assert await worker.deliver_due(now)


@pytest.mark.asyncio
async def test_before_send_hour_does_nothing(worker):
    assert not await worker.deliver_due(datetime(2026, 11, 17, 23, 59, tzinfo=UTC))
    worker.service.get_daily_details.assert_not_called()


def test_claim_excludes_competing_workers_and_recovers_expired_lease(worker):
    assert worker.repo.claim("2026-11-17", "b@vasily.onl", 100)
    assert not worker.repo.claim("2026-11-17", "b@vasily.onl", 101)
    assert worker.repo.claim("2026-11-17", "b@vasily.onl", 3701)


def test_message_has_html_plain_text_and_hidden_password(worker):
    details = worker.service.get_daily_details.return_value
    message = build_message(details, worker.config)
    assert message["To"] == "b@vasily.onl"
    assert message.get_content_type() == "multipart/alternative"
    assert message.get_body(preferencelist=("plain",)) is not None
    assert message.get_body(preferencelist=("html",)) is not None
    assert "secret" not in repr(worker.config)


@pytest.mark.asyncio
async def test_cached_summary_is_reused(worker):
    worker.service.get_daily_details.return_value["summary"] = "Existing summary"
    with patch("backend.services.daily_email.send_message"):
        assert await worker.deliver_due(datetime(2026, 11, 18, 0, 5, tzinfo=UTC))
    worker.service.generate_summary.assert_not_called()


def test_config_requires_opt_in_and_valid_settings(monkeypatch):
    monkeypatch.delenv("AAA_DAILY_EMAIL_ENABLED", raising=False)
    assert DailyEmailConfig.from_env() is None
    monkeypatch.setenv("AAA_DAILY_EMAIL_ENABLED", "true")
    monkeypatch.setenv("AAA_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("AAA_DAILY_EMAIL_HOUR", "25")
    with pytest.raises(ValueError):
        DailyEmailConfig.from_env()


def test_html_renders_markdown_links_and_escapes_untrusted_content(worker):
    details = worker.service.get_daily_details.return_value
    details["summary"] = (
        "## A useful day\n\n**Bold insight** and [source](https://example.org/paper). "
        "Also https://example.org/reference\n\n"
        '<script>alert("unsafe")</script>\n\n'
        "[bad](javascript:alert(1))\n\n![tracking](https://example.org/pixel)"
    )
    message = build_message(details, worker.config)
    html = message.get_body(preferencelist=("html",)).get_content()
    assert "<strong>Bold insight</strong>" in html
    assert 'href="https://example.org/paper"' in html
    assert 'href="https://example.org/reference"' in html
    assert 'href="https://aaa.sympoietic.systems/nodes?c=conversation-1"' in html
    assert 'href="https://aaa.sympoietic.systems/research?id=research-1"' in html
    assert "&amp;sub=nodes" in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert 'href="javascript:' not in html
    assert "<img" not in html
