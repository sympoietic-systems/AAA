"""V136: recover literal Markdown escapes without fabricating JSON structure."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.research.steps import synthesize


@pytest.mark.parametrize("literal", [r"\[S13\]", r"\(x+y\)", r"path\_name", r"50\%", r"\alpha", r"\q"])
def test_v136_invalid_escape_preserves_report_characters(literal):
    result, count = synthesize._parse_synthesis_json('{"report_markdown":"' + literal + '"}')
    assert result["report_markdown"] == literal
    assert count >= 1


def test_v136_valid_json_escapes_are_unchanged():
    report = 'Citation [S13]\nA tab\t and a quote " and a slash \\ and Unicode α'
    result, count = synthesize._parse_synthesis_json(json.dumps({"report_markdown": report}))
    assert result["report_markdown"] == report and count == 0


@pytest.mark.parametrize(
    "broken",
    [
        '{"report_markdown":"truncated',
        '{"report_markdown":"bad\\u12xx"}',
        '{"report_markdown":"ok",}',
        '{"report_markdown":"' + r"\q" * 2049 + '"}',
    ],
)
def test_v136_broken_structure_unicode_and_excessive_repairs_still_fail(broken):
    with pytest.raises(ValueError):
        synthesize._parse_synthesis_json(broken)


@pytest.mark.asyncio
async def test_v136_repaired_synthesis_is_observable_and_retains_raw_response(monkeypatch):
    raw = {
        "json_data": {},
        "content": r'{"report_markdown":"Source \[S13\] supports this."}',
        "error": "invalid_json_completion",
    }
    monkeypatch.setattr(synthesize, "generate_unified", AsyncMock(return_value=raw))
    state = {}
    orch = SimpleNamespace(
        _state=SimpleNamespace(llm_provider=object()),
        _get_state=lambda _: state,
        _get_cached_phase=lambda *args: {"persona": "persona", "system_prompt": "system"},
        _get_parsed_urls=lambda _: [],
        _format_reflection_markdown=lambda *args, **kwargs: "(none)",
        _log_meta=MagicMock(),
        _log_llm_response=MagicMock(),
        _save_llm_response_to_step_data=MagicMock(),
        step_repo=None,
        _TRUNC_META_LOG=2000,
    )
    report = await synthesize.run_synthesis(orch, "task", "objective", "goal", [], 0, step_id="step")
    assert report == r"Source \[S13\] supports this."
    assert state["delivery_degraded"] is True
    orch._save_llm_response_to_step_data.assert_called_once_with("step", raw)
    event = orch._log_meta.call_args
    assert event.args[1] == "synthesis_json_escape_repaired"
    assert event.args[2] == {"invalid_escapes_preserved": 2}


def test_v136_long_report_repairs_more_than_64_citation_escapes():
    report = r"Claim \[S13\]. " * 100
    result, repairs = synthesize._parse_synthesis_json('{"report_markdown":"' + report + '"}')
    assert result["report_markdown"] == report
    assert repairs == 200
