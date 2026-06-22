"""Test the Autonomous Research Engine through the live REST API.

Usage:
  uv run python scripts/test_research_api.py
"""
import urllib.request, json, time, os

PORT = os.environ.get("AAA_SERVER_PORT", "8499")
BASE = f"http://127.0.0.1:{PORT}"

def get(path):
    resp = urllib.request.urlopen(f"{BASE}{path}", timeout=10)
    return json.loads(resp.read())

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read())

# ── 1. Health ──
s = get("/api/health")
print(f"[OK] Health: {s['status']}")

# ── 2. Summary ──
s = get("/api/research/tasks/active/summary")
print(f"[OK] Summary: active={s['active_count']} queued={s['queued_count']} proposals={s['pending_proposals']}")

# ── 3. Dispatch (real LLM call!) ──
print(f"\n[Dispatching research task...]")
data = post("/api/research/dispatch", {
    "objective": "What are the key features and current limitations of WebGPU compute shaders in 2026?",
    "title": "WebGPU Compute 2026",
    "max_depth": 1, "max_breadth": 2, "budget_limit_usd": 0.50,
})
task_id = data["task_id"]
print(f"[OK] Task dispatched: {task_id[:8]}... status={data['status']}")

# ── 4. Poll for completion ──
print(f"[Polling for LLM completion...]")
for i in range(25):
    time.sleep(2)
    t = get(f"/api/research/tasks/{task_id}")
    s = t["status"]
    if s in ("completed", "failed"):
        print(f"\n  *** {s.upper()} after {i*2}s ***")
        print(f"  Branches:     {t.get('branches_created',0)}")
        print(f"  Assets:       {t.get('assets_harvested',0)}")
        print(f"  Lat.flights:  {t.get('lateral_flights',0)}")
        print(f"  Budget:       ${t.get('budget_spent_usd',0):.4f} / ${t.get('budget_limit_usd',0):.2f}")
        if t.get("result_summary"):
            print(f"  Summary:\n{t['result_summary'][:500]}")
        if s == "failed":
            print("  *** TASK FAILED — check server terminal ***")
        break
    if i % 5 == 0:
        print(f"  ... {s} ({i*2}s)")

# ── 5. List all ──
tasks = get("/api/research/tasks?limit=10")
print(f"\n[OK] All tasks ({len(tasks)}):")
for t in tasks[:5]:
    print(f"  [{t['status']:11}] {t['title'][:50]}  ${t.get('budget_spent_usd',0):.2f}/${t.get('budget_limit_usd',0):.2f}")

print(f"\nDone.")
