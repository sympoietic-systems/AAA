import asyncio
import os
import sys

sys.path.insert(0, "D:/AAA")

from backend.modules.llm_client import LLMClientModule, OpenRouterProvider


async def test_llm():
    api_key = os.environ.get("AAA_LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        print("No API key found. Testing structure only.")
        provider = OpenRouterProvider(
            api_key="dummy",
            model="deepseek/deepseek-chat",
        )
        mod = LLMClientModule(provider)
        assert mod.name == "llm_client"
        assert mod.validate() is True
        assert provider.provider_name == "openrouter"

        payload = {"messages": [{"role": "user", "content": "hi"}], "temperature": 0.5}
        try:
            result = await mod.process(payload)
        except Exception as e:
            print(f"Expected error (no valid key): {type(e).__name__}")
        else:
            print(f"Response (unexpected success): {result.get('response', 'N/A')}")
        print("Structure tests passed!")
        return

    print(f"API key found. Running live test...")
    provider = OpenRouterProvider(
        api_key=api_key,
        model="deepseek/deepseek-chat",
    )
    mod = LLMClientModule(provider)

    valid = await provider.validate_connection()
    print(f"Connection valid: {valid}")

    if valid:
        payload = {"messages": [{"role": "user", "content": "Say hello in exactly one word."}]}
        result = await mod.process(payload)
        print(f"Response: {result.get('response', 'N/A')}")
        print("Live test passed!")


asyncio.run(test_llm())
