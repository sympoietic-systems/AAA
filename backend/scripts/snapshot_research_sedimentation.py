"""One-off snapshot: crystallize memory tissue from completed research tasks.

Reconstructs the sedimentation packets that the live pipeline would have pushed
during each phase (reflect→tension, synthesize→concept/belief_seed,
consolidate→pattern) and processes them through the ResearchCrystallization
background action to produce memory nodes.

Usage:
    uv run backend/scripts/snapshot_research_sedimentation.py [--dry-run] [--limit N]

Options:
    --dry-run    Compute and print packets but don't crystallize
    --limit N    Only process N tasks (default: all completed)
    --task ID    Process a single task by ID
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Threshold reconstructors — mirror the exact logic from the live pipeline
# ═══════════════════════════════════════════════════════════════════════

TENSION_WORDS = ["conflict", "contradict", "disagree", "oppose", "tension", "clash", "versus", "vs", "difference"]


def _compute_contradiction_density(all_findings: list) -> float:
    if not all_findings:
        return 0.0
    matches = 0
    for finding in all_findings:
        text = finding.lower() if isinstance(finding, str) else str(finding).lower()
        if any(w in text for w in TENSION_WORDS):
            matches += 1
    return matches / len(all_findings)


def _compute_glitch_metrics(steps: list, step_result_repo) -> tuple[float, int, int]:
    glitches_detected = 0
    glitches_addressed = 0
    for step in steps:
        if step.get("step_type") != "searching":
            continue
        results = step_result_repo.get_by_step(step["id"]) if step_result_repo else []
        if not results or all(not r.get("source_url") for r in results):
            glitches_detected += 1
        else:
            glitches_detected += 1
            glitches_addressed += 1
    fidelity = glitches_addressed / glitches_detected if glitches_detected > 0 else 1.0
    return fidelity, glitches_detected, glitches_addressed


def _compute_stability_delta(task_id: str, result_summary: str, steps: list) -> float:
    try:
        from backend.modules.embedder import generate_embedding

        current_emb = generate_embedding(result_summary[:2000])
        prior_synth_steps = [
            st for st in steps
            if st.get("step_type") == "synthesize" and st.get("status") == "completed"
        ]
        if len(prior_synth_steps) < 2:
            return 0.0
        prior = prior_synth_steps[-2]
        prior_data = _parse_step_data(prior)
        prior_report = prior_data.get("report_markdown", "")
        if not prior_report:
            return 0.0
        prior_emb = generate_embedding(prior_report[:2000])
        import numpy as np

        cos_sim = float(
            np.dot(current_emb, prior_emb)
            / (np.linalg.norm(current_emb) * np.linalg.norm(prior_emb) + 1e-10)
        )
        return 1.0 - cos_sim
    except Exception as e:
        logger.debug("stability_delta skipped for %s: %s", task_id[:8], e)
        return 0.0


def _extract_confidence(result_summary: str) -> float:
    match = re.search(r"confidence:\s*(\d+(?:\.\d+)?)\s*%?", result_summary, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        return val / 100.0 if val <= 1.0 else val  # already a ratio, or 0-100%
    return 0.0


def _parse_step_data(step: dict) -> dict:
    try:
        raw = step.get("step_data") or "{}"
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}


def _now_iso() -> str:
    from backend.utils.research_logger import now_utc_str
    return now_utc_str()


# ═══════════════════════════════════════════════════════════════════════
# YAML output parser — extracts nodes from ResearchCrystallization output
# ═══════════════════════════════════════════════════════════════════════

def _parse_crystallization_output(content: str) -> list[dict]:
    """Parse YAML output from ResearchCrystallizeAction into memory node dicts.
    Reuses the existing battle-tested sedimentation parser (4-tier fallback).
    """
    if not content or not content.strip():
        return []
    from backend.metabolisation.sedimentation import parse_sedimentation_yaml
    nodes, _tier = parse_sedimentation_yaml(content)
    return nodes


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

async def main() -> None:
    parser = argparse.ArgumentParser(description="Snapshot research sedimentation")
    parser.add_argument("--dry-run", action="store_true", help="Compute packets but don't crystallize")
    parser.add_argument("--limit", type=int, default=0, help="Max tasks to process (0 = all)")
    parser.add_argument("--task", type=str, default="", help="Process a single task by ID")
    args = parser.parse_args()

    from backend.config import load_config
    from backend.storage.database import get_db_path, init_db

    os.environ.setdefault("AAA_RUN_MIGRATIONS", "true")  # ensure columns exist

    config = load_config()
    db_path = config.get("database", {}).get("path", "data/aaa.db")
    full_db_path = get_db_path(db_path)
    init_conn = init_db(str(full_db_path))
    init_conn.close()

    db_path_str = str(full_db_path)

    from backend.storage.repository import (
        ResearchTaskRepository,
        ResearchStepRepository,
        ResearchStepResultRepository,
        MemoryNodeRepository,
        ConsolidationCheckpointRepository,
    )

    task_repo = ResearchTaskRepository(db_path_str)
    step_repo = ResearchStepRepository(db_path_str)
    step_result_repo = ResearchStepResultRepository(db_path_str)
    memory_node_repo = MemoryNodeRepository(db_path_str)
    checkpoint_repo = ConsolidationCheckpointRepository(db_path_str)

    # ── Fetch tasks ──
    if args.task:
        task = task_repo.get(args.task)
        tasks = [task] if task else []
        if not tasks:
            print(f"Task not found: {args.task}")
            return
    else:
        tasks = task_repo.list_all(status="completed", limit=args.limit or 500)

    if not tasks:
        print("No completed research tasks found.")
        return

    print(f"Tasks loaded: {len(tasks)}")

    # ═══════════════════════════════════════════════════════════════
    # Phase 1: Reconstruct packets and push to orchestrator_state
    # ═══════════════════════════════════════════════════════════════

    packets_pushed = 0
    already_done = 0
    no_state = 0
    task_packets: dict[str, list[dict]] = {}  # task_id → reconstructed packets

    for task in tasks:
        task_id = task["id"]
        result_summary = task.get("result_summary", "")
        conversation_id = task.get("conversation_id") or f"research_{task_id}"

        existing = memory_node_repo.get_by_source("research", task_id)
        if existing:
            already_done += 1
            continue

        state_raw = task.get("orchestrator_state")
        if not state_raw:
            no_state += 1
            continue

        try:
            state = json.loads(state_raw) if isinstance(state_raw, str) else state_raw
        except Exception:
            no_state += 1
            continue

        for key in ("all_findings", "search_results_cache", "parsed_sources_cache", "digest_results_cache"):
            if key not in state:
                state[key] = []
        for key in ("last_reflection", "digest_signals"):
            if key not in state:
                state[key] = {}
        if "sedimentation_queue" not in state:
            state["sedimentation_queue"] = []

        steps = step_repo.get_by_task(task_id)
        all_findings = state.get("all_findings", [])
        reconstructed: list[dict] = []

        # ── REFLECT → tension ──
        density = _compute_contradiction_density(all_findings)
        glitch_fidelity, _, _ = _compute_glitch_metrics(steps, step_result_repo)

        if density > 0.3 or glitch_fidelity < 0.7:
            critique_ctx = json.dumps({
                "phase": "reflect",
                "contradiction_density": density,
                "glitch_fidelity": glitch_fidelity,
            }, ensure_ascii=False)
            reconstructed.append({
                "phase": "reflection",
                "trigger_thresholds": {"contradiction_density": density, "glitch_fidelity": glitch_fidelity},
                "raw_context": critique_ctx[:8000],
                "proposed_node_type": "tension",
                "confidence": max(density, 1.0 - glitch_fidelity),
                "pushed_at": _now_iso(),
            })

        # ── SYNTHESIZE → concept + belief_seed ──
        if result_summary:
            stability_delta = _compute_stability_delta(task_id, result_summary, steps)
            if stability_delta > 0.2:
                reconstructed.append({
                    "phase": "synthesize",
                    "trigger_thresholds": {"stability_delta": stability_delta},
                    "raw_context": result_summary[:8000],
                    "proposed_node_type": "concept",
                    "confidence": min(stability_delta * 2.0, 1.0),
                    "pushed_at": _now_iso(),
                })

            conf = _extract_confidence(result_summary)
            if conf > 0.8:
                reconstructed.append({
                    "phase": "synthesize",
                    "trigger_thresholds": {"confidence": conf},
                    "raw_context": result_summary[:8000],
                    "proposed_node_type": "belief_seed",
                    "confidence": conf,
                    "pushed_at": _now_iso(),
                })

            # Always crystallize the final synthesis as at least one concept node.
            # Snapshot mode: even if individual phase thresholds weren't met,
            # the completed research result is valuable memory tissue.
            if not any(p["proposed_node_type"] == "concept" for p in reconstructed):
                reconstructed.append({
                    "phase": "completed",
                    "trigger_thresholds": {"snapshot": True},
                    "raw_context": result_summary[:8000],
                    "proposed_node_type": "concept",
                    "confidence": 0.6,
                    "pushed_at": _now_iso(),
                })

        # ── CONSOLIDATE → pattern ──
        for step in steps:
            if step.get("step_type") != "reflect" or step.get("status") != "completed":
                continue
            step_data = _parse_step_data(step)
            llm_resp = step_data.get("llm_response", {})
            json_data = llm_resp.get("json_data", {})
            if isinstance(json_data, str):
                try:
                    json_data = json.loads(json_data)
                except Exception:
                    json_data = {}
            if not isinstance(json_data, dict):
                continue

            completeness = json_data.get("completeness_score", 0.0)
            key_insights = json_data.get("key_insights", [])

            if completeness > 0.7 and key_insights:
                reconstructed.append({
                    "phase": "consolidate",
                    "trigger_thresholds": {"completeness_score": completeness},
                    "raw_context": json.dumps(key_insights, ensure_ascii=False)[:8000],
                    "proposed_node_type": "pattern",
                    "confidence": completeness,
                    "pushed_at": _now_iso(),
                })
                break  # one pattern packet per task is enough

        if reconstructed:
            task_packets[task_id] = reconstructed
            packets_pushed += len(reconstructed)

            # Persist to orchestrator_state so the live rake can also find them
            state["sedimentation_queue"] = reconstructed
            task_repo.update(task_id, orchestrator_state=json.dumps(state, default=str, ensure_ascii=False))

    print(f"  Already has memory nodes: {already_done}")
    print(f"  No orchestrator_state:   {no_state}")
    print(f"  Packets reconstructed:   {packets_pushed}")

    if args.dry_run:
        for tid, packets in task_packets.items():
            print(f"\n  [{tid[:12]}...]")
            for p in packets:
                print(f"    {p['phase']:>12s} -> {p['proposed_node_type']:<14s} conf={p['confidence']:.2f}")
        print("\n--dry-run: packets computed but not crystallized.")
        return

    if not task_packets:
        print("Nothing to crystallize.")
        return

    # ═══════════════════════════════════════════════════════════════
    # Phase 2: Initialize LLM and process through ResearchCrystallization
    # ═══════════════════════════════════════════════════════════════

    print("\nInitializing LLM and background engine...")
    from backend.bootstrap.providers import _init_providers
    from backend.bootstrap.background import _init_background_engine

    llm_provider, structural_provider, vision_provider = _init_providers(config)
    bg_engine, bg_provider = _init_background_engine(config, llm_provider, vision_provider)

    total_nodes = 0
    tasks_processed = 0

    for task_id, packets in task_packets.items():
        task = task_repo.get(task_id)
        if not task:
            continue
        conversation_id = task.get("conversation_id") or f"research_{task_id}"

        # Ensure a synthetic conversation exists for the FK constraint
        try:
            import sqlite3 as _sqlite3
            db_conn = _sqlite3.connect(db_path_str)
            db_conn.execute("PRAGMA foreign_keys=ON")
            db_conn.execute(
                "INSERT OR IGNORE INTO conversations (id, title, agent_id) VALUES (?, ?, ?)",
                (conversation_id, f"Research Snapshot: {task.get('objective', '')[:100]}", "symbia"),
            )
            db_conn.commit()
            db_conn.close()
        except Exception as e:
            logger.warning("Conversation create failed for %s: %s", conversation_id, e)

        # Get or create consolidation checkpoint
        try:
            latest_cp = checkpoint_repo.get_latest(conversation_id)
            if latest_cp:
                checkpoint_id = latest_cp["id"]
            else:
                checkpoint_id = checkpoint_repo.save(
                    conversation_id=conversation_id,
                    message_count=0,
                    summary=f"Research snapshot: {task.get('objective', '')[:200]}",
                    model="research_crystallize",
                )
        except Exception as e:
            logger.warning("Checkpoint create failed for %s: %s", task_id[:8], e)
            checkpoint_id = -1

        task_nodes = 0
        for packet in packets:
            try:
                print(f"  [{task_id[:8]}] {packet['phase']:>12s} -> {packet['proposed_node_type']:<14s} ...", end=" ", flush=True)

                result = await bg_engine.run("research_crystallize", {
                    "text": packet.get("raw_context", ""),
                    "phase": packet.get("phase", "unknown"),
                    "node_type": packet.get("proposed_node_type", "concept"),
                    "conversation_id": conversation_id,
                    "source_type": "research",
                    "source_id": task_id,
                })

                content = result.get("content", "")
                if not content:
                    print("(empty)")
                    continue

                nodes = _parse_crystallization_output(content)
                if not nodes:
                    print("(no nodes parsed)")
                    continue

                # Attach source metadata
                for n in nodes:
                    n["source_type"] = "research"
                    n["source_id"] = task_id

                memory_node_repo.save_nodes(conversation_id, checkpoint_id, nodes)
                task_nodes += len(nodes)
                node_types = set(n.get("type", "?") for n in nodes)
                print(f"{len(nodes)} nodes ({', '.join(node_types)})")

            except Exception as e:
                print(f"FAILED: {e}")
                logger.warning("Crystallization failed for task %s packet: %s", task_id[:8], e)

        if task_nodes > 0:
            total_nodes += task_nodes
            tasks_processed += 1

            # Clear queue from orchestrator_state
            state_raw = task.get("orchestrator_state")
            if state_raw:
                try:
                    state = json.loads(state_raw) if isinstance(state_raw, str) else state_raw
                    state["sedimentation_queue"] = []
                    task_repo.update(task_id, orchestrator_state=json.dumps(state, default=str, ensure_ascii=False))
                except Exception:
                    pass

        print(f"  -- {task_id[:8]}: {task_nodes} nodes total\n")

    print(f"\nDone.")
    print(f"  Tasks with new nodes: {tasks_processed}")
    print(f"  Total nodes created:  {total_nodes}")


if __name__ == "__main__":
    asyncio.run(main())
