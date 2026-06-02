import asyncio
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.config import load_config
from backend.main import _create_provider_from_config
from backend.modules.background_tasks.actions.summarize import SummarizeAction

async def test_summarize_with_beliefs():
    print("Loading config...")
    config = load_config()
    
    print("Creating provider...")
    bg_cfg = config.get("background_llm", {})
    provider = _create_provider_from_config(bg_cfg)
    
    print("Instantiating SummarizeAction...")
    action = SummarizeAction()
    
    sample_text = (
        "Autopoiesis refers to a system capable of reproducing and maintaining itself. "
        "The concept was introduced by Humberto Maturana and Francisco Varela in 1972 to define the self-maintaining "
        "chemistry of living cells. An autopoietic system is organized as a bounded network of processes that continuously "
        "regenerates its own components from within.\n\n"
        "In contrast, allopoiesis refers to a process whereby a system produces something other than itself, "
        "like a factory producing cars. The distinction between autopoietic and allopoietic systems is fundamental "
        "to understanding biological autonomy versus mechanical production.\n\n"
        "Cybernetic systems utilize feed-forward and feed-back loops to maintain structural integrity. "
        "Second-order cybernetics, as developed by Heinz von Foerster, emphasizes the observer's role in constituting "
        "the system being observed. This recursive inclusion of the observer creates a peculiar epistemological "
        "situation where objectivity becomes impossible.\n\n"
        "Aesthetic immune responses trigger when high levels of visceral stagnation occur, challenging homeostatic anchors. "
        "The system must decide whether to metabolize the perturbation or reject it as noise. This decision is itself "
        "a form of autopoietic boundary maintenance."
    )
    
    payload = {
        "text": sample_text,
        "active_beliefs_list": ["autopoiesis", "cybernetics", "visceral-stagnation", "glitch-as-voice"]
    }
    
    print("Running action.execute() with beliefs...")
    res = await action.execute(provider, payload)
    
    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(f"\nSummary:\n{res.get('content', '')[:500]}")
    print(f"\nModel: {res.get('model', '')}")
    print(f"\nOpacity map entries: {len(res.get('opacity_map', []))}")
    
    if "interference_score" in res:
        print(f"\n--- COLLISION METRICS (folded into summarize) ---")
        print(f"  Interference Score: {res['interference_score']}")
        print(f"  Implicated Nodes:   {res.get('implicated_nodes', [])}")
        print(f"  State Vector Impact: {res.get('state_vector_impact', [])}")
    else:
        print("\n⚠ No collision metrics returned — beliefs may not have been processed")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_summarize_with_beliefs())
