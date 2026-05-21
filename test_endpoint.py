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

            try:
                response = await client.post(url, json=test["payload"])

                print(f"Status: {response.status_code}")

                print(f"\nResponse:")
                try:
                    data = response.json()
                    print(f"  action:    {data.get('action')}")
                    print(f"  model:     {data.get('model_used')}")
                    print(f"  error:     {data.get('error')}")
                    print(f"\n  result:")
                    result = data.get("result", "")
                    # Print first 300 chars of result
                    if len(result) > 300:
                        print(f"  {result[:300]}...")
                    else:
                        print(f"  {result}")
                except Exception:
                    print(f"  {response.text}")

            except httpx.TimeoutException:
                print("  Request timed out (180s)")
            except httpx.RequestError as e:
                print(f"  Request error: {e}")

            # Small delay between tests
            await asyncio.sleep(1)


asyncio.run(test_background_endpoint())
