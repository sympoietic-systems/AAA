import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.modules.llm_client import (
    KeyManager,
    ModelPoolProvider,
    OpenAICompatibleProvider,
    RateLimitError,
    generate_unified,
)


class TestModelPool(unittest.IsolatedAsyncioTestCase):
    def test_key_manager_basic(self):
        km = KeyManager(["key1", "key2"], cooldown_seconds=2)
        self.assertTrue(km.has_keys())

        # Get key 1
        k1 = km.get_available_key()
        self.assertEqual(k1, "key1")

        # Get key 2 (key1 was not marked exhausted, but KeyManager iterates keys sequentially)
        # Wait, get_available_key returns the first non-exhausted key in the list.
        # So it should return "key1" again if it is not exhausted.
        k1_again = km.get_available_key()
        self.assertEqual(k1_again, "key1")

        # Exhaust key1
        km.mark_key_exhausted("key1")

        # Now get_available_key should return "key2"
        k2 = km.get_available_key()
        self.assertEqual(k2, "key2")

        # Exhaust key2 too
        km.mark_key_exhausted("key2")

        # Now no key should be available
        self.assertIsNone(km.get_available_key())

    @patch("backend.modules.llm_client.OpenAICompatibleProvider.generate")
    async def test_model_pool_routing_and_rotation(self, mock_generate):
        # We set up a ModelPoolProvider with two models:
        # 1. google_router/gemini-2.5-flash (uses google_keys)
        # 2. openrouter_router/google/gemma-4-26b-a4b-it:free (uses openrouter_keys)

        provider = ModelPoolProvider(
            api_key="or_key_default",
            models=["google_router/gemini-2.5-flash", "openrouter_router/google/gemma-4-26b-a4b-it:free"],
            fallback_model="openrouter_router/nvidia/nemotron-nano-9b-v2:free",
            google_keys=["g_key1", "g_key2"],
            openrouter_keys=["or_key1"],
            cooldown_seconds=10,
        )

        # Setup mock generate behaviour:
        # Call 1: for gemini-2.5-flash with g_key1 -> raise RateLimitError
        # Call 2: for gemini-2.5-flash with g_key2 -> success!

        call_count = 0

        def side_effect(messages, **params):
            nonlocal call_count
            call_count += 1
            # We check the instance attributes of the provider that called us
            # mock_generate is called on an instance of OpenAICompatibleProvider
            # We can find out which model and api_key it has by checking mock_generate's call args or self reference,
            # but since generate is mocked, we can inspect mock_generate.call_args_list inside the test.
            if call_count == 1:
                raise RateLimitError("rate limited")
            return {"content": f"Success from call {call_count}", "thinking": None}

        mock_generate.side_effect = side_effect

        result = await provider.generate([{"role": "user", "content": "hello"}])

        # Check that we succeeded
        self.assertEqual(result["content"], "Success from call 2")

        # Verify the providers created and their parameters
        # Total calls to mock_generate should be 2
        self.assertEqual(mock_generate.call_count, 2)

        # The first call failed, key g_key1 should be marked exhausted
        self.assertIsNone(
            provider._google_key_mgr.get_available_key()
            if provider._google_key_mgr.get_available_key() == "g_key1"
            else None
        )
        # Wait, if g_key1 is exhausted, the next available key should be g_key2
        self.assertEqual(provider._google_key_mgr.get_available_key(), "g_key2")

    @patch("backend.modules.llm_client.OpenAICompatibleProvider.generate")
    async def test_fallback_to_second_model(self, mock_generate):
        # Setup provider where all google keys fail, so it falls back to OpenRouter model
        provider = ModelPoolProvider(
            api_key="or_key_default",
            models=["google_router/gemini-2.5-flash", "openrouter_router/google/gemma-4-26b-a4b-it:free"],
            google_keys=["g_key1"],
            openrouter_keys=["or_key1"],
            cooldown_seconds=10,
        )

        def side_effect(messages, **params):
            # We determine which key was used by looking at mock_generate.call_args_list or similar.
            # But simpler: first call is Google (fails), second call is OpenRouter (succeeds)
            if mock_generate.call_count == 1:
                raise RateLimitError("google rate limit")
            return {"content": "OpenRouter Success", "thinking": None}

        mock_generate.side_effect = side_effect

        result = await provider.generate([{"role": "user", "content": "hello"}])
        self.assertEqual(result["content"], "OpenRouter Success")
        self.assertEqual(mock_generate.call_count, 2)

    @patch("backend.modules.llm_client.OpenAICompatibleProvider.generate")
    async def test_deepseek_routing_with_thinking(self, mock_generate):
        provider = ModelPoolProvider(
            api_key="default",
            models=["deepseek_router/deepseek-v4-pro"],
            deepseek_keys=["ds_key1"],
            thinking=True,
            reasoning_effort="medium",
        )

        mock_generate.return_value = {"content": "DeepSeek response", "thinking": "thinking trace"}

        result = await provider.generate([{"role": "user", "content": "hello"}])
        self.assertEqual(result["content"], "DeepSeek response")
        self.assertEqual(result["thinking"], "thinking trace")

        # Verify the OpenAICompatibleProvider was initialized with thinking=True
        # We can inspect the parameters passed during generate() or the mock call args
        self.assertEqual(mock_generate.call_count, 1)

    @patch("backend.modules.llm_client.OpenAICompatibleProvider.generate", autospec=True)
    async def test_last_working_model_stateful_prioritization(self, mock_generate):
        provider = ModelPoolProvider(
            api_key="or_key_default",
            models=["google_router/gemini-2.5-flash", "openrouter_router/google/gemma-4-26b-a4b-it:free"],
            google_keys=["g_key1"],
            openrouter_keys=["or_key1"],
            cooldown_seconds=300,
        )

        calls = []

        async def side_effect(provider_inst, messages, **params):
            calls.append(provider_inst._model)
            if provider_inst._model == "gemini-2.5-flash":
                raise RateLimitError("google rate limit")
            return {"content": f"Success from {provider_inst._model}", "thinking": None}

        mock_generate.side_effect = side_effect

        # --- Request 1 ---
        result1 = await provider.generate([{"role": "user", "content": "hello"}])
        self.assertEqual(result1["content"], "Success from google/gemma-4-26b-a4b-it:free")
        self.assertEqual(provider._last_model_used, "openrouter_router/google/gemma-4-26b-a4b-it:free")
        self.assertGreater(provider._last_model_time, 0.0)
        self.assertEqual(calls, ["gemini-2.5-flash", "google/gemma-4-26b-a4b-it:free"])

        # Reset recorded calls
        calls.clear()

        # --- Request 2 ---
        result2 = await provider.generate([{"role": "user", "content": "hello again"}])
        self.assertEqual(result2["content"], "Success from google/gemma-4-26b-a4b-it:free")
        self.assertEqual(provider._last_model_used, "openrouter_router/google/gemma-4-26b-a4b-it:free")
        self.assertEqual(calls, ["google/gemma-4-26b-a4b-it:free"])

        # Reset recorded calls
        calls.clear()

        # --- Request 3 ---
        provider._last_model_time -= 301
        for m in list(provider._exhausted.keys()):
            provider._exhausted[m] -= 301
        for k in list(provider._google_key_mgr._exhausted.keys()):
            provider._google_key_mgr._exhausted[k] -= 301

        async def side_effect_success(provider_inst, messages, **params):
            calls.append(provider_inst._model)
            return {"content": f"Success from {provider_inst._model}", "thinking": None}

        mock_generate.side_effect = side_effect_success

        result3 = await provider.generate([{"role": "user", "content": "hello after cooldown"}])
        self.assertEqual(result3["content"], "Success from gemini-2.5-flash")
        self.assertEqual(provider._last_model_used, "google_router/gemini-2.5-flash")
        self.assertEqual(calls, ["gemini-2.5-flash"])

    @patch("httpx.AsyncClient.post")
    async def test_openai_compatible_max_tokens(self, mock_post):
        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"role": "assistant", "content": "hello"}}]}
        mock_post.return_value = mock_response

        # 1. Non-thinking provider
        provider = OpenAICompatibleProvider(
            api_key="test_key",
            model="test_model",
            api_base="https://api.test.com",
        )
        await provider.generate([{"role": "user", "content": "hi"}], max_tokens=123)

        # Check mock_post call arguments
        self.assertEqual(mock_post.call_count, 1)
        args, kwargs = mock_post.call_args
        body = kwargs["json"]
        self.assertEqual(body["max_tokens"], 123)
        self.assertEqual(body["temperature"], 0.7)  # default parameter

        # Reset mock
        mock_post.reset_mock()

        # 2. Thinking provider
        provider_thinking = OpenAICompatibleProvider(
            api_key="test_key",
            model="test_model",
            api_base="https://api.test.com",
            thinking=True,
        )
        await provider_thinking.generate([{"role": "user", "content": "hi"}], max_tokens=456)

        self.assertEqual(mock_post.call_count, 1)
        args, kwargs = mock_post.call_args
        body = kwargs["json"]
        self.assertEqual(body["max_tokens"], 456)
        self.assertNotIn("temperature", body)  # temperature not sent in thinking mode

    @patch("backend.modules.llm_client.OpenAICompatibleProvider.generate")
    @patch("backend.modules.llm_client.asyncio.sleep")
    async def test_connection_error_retry_and_exhaustion(self, mock_sleep, mock_generate):
        provider = ModelPoolProvider(
            api_key="or_key_default",
            models=["google_router/gemini-2.5-flash"],
            fallback_model="",
            google_keys=["g_key1"],
            cooldown_seconds=10,
        )

        # Scenario: First call raises RequestError. Retry succeeds.
        call_count = 0

        def side_effect(messages, **params):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                import httpx

                raise httpx.RequestError("connection lost")
            return {"content": "Success after retry", "thinking": None}

        mock_generate.side_effect = side_effect

        result = await provider.generate([{"role": "user", "content": "hello"}])
        self.assertEqual(result["content"], "Success after retry")
        self.assertEqual(mock_generate.call_count, 2)
        mock_sleep.assert_called_once_with(10)

        # Verify key g_key1 is NOT exhausted (since the retry succeeded)
        self.assertEqual(provider._google_key_mgr.get_available_key(), "g_key1")

    @patch("backend.modules.llm_client.OpenAICompatibleProvider.generate")
    @patch("backend.modules.llm_client.asyncio.sleep")
    async def test_connection_error_retry_exhausts_key(self, mock_sleep, mock_generate):
        provider = ModelPoolProvider(
            api_key="or_key_default",
            models=["google_router/gemini-2.5-flash"],
            fallback_model="",
            google_keys=["g_key1"],
            cooldown_seconds=10,
        )

        import httpx

        mock_generate.side_effect = httpx.RequestError("connection lost")

        with self.assertRaises(RateLimitError):
            await provider.generate([{"role": "user", "content": "hello"}])

        # 1 original attempt + 1 retry = 2 calls
        self.assertEqual(mock_generate.call_count, 2)
        mock_sleep.assert_called_once_with(10)

        # Since both failed, key is exhausted
        self.assertIsNone(provider._google_key_mgr.get_available_key())

    @patch("backend.modules.llm_client.OpenAICompatibleProvider.generate")
    async def test_generate_unified_forwards_thinking_override(self, mock_generate):
        mock_generate.return_value = {"content": "ok", "thinking": None, "model": "test"}
        provider = OpenAICompatibleProvider(
            api_key="key",
            model="test-model",
            api_base="https://api.example.com",
            provider_name="test",
            thinking=False,
        )
        result = await generate_unified(
            provider,
            system_prompt="s",
            user_prompt="u",
            thinking_override=True,
        )
        self.assertEqual(result["content"], "ok")
        call_kwargs = mock_generate.call_args[1]
        self.assertTrue(call_kwargs.get("thinking_override"))

    @patch("backend.modules.llm_client.OpenAICompatibleProvider.generate")
    async def test_generate_unified_thinking_override_absent(self, mock_generate):
        mock_generate.return_value = {"content": "ok", "thinking": None, "model": "test"}
        provider = OpenAICompatibleProvider(
            api_key="key",
            model="test-model",
            api_base="https://api.example.com",
            provider_name="test",
            thinking=False,
        )
        result = await generate_unified(
            provider,
            system_prompt="s",
            user_prompt="u",
        )
        self.assertEqual(result["content"], "ok")
        call_kwargs = mock_generate.call_args[1]
        self.assertNotIn("thinking_override", call_kwargs)


if __name__ == "__main__":
    unittest.main()
