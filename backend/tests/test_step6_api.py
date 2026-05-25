import sys

sys.path.insert(0, "D:/AAA")

from fastapi.testclient import TestClient
from backend.main import app


with TestClient(app) as client:
    import os
    password = os.environ.get("AAA_PASSWORD", "").strip()
    if password:
        client.headers.update({"Authorization": f"Bearer {password}"})

    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    print(f"Health: status={data['status']}, modules={list(data['modules'].keys())}")
    assert data["status"] == "ok"

    response = client.get("/api/history?limit=5")
    assert response.status_code == 200
    data = response.json()
    print(f"History: count={data['count']}")

    response = client.get("/api/errors?limit=5")
    assert response.status_code == 200
    data = response.json()
    print(f"Errors: {len(data)} entries")

    response = client.post("/api/chat", json={"content": "Hello", "speaker": "human"})
    print(f"Chat status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()['content'][:100]}")
    else:
        print(f"Error: {response.json().get('detail', 'unknown')[:200]}")

print("API tests completed!")
