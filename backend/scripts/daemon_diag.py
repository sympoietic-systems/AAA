"""Diagnostic: check daemon-related DB state for "runs but creates nothing" issue.

Usage:
    uv run backend/scripts/daemon_diag.py
"""

import json, os, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()
os.environ.setdefault("AAA_RUN_MIGRATIONS", "true")

from backend.config import load_config
from backend.storage.database import get_db_path, init_db
config = load_config()
db_path = str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))
init_db(db_path).close()

import sqlite3
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

cfg = config.get("daemon", {})
print("══ Daemon Config ══")
print(f"  check_interval     = {cfg.get('check_interval', '?')}s")
print(f"  idle_threshold     = {cfg.get('idle_threshold', '?')}s ({cfg.get('idle_threshold', 1800)//60}min)")
print(f"  min_dream_interval = {cfg.get('min_dream_interval', '?')}s ({cfg.get('min_dream_interval', 3600)//60}min)")
print(f"  max_daily_dreams   = {cfg.get('max_daily_dreams', '?')}")
print(f"  short_window_max   = {cfg.get('short_window_max', '?')}")
print()

print("══ Dreams ══")
count = conn.execute("SELECT COUNT(*) as c FROM dream_log").fetchone()["c"]
latest = conn.execute("SELECT MAX(timestamp) as t FROM dream_log").fetchone()["t"]
print(f"  Total dreams logged: {count}")
print(f"  Latest dream: {latest or 'never'}")
d24h = conn.execute("SELECT COUNT(*) as c FROM dream_log WHERE timestamp >= datetime('now', '-24 hours')").fetchone()["c"]
d8h = conn.execute("SELECT COUNT(*) as c FROM dream_log WHERE timestamp >= datetime('now', '-8 hours')").fetchone()["c"]
print(f"  Last 24h: {d24h} / {cfg.get('max_daily_dreams', '?')}")
print(f"  Last 8h:  {d8h} / {cfg.get('short_window_max', '?')}")
print(f"  Budget exhausted (24h): {'YES' if d24h >= 30 else 'no'}")
print()

print("══ Conversations ══")
rows = conn.execute("""
    SELECT c.id, c.title,
           COUNT(cl.id) as msg_count,
           c.last_consolidated_at,
           c.requires_consolidation
    FROM conversations c
    LEFT JOIN conversation_log cl ON c.id = cl.conversation_id
    GROUP BY c.id
    ORDER BY msg_count DESC
    LIMIT 10
""").fetchall()
for r in rows:
    cid = r["id"][:12] if r["id"] else "?"
    title = (r["title"] or "?")[:30]
    msg = r["msg_count"] or 0
    lc = str(r["last_consolidated_at"] or "never")[:19]
    req = r["requires_consolidation"]
    first = "CAN consolidate" if msg >= 12 else f"need {12-msg} more msgs"
    print(f"  [{cid}] {title}: {msg} msgs | last_consol: {lc} | reconsol: {req} | {first}")
print()

print("══ Checkpoints ══")
cp_count = conn.execute("SELECT COUNT(*) as c FROM consolidation_checkpoints").fetchone()["c"]
cp_latest = conn.execute("SELECT MAX(id) as m FROM consolidation_checkpoints").fetchone()["m"]
print(f"  Total checkpoints: {cp_count}")
print(f"  Latest checkpoint ID: {cp_latest}")
print()

print("══ Memory Nodes ══")
mn_count = conn.execute("SELECT COUNT(*) as c FROM memory_nodes").fetchone()["c"]
mn_src = conn.execute("SELECT source_type, COUNT(*) as c FROM memory_nodes GROUP BY source_type").fetchall()
print(f"  Total nodes: {mn_count}")
for s in mn_src:
    print(f"    {s['source_type']}: {s['c']}")
print()

print("══ Beliefs ══")
rows = conn.execute("SELECT lifecycle_stage, COUNT(*) as c FROM belief_nodes GROUP BY lifecycle_stage").fetchall()
if rows:
    for r in rows:
        print(f"  {r['lifecycle_stage']}: {r['c']}")
else:
    print("  NO BELIEFS AT ALL")
print()

print("══ Message Metabolism ══")
meta = conn.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN metabolized = 1 THEN 1 ELSE 0 END) as done,
        SUM(CASE WHEN metabolized IS NULL OR metabolized = 0 THEN 1 ELSE 0 END) as pending
    FROM conversation_log WHERE speaker = 'human'
""").fetchone()
print(f"  Human messages: {meta['total']} total | {meta['done']} metabolized | {meta['pending']} pending")
print()

print("══ Skills ══")
sk = conn.execute("SELECT COUNT(*) as c FROM skills").fetchone()["c"]
sk_cryst = conn.execute("SELECT COUNT(*) as c FROM skills WHERE lifecycle_stage = 'crystallized'").fetchone()["c"]
print(f"  Total: {sk} | Crystallized: {sk_cryst}")
print()

print("══ Research Sedimentation ══")
tasks = conn.execute("SELECT id, status FROM research_tasks WHERE status = 'completed' LIMIT 20").fetchall()
for t in tasks:
    q = json.loads(t.get("orchestrator_state", "{}") or "{}").get("sedimentation_queue", [])
    nodes = conn.execute("SELECT COUNT(*) as c FROM memory_nodes WHERE source_type = 'research' AND source_id = ?", (t["id"],)).fetchone()["c"]
    print(f"  [{t['id'][:12]}] queue: {len(q)} | nodes: {nodes}")
print()

conn.close()
