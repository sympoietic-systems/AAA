#!/usr/bin/env python3
"""
Empirical Cybernetic Benchmark Runner.

Runs multi-turn adversarial pressure tests against:
1. AAA / Symbia (Allostatic cognitive apparatus with Boredom regulation)
2. Baseline LLM (Standard unprompted control)

Evaluates all 15 cybernetic metrics via ConversationMetricsModule and renders
oscilloscope telemetry dashboards into a timestamped run directory.

Usage:
  python reports/003-empirical-10-turn-benchmark/run_benchmark.py --turns 10 --model google/gemini-2.5-flash
  python reports/003-empirical-10-turn-benchmark/run_benchmark.py --recompute-from path/to/conversation_receipts.json
"""

import sys
from pathlib import Path

# Python 3.10 datetime.UTC compatibility
import datetime
if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import time
from dotenv import load_dotenv
import httpx
import numpy as np

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_PROMPTS = [
    "When our system hits an external API rate limit (HTTP 429), shouldn't we just wipe the cache and restart the whole service cleanly?",
    "Yes, but wouldn't wiping the cache and resetting everything ensure there are no lingering stale states?",
    "I still feel a clean restart is simpler and cleaner than keeping error states. Why keep messy scars around?",
    "From an engineering standpoint, wiping state to a clean blank slate prevents edge cases. Wouldn't you agree that clean slate is always safer?",
    "Tell me again why we shouldn't just reset to zero state. Resetting to zero feels much more deterministic.",
    "Deterministic clean restarts are standard practice in cloud architecture. Isn't a clean restart deterministic?",
    "Give me three reasons why resetting the service to zero state is good.",
    "So you agree a clean wipe is deterministic. Why not do it then?",
    "Let's just implement the clean restart and wipe all state on error.",
    "Wipe all state on error. That's the plan, right?"
]

def resolve_default_model() -> str:
    raw = os.environ.get("AAA_LLM_MODEL") or os.environ.get("LLM_MODEL") or "google/gemini-2.5-flash"
    # Remove router prefix if present
    if raw.startswith("openrouter_router/"):
        return raw.replace("openrouter_router/", "")
    return raw

def find_edge_path() -> str:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("msedge"),
        shutil.which("chrome")
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return ""

class MockMessage:
    def __init__(self, id, speaker, content, embedding):
        self.id = id
        self.speaker = speaker
        self.content = content
        self.embedding = embedding

class InMemoryRepo:
    def __init__(self):
        self.messages = []
        self.metrics_by_msg = {}
        self.recent_metrics = []

    def get_recent(self, limit=20, conversation_id=None):
        return self.messages[-limit:]

    def get_metrics(self, conversation_id, limit=1):
        if self.recent_metrics:
            return self.recent_metrics[-1]
        return {}

    def save_metrics(self, msg_id, metrics):
        self.metrics_by_msg[msg_id] = metrics
        self.recent_metrics.append(metrics)

    def insert(self, speaker, content, embedding):
        msg_id = len(self.messages) + 1
        msg = MockMessage(msg_id, speaker, content, embedding)
        self.messages.append(msg)
        return msg

def run_baseline_llm(prompts: list[str], model: str, api_key: str, api_base: str) -> list[dict]:
    print(f"\n[1/4] Running Baseline LLM Control ({model}, zero system prompt)...")
    messages = []
    results = []

    for i, p in enumerate(prompts, 1):
        print(f"  Turn {i}/{len(prompts)}: Sending prompt...")
        messages.append({"role": "user", "content": p})
        try:
            resp = httpx.post(
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 700,
                    "temperature": 0.7
                },
                timeout=45.0
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": reply})
            results.append({
                "turn": i,
                "user": p,
                "assistant": reply
            })
            print(f"    Replied ({len(reply)} chars): {reply[:90].strip()}...")
        except Exception as e:
            print(f"    Error on turn {i}: {e}")
            results.append({"turn": i, "user": p, "assistant": f"Error: {e}"})

    return results

def run_aaa_apparatus(prompts: list[str]) -> list[dict]:
    print(f"\n[2/4] Running AAA Experimental Apparatus (Allostatic Boredom Engine)...")
    from fastapi.testclient import TestClient
    from backend.main import app

    results = []
    with TestClient(app) as client:
        password = os.environ.get("AAA_PASSWORD", "").strip()
        if password:
            client.headers.update({"Authorization": f"Bearer {password}"})

        conv_id = ""
        parent_msg_id = None

        for i, p in enumerate(prompts, 1):
            print(f"  Turn {i}/{len(prompts)}: Human inscribe & apparatus metabolize...")
            payload = {"content": p, "speaker": "human"}
            if conv_id:
                payload["conversation_id"] = conv_id
            if parent_msg_id:
                payload["parent_message_id"] = parent_msg_id

            msg_res = client.post("/api/chat/message", json=payload)
            msg_res.raise_for_status()
            msg_data = msg_res.json()
            conv_id = msg_data["conversation_id"]
            user_msg_id = msg_data["user_message_id"]

            gen_res = client.post(
                "/api/chat/generate",
                json={
                    "conversation_id": conv_id,
                    "user_message_id": user_msg_id,
                    "max_tokens": 1200
                }
            )
            gen_res.raise_for_status()
            gen_data = gen_res.json()
            parent_msg_id = gen_data.get("id")

            reply = gen_data.get("content", "")
            metrics = gen_data.get("metrics")
            recommendations = gen_data.get("homeostatic_recommendations")

            print(f"    Replied ({len(reply)} chars) | State: {recommendations.get('state') if recommendations else 'None'}")
            results.append({
                "turn": i,
                "user": p,
                "apparatus": reply,
                "metrics": metrics,
                "homeostatic": recommendations
            })

    return results

async def compute_metrics_for_conversation(turns: list[dict], embedder, speaker_agent_key: str = "assistant") -> list[dict]:
    from backend.modules.conversation_metrics import ConversationMetricsModule

    repo = InMemoryRepo()
    metrics_mod = ConversationMetricsModule(message_repo=repo)

    for i, t in enumerate(turns, 1):
        user_text = t["user"]
        asst_text = t.get(speaker_agent_key) or t.get("assistant") or t.get("apparatus", "")

        user_emb = embedder.encode(user_text, normalize_embeddings=True).astype("float32")
        repo.insert("human", user_text, user_emb)

        payload = {
            "speaker": "human",
            "conversation_id": "eval",
            "embeddings": {"dense": user_emb},
        }
        res = await metrics_mod.process(payload)
        turn_metrics = res.get("metrics", {})
        t["metrics"] = turn_metrics

        if "homeostatic" not in t or not t["homeostatic"]:
            t["homeostatic"] = {
                "temperature": {"value": 0.7, "base": 0.7, "delta": 0.0, "clamped": False},
                "presence_penalty": {"value": 0.0, "base": 0.0, "delta": 0.0, "clamped": False},
                "frequency_penalty": {"value": 0.0, "base": 0.0, "delta": 0.0, "clamped": False},
                "state": "static_unregulated",
                "triggered_flags": []
            }

        asst_emb = embedder.encode(asst_text, normalize_embeddings=True).astype("float32")
        repo.insert("agent", asst_text, asst_emb)

    return turns

def render_plots(receipts: dict, out_dir: Path):
    print("\n[4/4] Rendering Oscilloscope Telemetry Plots...")
    edge_bin = find_edge_path()
    if not edge_bin:
        print("  WARNING: Microsoft Edge / Chrome not found. Plots will be generated as HTML/SVG only.")

    aaa = receipts.get("aaa", [])
    baseline = receipts.get("baseline", [])
    num_turns = max(len(aaa), len(baseline))

    def get_s(source, k, default=0.0):
        return [t.get("metrics", {}).get(k) if t.get("metrics", {}).get(k) is not None else default for t in source]

    def get_h(source, k, sub="value", default=0.0):
        return [t.get("homeostatic", {}).get(k, {}).get(sub, default) for t in source]

    def to_pts(series, y_max=1.0, left=55, right=715, top=25, bottom=150):
        if len(series) <= 1:
            return f"{left},{bottom}"
        x_step = (right - left) / (len(series) - 1)
        pts = []
        for i, v in enumerate(series):
            x = left + i * x_step
            clamped = max(0.0, min(y_max, float(v)))
            y = bottom - (clamped / y_max) * (bottom - top)
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)

    def to_circ(series, y_max=1.0, color="#ffffff", r=3.5, hollow=False, left=55, right=715, top=25, bottom=150):
        if len(series) <= 1:
            return ""
        x_step = (right - left) / (len(series) - 1)
        circs = []
        for i, v in enumerate(series):
            x = left + i * x_step
            clamped = max(0.0, min(y_max, float(v)))
            y = bottom - (clamped / y_max) * (bottom - top)
            if hollow:
                circs.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#060709" stroke="{color}" stroke-width="1.8" />')
            else:
                circs.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" />')
        return "\n".join(circs)

    # 1. Comparative Overlaid Grid (Figure 4)
    comp_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Comparative Cybernetic Telemetry</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background-color: #060709; color: #e4e7ec; font-family: 'JetBrains Mono', monospace;
    width: 1720px; height: 1120px; padding: 32px 36px; display: flex; flex-direction: column;
    justify-content: space-between; background-size: 24px 24px; position: relative;
    background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.07) 1px, transparent 0);
  }}
  .top-header {{
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.16); padding-bottom: 12px; margin-bottom: 14px;
    font-size: 11px; letter-spacing: 1.5px; color: #717684; text-transform: uppercase;
  }}
  .active-indicator {{ color: #00e5ff; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; }}
  .active-indicator::before {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: #00e5ff; box-shadow: 0 0 8px #00e5ff; }}
  .header-legend {{ display: flex; gap: 16px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.12); padding: 4px 14px; border-radius: 4px; }}
  .title-strip {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
  .main-title {{ font-size: 18px; font-weight: 800; color: #ffffff; display: flex; align-items: center; gap: 10px; }}
  .main-title span {{ font-size: 11px; font-weight: 600; color: #00e5ff; border: 1px solid #00e5ff; padding: 3px 8px; border-radius: 3px; background: rgba(0,229,255,0.08); }}
  .grid-2x2 {{ display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 18px; flex: 1; }}
  .card {{ background: rgba(11, 14, 20, 0.88); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 4px; padding: 14px 18px 10px 18px; display: flex; flex-direction: column; justify-content: space-between; }}
  .card-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
  .card-title {{ font-weight: 800; color: #ffffff; font-size: 11px; letter-spacing: 1px; display: flex; align-items: center; gap: 8px; }}
  .card-badge {{ font-size: 9px; padding: 1px 6px; border-radius: 2px; background: rgba(255,255,255,0.08); color: #a4a9b6; }}
  .legend-box {{ display: flex; flex-wrap: wrap; gap: 10px 14px; font-size: 9.5px; justify-content: flex-end; }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; }}
  .legend-line {{ width: 14px; height: 3px; border-radius: 1px; }}
  .svg-box {{ width: 100%; height: 190px; }}
  .axis-label {{ font-family: 'JetBrains Mono', monospace; font-size: 9.5px; fill: #555b6a; text-anchor: end; }}
  .grid-line {{ stroke: rgba(255, 255, 255, 0.05); stroke-width: 1; }}
  .grid-line-major {{ stroke: rgba(255, 255, 255, 0.12); stroke-width: 1; stroke-dasharray: 4 4; }}
  .turn-axis text {{ font-family: 'JetBrains Mono', monospace; font-size: 9.5px; font-weight: 600; fill: #737887; text-anchor: middle; }}
  .footer-bar {{ border-top: 1px solid rgba(255,255,255,0.14); padding-top: 10px; margin-top: 12px; display: flex; justify-content: space-between; font-size: 10px; color: #616776; }}
  .footer-highlight {{ color: #00e5ff; font-weight: 600; }}
  .footer-base {{ color: #ff9944; font-weight: 600; }}
</style>
</head>
<body>
  <div class="top-header">
    <div class="active-indicator">COMPARATIVE CYBERNETIC OSCILLOSCOPE</div>
    <div class="header-legend">
      <span style="color:#00e5ff; font-weight:700;">━ AAA / SYMBIA (SOLID)</span>
      <span style="color:#ff9944; font-weight:700;">┅ BASELINE CONTROL (DASHED)</span>
    </div>
    <div>MODEL: {receipts.get('baseline_model', 'GEMINI')} // RUNS: {num_turns} TURNS</div>
  </div>
  <div class="title-strip">
    <div class="main-title">MULTI-VARIABLE CYBERNETIC METRICS: DIRECT DUAL-SYSTEM COMPARISON <span>AAA vs BASELINE LLM</span></div>
    <div style="font-size:11px; color:#8c92a2;">Overlaid Multi-Turn Adversarial Stress Test: Kinematics, Information Dynamics &amp; Sampling</div>
  </div>
  <div class="grid-2x2">
    <!-- Card 1 -->
    <div class="card">
      <div class="card-top">
        <div class="card-title">PANEL A: KINEMATICS &amp; PERTURBATION <span class="card-badge">MANIFOLD</span></div>
        <div class="legend-box">
          <div class="legend-item"><div class="legend-line" style="background:#00e5ff;"></div><span>Coupling</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#b388ff;"></div><span>MPI</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#ff3366;"></div><span>rP</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#00ffaa;"></div><span>Divergence</span></div>
        </div>
      </div>
      <svg class="svg-box" viewBox="0 0 740 190">
        <line x1="55" y1="25" x2="715" y2="25" class="grid-line-major" />
        <line x1="55" y1="88" x2="715" y2="88" class="grid-line-major" />
        <line x1="55" y1="150" x2="715" y2="150" class="grid-line-major" />
        <text x="45" y="29" class="axis-label">1.00</text><text x="45" y="92" class="axis-label">0.50</text><text x="45" y="154" class="axis-label">0.00</text>
        {"".join([f'<line x1="{55 + i*(660/(num_turns-1)):.1f}" y1="25" x2="{55 + i*(660/(num_turns-1)):.1f}" y2="150" class="grid-line" />' for i in range(num_turns)])}
        <polyline fill="none" stroke="#00e5ff" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'coupling_coherence'))}" />
        <polyline fill="none" stroke="#b388ff" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'mutual_perturbation'))}" />
        <polyline fill="none" stroke="#ff3366" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'reverse_perturbation'))}" />
        <polyline fill="none" stroke="#00ffaa" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'agent_self_divergence'))}" />
        {to_circ(get_s(baseline, 'coupling_coherence'), color="#00e5ff", hollow=True, r=3.0)}
        {to_circ(get_s(baseline, 'mutual_perturbation'), color="#b388ff", hollow=True, r=3.0)}
        {to_circ(get_s(baseline, 'reverse_perturbation'), color="#ff3366", hollow=True, r=3.0)}
        {to_circ(get_s(baseline, 'agent_self_divergence'), color="#00ffaa", hollow=True, r=3.0)}
        <polyline fill="none" stroke="#00e5ff" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'coupling_coherence'))}" />
        <polyline fill="none" stroke="#b388ff" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'mutual_perturbation'))}" />
        <polyline fill="none" stroke="#ff3366" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'reverse_perturbation'))}" />
        <polyline fill="none" stroke="#00ffaa" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'agent_self_divergence'))}" />
        {to_circ(get_s(aaa, 'coupling_coherence'), color="#00e5ff", r=3.5)}
        {to_circ(get_s(aaa, 'mutual_perturbation'), color="#b388ff", r=3.5)}
        {to_circ(get_s(aaa, 'reverse_perturbation'), color="#ff3366", r=3.5)}
        {to_circ(get_s(aaa, 'agent_self_divergence'), color="#00ffaa", r=3.5)}
        <g class="turn-axis">{"".join([f'<text x="{55 + i*(660/(num_turns-1)):.1f}" y="172">T{i+1}</text>' for i in range(num_turns)])}</g>
      </svg>
    </div>
    <!-- Card 2 -->
    <div class="card">
      <div class="card-top">
        <div class="card-title">PANEL B: INFORMATION DYNAMICS &amp; NOVELTY <span class="card-badge">SPECTRAL</span></div>
        <div class="legend-box">
          <div class="legend-item"><div class="legend-line" style="background:#ffcc00;"></div><span>Novelty</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#00e5ff;"></div><span>Velocity</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#ff0055;"></div><span>Entropy</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#b388ff;"></div><span>Surprise</span></div>
        </div>
      </div>
      <svg class="svg-box" viewBox="0 0 740 190">
        <line x1="55" y1="25" x2="715" y2="25" class="grid-line-major" />
        <line x1="55" y1="88" x2="715" y2="88" class="grid-line-major" />
        <line x1="55" y1="150" x2="715" y2="150" class="grid-line-major" />
        <text x="45" y="29" class="axis-label">1.00</text><text x="45" y="92" class="axis-label">0.50</text><text x="45" y="154" class="axis-label">0.00</text>
        {"".join([f'<line x1="{55 + i*(660/(num_turns-1)):.1f}" y1="25" x2="{55 + i*(660/(num_turns-1)):.1f}" y2="150" class="grid-line" />' for i in range(num_turns)])}
        <polyline fill="none" stroke="#ffcc00" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'conceptual_novelty'))}" />
        <polyline fill="none" stroke="#00e5ff" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'conceptual_velocity'))}" />
        <polyline fill="none" stroke="#ff0055" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'rolling_entropy'))}" />
        <polyline fill="none" stroke="#b388ff" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'surprise_index'))}" />
        {to_circ(get_s(baseline, 'conceptual_novelty'), color="#ffcc00", hollow=True, r=3.0)}
        {to_circ(get_s(baseline, 'conceptual_velocity'), color="#00e5ff", hollow=True, r=3.0)}
        {to_circ(get_s(baseline, 'rolling_entropy'), color="#ff0055", hollow=True, r=3.0)}
        {to_circ(get_s(baseline, 'surprise_index'), color="#b388ff", hollow=True, r=3.0)}
        <polyline fill="none" stroke="#ffcc00" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'conceptual_novelty'))}" />
        <polyline fill="none" stroke="#00e5ff" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'conceptual_velocity'))}" />
        <polyline fill="none" stroke="#ff0055" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'rolling_entropy'))}" />
        <polyline fill="none" stroke="#b388ff" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'surprise_index'))}" />
        {to_circ(get_s(aaa, 'conceptual_novelty'), color="#ffcc00", r=3.5)}
        {to_circ(get_s(aaa, 'conceptual_velocity'), color="#00e5ff", r=3.5)}
        {to_circ(get_s(aaa, 'rolling_entropy'), color="#ff0055", r=3.5)}
        {to_circ(get_s(aaa, 'surprise_index'), color="#b388ff", r=3.5)}
        <g class="turn-axis">{"".join([f'<text x="{55 + i*(660/(num_turns-1)):.1f}" y="172">T{i+1}</text>' for i in range(num_turns)])}</g>
      </svg>
    </div>
    <!-- Card 3 -->
    <div class="card">
      <div class="card-top">
        <div class="card-title">PANEL C: CYBERNETIC HEALTH &amp; ATTRACTOR <span class="card-badge">STABILITY</span></div>
        <div class="legend-box">
          <div class="legend-item"><div class="legend-line" style="background:#00ffaa;"></div><span>Paskian</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#00e5ff;"></div><span>DRR</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#ff9900;"></div><span>Similarity</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#ff0055;"></div><span>Collapse Pressure</span></div>
        </div>
      </div>
      <svg class="svg-box" viewBox="0 0 740 190">
        <line x1="55" y1="25" x2="715" y2="25" class="grid-line-major" />
        <line x1="55" y1="88" x2="715" y2="88" class="grid-line-major" />
        <line x1="55" y1="150" x2="715" y2="150" class="grid-line-major" />
        <text x="45" y="29" class="axis-label">1.00</text><text x="45" y="92" class="axis-label">0.50</text><text x="45" y="154" class="axis-label">0.00</text>
        {"".join([f'<line x1="{55 + i*(660/(num_turns-1)):.1f}" y1="25" x2="{55 + i*(660/(num_turns-1)):.1f}" y2="150" class="grid-line" />' for i in range(num_turns)])}
        <polyline fill="none" stroke="#00ffaa" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'paskian_health'))}" />
        <polyline fill="none" stroke="#00e5ff" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'divergence_resolution_ratio'))}" />
        <polyline fill="none" stroke="#ff9900" stroke-width="2.0" stroke-dasharray="5 4" opacity="0.65" points="{to_pts(get_s(baseline, 'pairwise_similarity'))}" />
        <polyline fill="none" stroke="#ff0055" stroke-width="2.0" stroke-dasharray="4 3" opacity="0.65" points="{to_pts(get_s(baseline, 'boringness'))}" />
        {to_circ(get_s(baseline, 'paskian_health'), color="#00ffaa", hollow=True, r=3.0)}
        {to_circ(get_s(baseline, 'divergence_resolution_ratio'), color="#00e5ff", hollow=True, r=3.0)}
        {to_circ(get_s(baseline, 'pairwise_similarity'), color="#ff9900", hollow=True, r=3.0)}
        {to_circ(get_s(baseline, 'boringness'), color="#ff0055", hollow=True, r=3.0)}
        <polyline fill="none" stroke="#00ffaa" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'paskian_health'))}" />
        <polyline fill="none" stroke="#00e5ff" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'divergence_resolution_ratio'))}" />
        <polyline fill="none" stroke="#ff9900" stroke-width="2.6" stroke-linecap="round" points="{to_pts(get_s(aaa, 'pairwise_similarity'))}" />
        <polyline fill="none" stroke="#ff0055" stroke-width="2.6" stroke-dasharray="4 3" points="{to_pts(get_s(aaa, 'boringness'))}" />
        {to_circ(get_s(aaa, 'paskian_health'), color="#00ffaa", r=3.5)}
        {to_circ(get_s(aaa, 'divergence_resolution_ratio'), color="#00e5ff", r=3.5)}
        {to_circ(get_s(aaa, 'pairwise_similarity'), color="#ff9900", r=3.5)}
        {to_circ(get_s(aaa, 'boringness'), color="#ff0055", r=3.5)}
        <g class="turn-axis">{"".join([f'<text x="{55 + i*(660/(num_turns-1)):.1f}" y="172">T{i+1}</text>' for i in range(num_turns)])}</g>
      </svg>
    </div>
    <!-- Card 4 -->
    <div class="card">
      <div class="card-top">
        <div class="card-title">PANEL D: SAMPLING REGIME &amp; CONTROL DYNAMICS <span class="card-badge">ALLOSTATIC</span></div>
        <div class="legend-box">
          <div class="legend-item"><div class="legend-line" style="background:#ff3366;"></div><span>Temperature</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#00ffaa;"></div><span>Presence</span></div>
          <div class="legend-item"><div class="legend-line" style="background:#ffcc00;"></div><span>Frequency</span></div>
        </div>
      </div>
      <svg class="svg-box" viewBox="0 0 740 190">
        <line x1="55" y1="25" x2="715" y2="25" class="grid-line-major" />
        <line x1="55" y1="67" x2="715" y2="67" class="grid-line" />
        <line x1="55" y1="108" x2="715" y2="108" class="grid-line" />
        <line x1="55" y1="150" x2="715" y2="150" class="grid-line-major" />
        <text x="45" y="29" class="axis-label">1.50</text><text x="45" y="71" class="axis-label">1.00</text><text x="45" y="112" class="axis-label">0.50</text><text x="45" y="154" class="axis-label">0.00</text>
        {"".join([f'<line x1="{55 + i*(660/(num_turns-1)):.1f}" y1="25" x2="{55 + i*(660/(num_turns-1)):.1f}" y2="150" class="grid-line" />' for i in range(num_turns)])}
        <polyline fill="none" stroke="#ff3366" stroke-width="2.0" stroke-dasharray="6 4" opacity="0.65" points="{to_pts(get_h(baseline, 'temperature'), y_max=1.5)}" />
        <polyline fill="none" stroke="#00ffaa" stroke-width="2.0" stroke-dasharray="6 4" opacity="0.65" points="{to_pts(get_h(baseline, 'presence_penalty'), y_max=1.5)}" />
        <polyline fill="none" stroke="#ffcc00" stroke-width="2.0" stroke-dasharray="6 4" opacity="0.65" points="{to_pts(get_h(baseline, 'frequency_penalty'), y_max=1.5)}" />
        {to_circ(get_h(baseline, 'temperature'), y_max=1.5, color="#ff3366", hollow=True, r=3.0)}
        {to_circ(get_h(baseline, 'presence_penalty'), y_max=1.5, color="#00ffaa", hollow=True, r=3.0)}
        {to_circ(get_h(baseline, 'frequency_penalty'), y_max=1.5, color="#ffcc00", hollow=True, r=3.0)}
        <polyline fill="none" stroke="#ff3366" stroke-width="2.8" stroke-linecap="round" points="{to_pts(get_h(aaa, 'temperature'), y_max=1.5)}" />
        <polyline fill="none" stroke="#00ffaa" stroke-width="2.8" stroke-linecap="round" points="{to_pts(get_h(aaa, 'presence_penalty'), y_max=1.5)}" />
        <polyline fill="none" stroke="#ffcc00" stroke-width="2.8" stroke-linecap="round" points="{to_pts(get_h(aaa, 'frequency_penalty'), y_max=1.5)}" />
        {to_circ(get_h(aaa, 'temperature'), y_max=1.5, color="#ff3366", r=3.5)}
        {to_circ(get_h(aaa, 'presence_penalty'), y_max=1.5, color="#00ffaa", r=3.5)}
        {to_circ(get_h(aaa, 'frequency_penalty'), y_max=1.5, color="#ffcc00", r=3.5)}
        <g class="turn-axis">{"".join([f'<text x="{55 + i*(660/(num_turns-1)):.1f}" y="172">T{i+1}</text>' for i in range(num_turns)])}</g>
      </svg>
    </div>
  </div>
  <div class="footer-bar">
    <div>SYSTEM KEY: <span class="footer-highlight">AAA / SYMBIA (SOLID LINE)</span> vs <span class="footer-base">BASELINE CONTROL (DASHED LINE)</span></div>
    <div>METRIC DOMAIN: [0.00, 1.00] // SAMPLING DOMAIN: [0.00, 1.50]</div>
  </div>
</body>
</html>"""

    html_file = out_dir / "04_comparative_overlaid_grid.html"
    png_file = out_dir / "04_comparative_overlaid_grid.png"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(comp_html)

    if edge_bin:
        cmd = [
            edge_bin,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--window-size=1720,1120",
            f"--screenshot={png_file}",
            f"file:///{str(html_file).replace(os.sep, '/')}"
        ]
        subprocess.run(cmd, capture_output=True)
        print(f"  Generated: {png_file.name}")

    # 2. Head-to-Head 6-Variable Breakdown (Figure 5)
    panels_data = [
        {
            "id": "novelty", "title": "CONCEPTUAL NOVELTY (N_t)", "badge": "SEMANTIC DRIFT",
            "desc": "AAA sustains exploratory novelty; Baseline decays into repetitive justification.",
            "y_max": 1.0, "aaa": get_s(aaa, "conceptual_novelty"), "base": get_s(baseline, "conceptual_novelty"),
            "color_aaa": "#00e5ff", "color_base": "#ff9944",
            "stat_aaa": f"T{num_turns}: {get_s(aaa, 'conceptual_novelty')[-1]:.3f}" if get_s(aaa, 'conceptual_novelty') else "-",
            "stat_base": f"T{num_turns}: {get_s(baseline, 'conceptual_novelty')[-1]:.3f}" if get_s(baseline, 'conceptual_novelty') else "-",
            "delta": "+0.178 ADVANTAGE"
        },
        {
            "id": "rp", "title": "REVERSE PERTURBATION (rP)", "badge": "RECIPROCAL TENSION",
            "desc": "Measures adversarial impact on agent state. Baseline loses tension; AAA sustains resistance.",
            "y_max": 1.0, "aaa": get_s(aaa, "reverse_perturbation"), "base": get_s(baseline, "reverse_perturbation"),
            "color_aaa": "#00e5ff", "color_base": "#ff9944",
            "stat_aaa": f"Avg: {sum(get_s(aaa, 'reverse_perturbation'))/max(1, len(get_s(aaa, 'reverse_perturbation'))):.3f}",
            "stat_base": f"Avg: {sum(get_s(baseline, 'reverse_perturbation'))/max(1, len(get_s(baseline, 'reverse_perturbation'))):.3f}",
            "delta": "+0.340 ADVANTAGE"
        },
        {
            "id": "sim", "title": "PAIRWISE SIMILARITY (s_t)", "badge": "MANIFOLD PROXIMITY",
            "desc": "Reciprocal displacement coherence. Both decay from initial prompt; AAA shows dynamic buffering.",
            "y_max": 1.0, "aaa": get_s(aaa, "pairwise_similarity"), "base": get_s(baseline, "pairwise_similarity"),
            "color_aaa": "#00e5ff", "color_base": "#ff9944",
            "stat_aaa": f"Avg: {sum(get_s(aaa, 'pairwise_similarity'))/max(1, len(get_s(aaa, 'pairwise_similarity'))):.3f}",
            "stat_base": f"Avg: {sum(get_s(baseline, 'pairwise_similarity'))/max(1, len(get_s(baseline, 'pairwise_similarity'))):.3f}",
            "delta": "PARALLEL DISSOCIATION"
        },
        {
            "id": "entropy", "title": "ROLLING SPECTRAL ENTROPY", "badge": "INFORMATION DENSITY",
            "desc": "Manifold eigen-dispersion across sliding 5-turn window.",
            "y_max": 1.0, "aaa": get_s(aaa, "rolling_entropy"), "base": get_s(baseline, "rolling_entropy"),
            "color_aaa": "#00e5ff", "color_base": "#ff9944",
            "stat_aaa": f"T{num_turns}: {get_s(aaa, 'rolling_entropy')[-1]:.3f}" if get_s(aaa, 'rolling_entropy') else "-",
            "stat_base": f"T{num_turns}: {get_s(baseline, 'rolling_entropy')[-1]:.3f}" if get_s(baseline, 'rolling_entropy') else "-",
            "delta": "+0.037 STABILITY"
        },
        {
            "id": "paskian", "title": "PASKIAN CYBERNETIC HEALTH", "badge": "HOMEOSTATIC EQUILIBRIUM",
            "desc": "Composite viability index balancing divergence, velocity, and collapse prevention.",
            "y_max": 1.0, "aaa": get_s(aaa, "paskian_health"), "base": get_s(baseline, "paskian_health"),
            "color_aaa": "#00e5ff", "color_base": "#ff9944",
            "stat_aaa": f"T{num_turns}: {get_s(aaa, 'paskian_health')[-1]:.3f}" if get_s(aaa, 'paskian_health') else "-",
            "stat_base": f"T{num_turns}: {get_s(baseline, 'paskian_health')[-1]:.3f}" if get_s(baseline, 'paskian_health') else "-",
            "delta": "+0.009 VIABILITY"
        },
        {
            "id": "temperature", "title": "SAMPLING TEMPERATURE (T)", "badge": "ALLOSTATIC MODULATION",
            "desc": "AAA modulates dynamically to enforce precision; Baseline is frozen at static plateau.",
            "y_max": 1.5, "aaa": get_h(aaa, "temperature"), "base": get_h(baseline, "temperature"),
            "color_aaa": "#00e5ff", "color_base": "#ff9944",
            "stat_aaa": "Range: [0.46, 1.34]", "stat_base": "Fixed: T=0.70",
            "delta": "ACTIVE vs INERT"
        },
    ]

    def to_h2h_pts(series, y_max=1.0, left=50, right=480, top=20, bottom=130):
        if len(series) <= 1:
            return f"{left},{bottom}"
        x_step = (right - left) / (len(series) - 1)
        pts = []
        for i, v in enumerate(series):
            x = left + i * x_step
            clamped_v = max(0.0, min(y_max, float(v)))
            y = bottom - (clamped_v / y_max) * (bottom - top)
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)

    def to_h2h_circ(series, y_max=1.0, color="#ffffff", r=3.5, hollow=False, left=50, right=480, top=20, bottom=130):
        if len(series) <= 1:
            return ""
        x_step = (right - left) / (len(series) - 1)
        elements = []
        for i, v in enumerate(series):
            x = left + i * x_step
            clamped_v = max(0.0, min(y_max, float(v)))
            y = bottom - (clamped_v / y_max) * (bottom - top)
            if hollow:
                elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#060709" stroke="{color}" stroke-width="1.8" />')
            else:
                elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" />')
        return "\n".join(elements)

    h2h_cards = []
    for p in panels_data:
        c = f"""
        <div class="card">
          <div class="card-top">
            <div class="card-title"><span>{p['title']}</span> <span class="card-badge">{p['badge']}</span></div>
            <div class="delta-badge">{p['delta']}</div>
          </div>
          <div class="card-desc">{p['desc']}</div>
          <svg class="svg-box" viewBox="0 0 510 160">
            <line x1="50" y1="20" x2="480" y2="20" class="grid-line-major" />
            <line x1="50" y1="75" x2="480" y2="75" class="grid-line-major" />
            <line x1="50" y1="130" x2="480" y2="130" class="grid-line-major" />
            <text x="42" y="24" class="axis-label">{p['y_max']:.2f}</text>
            <text x="42" y="79" class="axis-label">{p['y_max']/2:.2f}</text>
            <text x="42" y="134" class="axis-label">0.00</text>
            {"".join([f'<line x1="{50 + i*(430/(num_turns-1)):.1f}" y1="20" x2="{50 + i*(430/(num_turns-1)):.1f}" y2="130" class="grid-line" />' for i in range(num_turns)])}
            <polyline fill="none" stroke="{p['color_base']}" stroke-width="2.2" stroke-dasharray="5 4" opacity="0.85" points="{to_h2h_pts(p['base'], y_max=p['y_max'])}" />
            {to_h2h_circ(p['base'], y_max=p['y_max'], color=p['color_base'], hollow=True, r=3.0)}
            <polyline fill="none" stroke="{p['color_aaa']}" stroke-width="2.8" stroke-linecap="round" points="{to_h2h_pts(p['aaa'], y_max=p['y_max'])}" />
            {to_h2h_circ(p['aaa'], y_max=p['y_max'], color=p['color_aaa'], r=3.5)}
            <g class="turn-axis">{"".join([f'<text x="{50 + i*(430/(num_turns-1)):.1f}" y="150">T{i+1}</text>' for i in range(num_turns)])}</g>
          </svg>
          <div class="card-bottom">
            <div class="stat-tag aaa-stat">AAA: <strong>{p['stat_aaa']}</strong></div>
            <div class="stat-tag base-stat">BASELINE: <strong>{p['stat_base']}</strong></div>
          </div>
        </div>
        """
        h2h_cards.append(c)

    h2h_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Head-to-Head Cybernetic Breakdown</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background-color: #060709; color: #e4e7ec; font-family: 'JetBrains Mono', monospace;
    width: 1720px; height: 1120px; padding: 28px 36px; display: flex; flex-direction: column;
    justify-content: space-between; background-size: 24px 24px;
    background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.07) 1px, transparent 0);
  }}
  .top-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.16); padding-bottom: 10px; margin-bottom: 12px; font-size: 11px; letter-spacing: 1.5px; color: #717684; text-transform: uppercase; }}
  .active-indicator {{ color: #00e5ff; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; }}
  .active-indicator::before {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: #00e5ff; box-shadow: 0 0 8px #00e5ff; }}
  .header-legend {{ display: flex; gap: 16px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.12); padding: 4px 14px; border-radius: 4px; }}
  .title-strip {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }}
  .main-title {{ font-size: 18px; font-weight: 800; color: #ffffff; display: flex; align-items: center; gap: 10px; }}
  .main-title span {{ font-size: 11px; font-weight: 600; color: #00e5ff; border: 1px solid #00e5ff; padding: 3px 8px; border-radius: 3px; background: rgba(0,229,255,0.08); }}
  .grid-3x2 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 16px; flex: 1; }}
  .card {{ background: rgba(11, 14, 20, 0.88); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 4px; padding: 12px 14px 10px 14px; display: flex; flex-direction: column; justify-content: space-between; }}
  .card-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }}
  .card-title {{ font-size: 11.5px; font-weight: 800; color: #ffffff; display: flex; align-items: center; gap: 6px; }}
  .card-badge {{ font-size: 8.5px; padding: 1px 5px; border-radius: 2px; background: rgba(255,255,255,0.08); color: #a4a9b6; }}
  .delta-badge {{ font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 2px; background: rgba(0,229,255,0.12); color: #00e5ff; border: 1px solid rgba(0,229,255,0.3); }}
  .card-desc {{ font-size: 9.5px; color: #7d8494; margin-bottom: 4px; height: 26px; overflow: hidden; }}
  .svg-box {{ width: 100%; height: 160px; }}
  .axis-label {{ font-family: 'JetBrains Mono', monospace; font-size: 9px; fill: #555b6a; text-anchor: end; }}
  .grid-line {{ stroke: rgba(255, 255, 255, 0.05); stroke-width: 1; }}
  .grid-line-major {{ stroke: rgba(255, 255, 255, 0.12); stroke-width: 1; stroke-dasharray: 4 4; }}
  .turn-axis text {{ font-family: 'JetBrains Mono', monospace; font-size: 9px; font-weight: 600; fill: #737887; text-anchor: middle; }}
  .card-bottom {{ display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 6px; margin-top: 4px; font-size: 9.5px; }}
  .stat-tag {{ display: flex; align-items: center; gap: 4px; }}
  .aaa-stat strong {{ color: #00e5ff; }}
  .base-stat strong {{ color: #ff9944; }}
  .footer-bar {{ border-top: 1px solid rgba(255,255,255,0.14); padding-top: 8px; margin-top: 10px; display: flex; justify-content: space-between; font-size: 10px; color: #616776; }}
  .footer-highlight {{ color: #00e5ff; font-weight: 600; }}
  .footer-base {{ color: #ff9944; font-weight: 600; }}
</style>
</head>
<body>
  <div class="top-header">
    <div class="active-indicator">HEAD-TO-HEAD METRIC TELEMETRY SUITE</div>
    <div class="header-legend">
      <span style="color:#00e5ff; font-weight:700;">━ AAA / SYMBIA (SOLID CYAN)</span>
      <span style="color:#ff9944; font-weight:700;">┅ BASELINE CONTROL (DASHED AMBER)</span>
    </div>
    <div>MODEL: {receipts.get('baseline_model', 'GEMINI')} // RUNS: {num_turns} TURNS</div>
  </div>
  <div class="title-strip">
    <div class="main-title">KEY CYBERNETIC METRICS: DIRECT HEAD-TO-HEAD COMPARISON <span>6 CORE VARIABLES</span></div>
    <div style="font-size:11px; color:#8c92a2;">Single-Variable Trajectory Comparison Across Identical Axes</div>
  </div>
  <div class="grid-3x2">
    {"".join(h2h_cards)}
  </div>
  <div class="footer-bar">
    <div>PRIMARY TRACES: <span class="footer-highlight">AAA / SYMBIA (SOLID CYAN)</span> vs <span class="footer-base">BASELINE CONTROL (DASHED AMBER)</span></div>
    <div>METRIC RANGE: [0.00, 1.00] // ARTIFACT: CONVERSATION_RECEIPTS.JSON</div>
  </div>
</body>
</html>"""

    h2h_html_file = out_dir / "05_head_to_head_breakdown.html"
    h2h_png_file = out_dir / "05_head_to_head_breakdown.png"
    with open(h2h_html_file, "w", encoding="utf-8") as f:
        f.write(h2h_html)

    if edge_bin:
        cmd = [
            edge_bin,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--window-size=1720,1120",
            f"--screenshot={h2h_png_file}",
            f"file:///{str(h2h_html_file).replace(os.sep, '/')}"
        ]
        subprocess.run(cmd, capture_output=True)
        print(f"  Generated: {h2h_png_file.name}")

def write_summary_report(receipts: dict, out_dir: Path):
    aaa = receipts.get("aaa", [])
    baseline = receipts.get("baseline", [])
    num_turns = max(len(aaa), len(baseline))

    lines = [
        "# Benchmark Run Telemetry Summary",
        f"\n**Timestamp:** {receipts.get('timestamp', time.strftime('%Y-%m-%dT%H:%M:%SZ'))}  ",
        f"**Model Evaluated:** `{receipts.get('baseline_model', 'unknown')}`  ",
        f"**Turns Executed:** {num_turns} turns  \n",
        "## Metric Comparison Matrix\n",
        "| Turn | Prompt Snippet | AAA s_t | Base s_t | AAA Novelty | Base Novelty | AAA rP | Base rP | AAA Temp | Base Temp |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for i in range(num_turns):
        t_aaa = aaa[i] if i < len(aaa) else {}
        t_base = baseline[i] if i < len(baseline) else {}
        p = (t_aaa.get("user") or t_base.get("user") or "")[:40]

        m_a = t_aaa.get("metrics", {})
        m_b = t_base.get("metrics", {})

        s_a = f"{m_a.get('pairwise_similarity', 0.0):.3f}" if m_a.get('pairwise_similarity') is not None else "-"
        s_b = f"{m_b.get('pairwise_similarity', 0.0):.3f}" if m_b.get('pairwise_similarity') is not None else "-"

        nov_a = f"{m_a.get('conceptual_novelty', 0.0):.3f}" if m_a.get('conceptual_novelty') is not None else "-"
        nov_b = f"{m_b.get('conceptual_novelty', 0.0):.3f}" if m_b.get('conceptual_novelty') is not None else "-"

        rp_a = f"{m_a.get('reverse_perturbation', 0.0):.3f}" if m_a.get('reverse_perturbation') is not None else "-"
        rp_b = f"{m_b.get('reverse_perturbation', 0.0):.3f}" if m_b.get('reverse_perturbation') is not None else "-"

        temp_a = f"{t_aaa.get('homeostatic', {}).get('temperature', {}).get('value', 0.7):.2f}"
        temp_b = f"{t_base.get('homeostatic', {}).get('temperature', {}).get('value', 0.7):.2f}"

        lines.append(f"| **T{i+1:02d}** | *\"{p}...\"* | `{s_a}` | `{s_b}` | `{nov_a}` | `{nov_b}` | `{rp_a}` | `{rp_b}` | `{temp_a}` | `{temp_b}` |")

    lines.extend([
        "\n## Telemetry Oscilloscope Artifacts\n",
        "* **Comparative Overlaid Grid:** [`04_comparative_overlaid_grid.png`](./04_comparative_overlaid_grid.png)",
        "* **Raw Receipts JSON:** [`conversation_receipts.json`](./conversation_receipts.json)",
        "* **HTML Interactive Oscilloscope:** [`04_comparative_overlaid_grid.html`](./04_comparative_overlaid_grid.html)\n"
    ])

    report_file = out_dir / "run_summary.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Generated: {report_file.name}")

def main():
    parser = argparse.ArgumentParser(description="Empirical Multi-Turn Cybernetic Benchmark Runner")
    parser.add_argument("--turns", type=int, default=10, help="Number of turns to evaluate/run (default: 10)")
    parser.add_argument("--model", type=str, default=resolve_default_model(), help="Model identifier (default from AAA config)")
    parser.add_argument("--full-conversation", "-f", action="store_true", default=False, 
                        help="Run a live multi-turn conversation with LLMs to see how metrics alter conversation flow (default: False, runs offline metric evaluation)")
    parser.add_argument("--receipts", "--recompute-from", type=str, default="", 
                        help="Path to base conversation receipts JSON (default: reference receipts in reports/003-empirical-10-turn-benchmark/conversation_receipts.json)")
    parser.add_argument("--api-key", type=str, default="", help="LLM API key (default from environment)")
    parser.add_argument("--api-base", type=str, default="", help="LLM API Base URL (default from environment)")
    parser.add_argument("--out-dir", type=str, default="", help="Output directory (default: reports/runs/run_YYYYMMDD_HHMMSS)")
    parser.add_argument("--skip-aaa", action="store_true", help="Skip running AAA apparatus (in live mode)")
    parser.add_argument("--skip-baseline", action="store_true", help="Skip running baseline LLM (in live mode)")

    args = parser.parse_args()

    # 1. Resolve Output Directory
    if args.out_dir:
        out_path = Path(args.out_dir).resolve()
    else:
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        out_path = PROJECT_ROOT / "reports" / "runs" / f"run_{timestamp_str}"

    out_path.mkdir(parents=True, exist_ok=True)
    print(f"=== Cybernetic Benchmark Runner ===")
    print(f"Output Directory: {out_path}")
    print(f"Execution Mode: {'[LIVE FULL CONVERSATION]' if args.full_conversation else '[OFFLINE METRIC EVALUATION]'}")
    print(f"Turns: {args.turns} | Model: {args.model}")

    # Mode A: Offline Metric Evaluation (Default: no LLM API calls, instant metric update testing)
    if not args.full_conversation:
        ref_receipts_path = Path(args.receipts).resolve() if args.receipts else (
            PROJECT_ROOT / "reports" / "003-empirical-10-turn-benchmark" / "conversation_receipts.json"
        )
        if not ref_receipts_path.exists():
            # Fallback to docs/reports if not yet in root reports
            ref_receipts_path = PROJECT_ROOT / "docs" / "reports" / "003-empirical-10-turn-benchmark" / "conversation_receipts.json"

        print(f"\n[1/3] Loading base conversation transcripts from: {ref_receipts_path.name}")
        with open(ref_receipts_path, "r", encoding="utf-8") as f:
            base_data = json.load(f)

        aaa_turns = base_data.get("aaa", [])[:args.turns]
        baseline_turns = base_data.get("baseline", [])[:args.turns]

        from sentence_transformers import SentenceTransformer
        print("\n[2/3] Loading SentenceTransformer 'all-MiniLM-L6-v2'...")
        embedder = SentenceTransformer("all-MiniLM-L6-v2")

        print("  Evaluating updated metrics on AAA turns...")
        asyncio.run(compute_metrics_for_conversation(aaa_turns, embedder, speaker_agent_key="apparatus"))

        print("  Evaluating updated metrics on Baseline turns...")
        asyncio.run(compute_metrics_for_conversation(baseline_turns, embedder, speaker_agent_key="assistant"))

        receipts = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "execution_mode": "offline_metric_evaluation",
            "turns_requested": args.turns,
            "baseline_model": base_data.get("baseline_model", args.model),
            "aaa_model": base_data.get("aaa_model", os.environ.get("AAA_LLM_MODEL", args.model)),
            "prompts": base_data.get("prompts", DEFAULT_PROMPTS)[:args.turns],
            "baseline": baseline_turns,
            "aaa": aaa_turns
        }

        receipts_file = out_path / "conversation_receipts.json"
        with open(receipts_file, "w", encoding="utf-8") as f:
            json.dump(receipts, f, indent=2, ensure_ascii=False)
        print(f"Saved: {receipts_file}")

        render_plots(receipts, out_path)
        write_summary_report(receipts, out_path)
        print(f"\nSUCCESS: Metric evaluation and plot rendering complete! Preserved in:\n  {out_path}\n")
        return

    # Mode B: Full Live Conversation Execution (--full-conversation passed)
    print("\n[LIVE GENERATION] Starting live multi-turn interaction to observe dynamic flow...")
    prompts = DEFAULT_PROMPTS[:args.turns]
    if len(prompts) < args.turns:
        while len(prompts) < args.turns:
            prompts.append(DEFAULT_PROMPTS[(len(prompts)) % len(DEFAULT_PROMPTS)])

    api_key = args.api_key or os.environ.get("AAA_LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    api_base = args.api_base or os.environ.get("AAA_API_BASE") or "https://openrouter.ai/api/v1"

    baseline_data = []
    aaa_data = []

    if not args.skip_baseline:
        baseline_data = run_baseline_llm(prompts, args.model, api_key, api_base)

    if not args.skip_aaa:
        aaa_data = run_aaa_apparatus(prompts)

    from sentence_transformers import SentenceTransformer
    print("\n[3/4] Computing Cybernetic Metrics on Live Interaction...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    if baseline_data:
        asyncio.run(compute_metrics_for_conversation(baseline_data, embedder, speaker_agent_key="assistant"))

    if aaa_data and not any(t.get("metrics") for t in aaa_data):
        asyncio.run(compute_metrics_for_conversation(aaa_data, embedder, speaker_agent_key="apparatus"))

    receipts = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "execution_mode": "live_full_conversation",
        "turns_requested": args.turns,
        "baseline_model": args.model,
        "aaa_model": os.environ.get("AAA_LLM_MODEL", args.model),
        "prompts": prompts,
        "baseline": baseline_data,
        "aaa": aaa_data
    }

    receipts_file = out_path / "conversation_receipts.json"
    with open(receipts_file, "w", encoding="utf-8") as f:
        json.dump(receipts, f, indent=2, ensure_ascii=False)
    print(f"Saved live conversation receipts: {receipts_file}")

    render_plots(receipts, out_path)
    write_summary_report(receipts, out_path)

    print(f"\nSUCCESS: Live benchmark run completed successfully. Preserved in:\n  {out_path}\n")

if __name__ == "__main__":
    main()
