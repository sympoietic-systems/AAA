import asyncio
import json
import httpx


async def test_background_endpoint():
    url = "http://127.0.0.1:8000/api/background"

    tests = [
        {
            "name": "generate_title",
            "payload": {
                "action": "generate_title",
                "text": "Hello, I want to discuss quantum physics and the nature of consciousness",
            },
        },
        {
            "name": "summarize",
            "payload": {
                "action": "summarize",
                "text": "The conversation explored the intersection of quantum mechanics and consciousness, discussing how observation collapses wave functions and whether consciousness itself might be a quantum phenomenon.",
            },
        },
        {
            "name": "consolidate",
            "payload": {
                "action": "consolidate",
                "context": {
                    "messages": [
                        {"speaker": "human", "content": "What is consciousness?"},
                        {"speaker": "apparatus", "content": "The hard problem remains unresolved. Qualia cannot be reduced to physical processes alone."},
                    ]
                },
            },
        },
    ]

    async with httpx.AsyncClient(timeout=180.0) as client:
        for test in tests:
            print(f"\n{'=' * 60}")
            print(f"Testing: {test['name']}")
            print(f"{'=' * 60}")

            retries = 3
            for attempt in range(retries):
                try:
                    response = await client.post(url, json=test["payload"])

                    print(f"Status: {response.status_code}")

                    if response.status_code == 502:
                        print("  Server restarting (uvicorn reload), retrying...")
                        await asyncio.sleep(5)
                        continue

                    data = response.json()
                    print(f"  action:    {data.get('action')}")
                    print(f"  model:     {data.get('model_used')}")
                    print(f"  error:     {data.get('error')}")
                    print(f"\n  result:")
                    result = data.get("result", "")
                    if len(result) > 300:
                        print(f"  {result[:300]}...")
                    else:
                        print(f"  {result}")
                    break

                except httpx.TimeoutException:
                    print("  Request timed out (180s)")
                    break
                except httpx.RequestError as e:
                    print(f"  Request error: {e}")
                    if attempt < retries - 1:
                        print("  Retrying...")
                        await asyncio.sleep(5)
                    else:
                        print("  Max retries reached")

            await asyncio.sleep(2)


asyncio.run(test_background_endpoint())
