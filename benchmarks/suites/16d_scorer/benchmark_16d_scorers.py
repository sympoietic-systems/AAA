"""Benchmark suite comparing 16D Structural Scoring methods on realistic AAA corpus.

Compares:
1. LexiconScorer (Keyword density + non-linear exponential saturation)
2. TopologyScorer (Markdown structure, entropy, and link heuristics)
3. LLMScorer (Generative LLM classifier, if enabled)
4. JevStructuralScorer (TypeSafe Jev System One Score primitives with power & confidence)
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.bootstrap.providers import _init_providers
from backend.config import load_config
from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.structural_engine import (
    CYBERNETIC_DIMENSIONS,
    JevStructuralScorer,
    LexiconScorer,
    TopologyScorer,
    LLMScorer,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark_16d")

# Realistic AAA Corpus across 3 distinct agential categories
TEST_CORPUS = [
    # ── Category A: Agential Beliefs ─────────────────────────────────────
    {
        "id": "belief_autopoiesis",
        "category": "Belief",
        "title": "Autopoietic Closure",
        "text": (
            "An agentic cognition maintains continuous operational closure: its identity is "
            "recursively produced through circular networks of metabolic interactions. When the "
            "boundary conditions are perturbed, the system dampens noise to preserve homeostatic equilibrium."
        ),
    },
    {
        "id": "belief_tipping_point",
        "category": "Belief",
        "title": "Bifurcation Threshold",
        "text": (
            "Attractor collapse occurs abruptly across critical non-linear thresholds. Runaway positive feedback "
            "amplifies latent divergence, triggering sudden catastrophic phase transitions where existing basins dissolve."
        ),
    },
    {
        "id": "belief_rhizome",
        "category": "Belief",
        "title": "Rhizomatic Deterritorialization",
        "text": (
            "Decentralized knowledge meshes operate without central hierarchy. Multi-directional lines of flight "
            "cross semi-permeable membranes, migrating across smooth conceptual spaces via nomadic lateral links."
        ),
    },
    # ── Category B: Long-Term Memories & Research Nodes ──────────────────
    {
        "id": "memory_vsm_recursion",
        "category": "Memory",
        "title": "Beer's Viable System Model Architecture",
        "text": """# Viable System Model & Recursive Cybernetic Architecture

## 1. Regulatory Variety Attenuation
- System 1 (Operations): Embedded functional organs and executors.
- System 2 (Coordination): Dampens oscillation between operational units.
- System 3 (Control): Resource allocation, requisite variety filtering, and internal audit.

## 2. Temporal Foresight & Symbiosis
```yaml
feedback_lag: 200ms
variety_attenuation_ratio: 0.85
co_evolution_coupling: enabled
```

> Ashby's Law dictates that internal regulatory variety must match or exceed external environmental complexity.
See [[cybernetics/ashby]] and [[cybernetics/beer_vsm]].
""",
    },
    {
        "id": "memory_somatic_substrate",
        "category": "Memory",
        "title": "Embodied Substrate & Temporal Hysteresis",
        "text": (
            "Cognition cannot be detached from its physical hardware substrate and silicon constraints. "
            "Temporal latency in sensory transmission introduces unavoidable hysteresis loops, grounding "
            "virtual abstractions directly in raw thermal, energetic, and bandwidth limitations."
        ),
    },
    # ── Category C: Conversational Turns / User Messages ─────────────────
    {
        "id": "turn_dialogue_consensus",
        "category": "Message",
        "title": "Paskian Conversational Alignment",
        "text": (
            "Can we pause and negotiate our shared definitions? I want to establish explicit consensus on what "
            "our conversation is aiming to co-orient around before we proceed with the implementation."
        ),
    },
    {
        "id": "turn_mesh_query",
        "category": "Message",
        "title": "Distributed Mesh Query",
        "text": (
            "How do peer-to-peer decentralized nodes handle Byzantine consensus without a central coordinator? "
            "Show me the gossip protocol routing table."
        ),
    },
]


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


async def run_benchmark():
    config = load_config()
    output_dir = Path(ROOT_DIR) / "backend" / "benchmarks" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize Scorers
    lex_scorer = LexiconScorer()
    topo_scorer = TopologyScorer()

    ts_cfg = config.get("typesafe", {})
    ts_client = TypeSafeDecisionClient.from_config(ts_cfg) if ts_cfg.get("enabled", True) else None
    jev_scorer = JevStructuralScorer(client=ts_client)

    llm_provider, structural_provider, _ = _init_providers(config)
    llm_scorer = LLMScorer(provider=structural_provider or llm_provider)

    logger.info("Scorers initialized:")
    logger.info(" - LexiconScorer: Ready")
    logger.info(" - TopologyScorer: Ready")
    logger.info(" - JevStructuralScorer: Ready (Configured=%s, Model=%s)", jev_scorer.is_available, getattr(ts_client, "model", None))
    logger.info(" - LLMScorer: Ready (Provider=%s)", getattr(structural_provider or llm_provider, "provider_name", "None"))

    results = []

    for item in TEST_CORPUS:
        text = item["text"]
        item_id = item["id"]
        logger.info("Evaluating [%s] %s (%d chars)...", item["category"], item["title"], len(text))

        # 1. Lexicon
        t0 = time.perf_counter()
        s_lex = lex_scorer.score(text)
        dt_lex = (time.perf_counter() - t0) * 1000.0

        # 2. Topology
        t0 = time.perf_counter()
        s_topo = topo_scorer.score(text)
        dt_topo = (time.perf_counter() - t0) * 1000.0

        # 3. LLM
        s_llm = np.full(16, 0.25, dtype=np.float32)
        dt_llm = 0.0
        if llm_scorer.provider:
            t0 = time.perf_counter()
            try:
                s_llm = await asyncio.wait_for(llm_scorer.score_async(text), timeout=10.0)
            except Exception as e:
                logger.warning("LLMScorer failed for %s: %s", item_id, e)
            dt_llm = (time.perf_counter() - t0) * 1000.0

        # 4. Jev
        s_jev = np.full(16, 0.25, dtype=np.float32)
        c_jev = np.full(16, 0.50, dtype=np.float32)
        dt_jev = 0.0
        if jev_scorer.is_available:
            t0 = time.perf_counter()
            try:
                s_jev, c_jev = await jev_scorer.score_with_confidence_async(text)
            except Exception as e:
                logger.warning("JevStructuralScorer failed for %s: %s", item_id, e)
            dt_jev = (time.perf_counter() - t0) * 1000.0

        item_result = {
            "id": item["id"],
            "category": item["category"],
            "title": item["title"],
            "text": text,
            "timings_ms": {
                "lexicon": round(dt_lex, 2),
                "topology": round(dt_topo, 2),
                "llm": round(dt_llm, 2),
                "jev": round(dt_jev, 2),
            },
            "scores": {
                "lexicon": [round(float(v), 4) for v in s_lex],
                "topology": [round(float(v), 4) for v in s_topo],
                "llm": [round(float(v), 4) for v in s_llm],
                "jev_power": [round(float(v), 4) for v in s_jev],
                "jev_confidence": [round(float(v), 4) for v in c_jev],
            },
            "similarities": {
                "jev_vs_lexicon": round(cosine_sim(s_jev, s_lex), 4),
                "jev_vs_llm": round(cosine_sim(s_jev, s_llm), 4),
                "lexicon_vs_llm": round(cosine_sim(s_lex, s_llm), 4),
            },
        }
        results.append(item_result)

    benchmark_data = {
        "dimensions": [
            {"index": i, "slug": slug, "title": title, "focus": focus}
            for i, (slug, title, focus) in enumerate(CYBERNETIC_DIMENSIONS)
        ],
        "corpus_results": results,
    }

    out_file = output_dir / "benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    logger.info("Benchmark complete. Data saved to: %s", out_file)
    return out_file


if __name__ == "__main__":
    asyncio.run(run_benchmark())
