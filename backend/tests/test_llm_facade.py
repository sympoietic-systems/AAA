import json

import pytest

from backend.modules import llm_client
from backend.modules.llm_http import OpenAICompatibleProvider, OpenRouterProvider
from backend.modules.llm_parsing import _parse_json_safely, generate_unified
from backend.modules.llm_pool import KeyManager, ModelPoolProvider
from backend.modules.llm_protocol import BaseLLMProvider, RateLimitError


def test_llm_client_facade_preserves_historical_exports():
    assert llm_client.BaseLLMProvider is BaseLLMProvider
    assert llm_client.OpenAICompatibleProvider is OpenAICompatibleProvider
    assert llm_client.OpenRouterProvider is OpenRouterProvider
    assert llm_client.KeyManager is KeyManager
    assert llm_client.ModelPoolProvider is ModelPoolProvider
    assert llm_client.RateLimitError is RateLimitError
    assert llm_client.generate_unified is generate_unified
    assert llm_client._parse_json_safely is _parse_json_safely


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('<think>ignore</think>{"ok": true,}', {"ok": True}),
        ('prefix {"items": [1, 2]', {"items": [1, 2]}),
        ('{"line": "one\ntwo"}', {"line": "one\ntwo"}),
    ],
)
def test_json_parser_retains_tolerant_repair_contract(raw: str, expected: dict[str, object]):
    assert _parse_json_safely(raw) == expected


def test_json_parser_raises_for_non_json_text():
    with pytest.raises(json.JSONDecodeError):
        _parse_json_safely("plain text")
