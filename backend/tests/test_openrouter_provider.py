import unittest
from unittest.mock import MagicMock, patch

from backend.config import _apply_env_overrides
from backend.modules.llm_client import ModelPoolProvider, OpenRouterProvider
from backend.modules.providers.openrouter_utils import (
    build_openrouter_provider_config,
    resolve_openrouter_provider_config,
)


class TestOpenRouterProviderConfig(unittest.IsolatedAsyncioTestCase):
    def test_build_openrouter_provider_config_string_list(self):
        body = {}
        provider_params = {
            "order": "Chutes, DeepInfra",
            "allow_fallbacks": "true",
            "ignore": "Together",
        }
        build_openrouter_provider_config(body, provider_params)
        self.assertIn("provider", body)
        self.assertEqual(body["provider"]["order"], ["Chutes", "DeepInfra"])
        self.assertTrue(body["provider"]["allow_fallbacks"])
        self.assertEqual(body["provider"]["ignore"], ["Together"])

    def test_build_openrouter_provider_config_list(self):
        body = {}
        provider_params = {
            "order": ["Chutes", "DeepInfra"],
            "allow_fallbacks": False,
        }
        build_openrouter_provider_config(body, provider_params)
        self.assertIn("provider", body)
        self.assertEqual(body["provider"]["order"], ["Chutes", "DeepInfra"])
        self.assertFalse(body["provider"]["allow_fallbacks"])

    def test_resolve_openrouter_provider_config(self):
        providers_map = {
            "deepseek/deepseek-chat": "Chutes,DeepInfra",
            "meta-llama/*": {"order": ["Together", "Nebius"], "allow_fallbacks": False},
        }
        global_provider = {"order": ["GlobalProvider"]}

        # 1. Exact match
        res_exact = resolve_openrouter_provider_config("deepseek/deepseek-chat", global_provider, providers_map)
        self.assertEqual(res_exact, {"order": ["Chutes", "DeepInfra"]})

        # 2. Wildcard match
        res_wildcard = resolve_openrouter_provider_config(
            "meta-llama/llama-3.3-70b-instruct", global_provider, providers_map
        )
        self.assertEqual(res_wildcard, {"order": ["Together", "Nebius"], "allow_fallbacks": False})

        # 3. Unmatched model -> fallback to global provider
        res_fallback = resolve_openrouter_provider_config(
            "google/gemma-4-26b-a4b-it:free", global_provider, providers_map
        )
        self.assertEqual(res_fallback, {"order": ["GlobalProvider"]})

        # 4. No map and no global provider -> None (lets OpenRouter decide)
        res_none = resolve_openrouter_provider_config("google/gemma-4-26b-a4b-it:free", None, None)
        self.assertIsNone(res_none)

    @patch("httpx.AsyncClient.post")
    async def test_no_provider_specified_omits_provider_key(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "default routing", "role": "assistant"}}]
        }
        mock_post.return_value = mock_response

        # No openrouter_provider passed
        provider = OpenRouterProvider(
            api_key="sk-or-dummy",
            model="deepseek/deepseek-chat",
        )
        res = await provider.generate([{"role": "user", "content": "hi"}])
        self.assertEqual(res["content"], "default routing")

        # Verify "provider" is NOT sent in request JSON body
        called_json = mock_post.call_args.kwargs.get("json", {})
        self.assertNotIn("provider", called_json)

    @patch("httpx.AsyncClient.post")
    async def test_openrouter_provider_attaches_routing(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "hello world", "role": "assistant"}}]}
        mock_post.return_value = mock_response

        provider = OpenRouterProvider(
            api_key="sk-or-dummy",
            model="deepseek/deepseek-chat",
            openrouter_provider={"order": ["Chutes", "DeepInfra"], "allow_fallbacks": False},
        )
        res = await provider.generate([{"role": "user", "content": "hi"}])
        self.assertEqual(res["content"], "hello world")

        called_json = mock_post.call_args.kwargs.get("json", {})
        self.assertIn("provider", called_json)
        self.assertEqual(called_json["provider"]["order"], ["Chutes", "DeepInfra"])
        self.assertFalse(called_json["provider"]["allow_fallbacks"])

    @patch("httpx.AsyncClient.post")
    async def test_model_pool_per_model_provider_routing(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "pool response", "role": "assistant"}}]}
        mock_post.return_value = mock_response

        providers_map = {
            "deepseek/deepseek-chat": "Chutes,DeepInfra",
            "meta-llama/llama-3.3-70b-instruct": "Together",
        }

        pool = ModelPoolProvider(
            api_key="sk-or-dummy",
            models=["openrouter_router/deepseek/deepseek-chat"],
            openrouter_providers_map=providers_map,
        )

        res = await pool.generate([{"role": "user", "content": "hi"}])
        self.assertEqual(res["content"], "pool response")

        called_json = mock_post.call_args.kwargs.get("json", {})
        self.assertIn("provider", called_json)
        self.assertEqual(called_json["provider"]["order"], ["Chutes", "DeepInfra"])

    def test_env_overrides_parsing(self):
        config = {"llm": {}}
        with patch.dict(
            "os.environ",
            {
                "AAA_OPENROUTER_PROVIDER_ORDER": "Chutes,DeepInfra",
                "AAA_OPENROUTER_ALLOW_FALLBACKS": "true",
                "AAA_OPENROUTER_PROVIDERS_MAP": '{"deepseek/deepseek-chat": "Chutes"}',
            },
        ):
            updated = _apply_env_overrides(config)
            or_cfg = updated.get("llm", {}).get("openrouter_provider")
            or_map = updated.get("llm", {}).get("openrouter_providers_map")
            self.assertIsNotNone(or_cfg)
            self.assertEqual(or_cfg.get("order"), ["Chutes", "DeepInfra"])
            self.assertTrue(or_cfg.get("allow_fallbacks"))
            self.assertEqual(or_map, {"deepseek/deepseek-chat": "Chutes"})


if __name__ == "__main__":
    unittest.main()
