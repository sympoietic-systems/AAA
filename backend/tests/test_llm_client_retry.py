import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.modules.llm_client import (
    OpenAICompatibleProvider,
    RateLimitError,
)


def _make_provider(**kwargs):
    return OpenAICompatibleProvider(
        api_key=kwargs.get("api_key", "test-key"),
        model=kwargs.get("model", "test-model"),
        api_base=kwargs.get("api_base", "https://api.openai.com/v1"),
        provider_name=kwargs.get("provider_name", "openai_compatible"),
        max_retries=kwargs.get("max_retries", 2),
    )


class TestParseMessage:
    def test_parses_standard_openai_response(self):
        p = _make_provider()
        message = {"role": "assistant", "content": "Hello, world!"}
        data = {
            "model": "gpt-4",
            "choices": [{"finish_reason": "stop"}],
        }
        result = p._parse_message(message, data)
        assert result["content"] == "Hello, world!"
        assert result["model"] == "gpt-4"
        assert result["truncated"] is False
        assert result["finish_reason"] == "stop"

    def test_detects_truncation_from_length(self):
        p = _make_provider()
        message = {"role": "assistant", "content": "Truncated..."}
        data = {"choices": [{"finish_reason": "length"}]}
        result = p._parse_message(message, data)
        assert result["truncated"] is True
        assert result["finish_reason"] == "length"

    def test_detects_truncation_from_max_tokens(self):
        p = _make_provider()
        message = {"role": "assistant", "content": "Truncated..."}
        data = {"choices": [{"finish_reason": "max_tokens"}]}
        result = p._parse_message(message, data)
        assert result["truncated"] is True

    def test_uses_reasoning_when_content_empty(self):
        p = _make_provider()
        message = {"role": "assistant", "content": None, "reasoning": "I think therefore I am"}
        data = {"choices": [{"finish_reason": "stop"}]}
        result = p._parse_message(message, data)
        assert result["content"] == "I think therefore I am"
        assert result["reasoning"] == "I think therefore I am"

    def test_handles_openrouter_reasoning_details(self):
        p = _make_provider()
        message = {
            "role": "assistant",
            "content": "Final answer",
            "reasoning_details": [
                {"text": "Step 1: analyze"},
                {"text": "Step 2: conclude"},
            ],
        }
        data = {"choices": [{"finish_reason": "stop"}]}
        result = p._parse_message(message, data)
        assert "Step 1: analyze" in result["reasoning"]
        assert "Step 2: conclude" in result["reasoning"]

    def test_provider_name_preserved(self):
        p = _make_provider(provider_name="my-custom-provider")
        message = {"role": "assistant", "content": "hi"}
        data = {"choices": [{"finish_reason": "stop"}]}
        result = p._parse_message(message, data)
        assert result["provider_used"] == "my-custom-provider"


class TestRateLimitHeaders:
    def test_parses_standard_headers(self):
        p = _make_provider()
        headers = {
            "x-ratelimit-remaining-requests": "42",
            "x-ratelimit-limit-requests": "100",
            "x-ratelimit-reset-requests": "2025-01-01T00:00:00Z",
        }
        result = p._parse_rate_limit_headers(headers)
        assert result["remaining"] == 42
        assert result["limit"] == 100
        assert result["reset"] == "2025-01-01T00:00:00Z"

    def test_defaults_missing_headers(self):
        p = _make_provider()
        result = p._parse_rate_limit_headers({})
        assert result["remaining"] == 0
        assert result["limit"] == 0


class TestRateLimitError:
    def test_error_contains_rate_info(self):
        err = RateLimitError("Too many requests", retry_after=30, remaining=5, limit=100)
        assert err.retry_after == 30
        assert err.remaining == 5
        assert err.limit == 100
        assert "Too many requests" in str(err)


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retries_on_429_and_raises_rate_limit_error(self):
        p = _make_provider(max_retries=1)

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {
            "retry-after": "1",
            "x-ratelimit-remaining-requests": "0",
            "x-ratelimit-limit-requests": "100",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            try:
                await p._request_with_retry({"model": "test", "messages": []})
                raise AssertionError("Expected RateLimitError")
            except RateLimitError as e:
                assert e.remaining == 0
                assert e.limit == 100
                assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_network_error(self):
        p = _make_provider(max_retries=1)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {
            "model": "test",
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client.post = AsyncMock()
        import httpx

        mock_client.post.side_effect = [
            httpx.RequestError("Connection failed"),
            mock_response,
        ]

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await p._request_with_retry({"model": "test", "messages": []})
            assert result["content"] == "ok"
            assert mock_client.post.call_count == 2


class TestValidateConnection:
    @pytest.mark.asyncio
    async def test_validate_connection_returns_true_on_success(self):
        p = _make_provider()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {
            "model": "test",
            "choices": [{"message": {"role": "assistant", "content": "pong"}}],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            assert await p.validate_connection() is True

    @pytest.mark.asyncio
    async def test_validate_connection_returns_false_on_error(self):
        p = _make_provider()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=Exception("API error"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            assert await p.validate_connection() is False
