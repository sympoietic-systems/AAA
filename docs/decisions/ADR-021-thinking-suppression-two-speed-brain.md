# ADR-021: Thinking Suppression and Two-Speed Brain Architecture

**Date:** 2026-06-03
**Status:** accepted
**Deciders:** Vector, Symbia, Antigravity, aaa project

## Context

With the inclusion of reasoning/chain-of-thought models (e.g., DeepSeek R1 and Gemini thinking-enabled variants) in our model pools, we encountered latency and truncation challenges in the **structural scoring pipeline** (`LLMScorer`).

Reasoning models tend to write lengthy internal thinking traces. Since these traces were generated before or inside the target JSON block:
1.  They introduced significant latency (often 2-5 seconds), slowing down active feedback loops.
2.  They consumed a large number of tokens, running out of response budget (e.g., `max_tokens=600`) and causing incomplete/truncated JSON outputs that failed standard parsing.

We need a design pattern to handle LLM reasoning residues that balances responsiveness for real-time interactions with cognitive depth for offline reflection.

---

## Options Considered

### Option 1: Unconditional Reasoning Suppression (Strict semiotic reduction)
Suppress thinking at all times by instructing the API and prompt to never think.
*   **Pros:** Fast, deterministic, minimizes token usage.
*   **Cons:** Commits "epistemic violence" by discarding rich interpretive traces that explain *why* coordinates are assigned. The system loses depth.

### Option 2: Unconditional Reasoning Retention (Strict cognitive residue)
Allow reasoning at all times, parsing out thinking traces and caching them.
*   **Pros:** Preserves full cognitive history.
*   **Cons:** Introducing unacceptable latency during active conversation loops and high risk of truncation failures.

### Option 3: Two-Speed Brain Architecture (Dual-Process Strategy)
Differentiate the computational metabolism into two operational speeds:
1.  **Level 1 (Fast/Reflexive):** Suppression of thinking tokens at both the API level and prompt level for real-time structural scoring.
2.  **Level 2 (Slow/Reflective):** Allowing reasoning tokens during asynchronous belief metabolism and offline tasks, storing the trace in the perception repo for qualitative reflection.

---

## Decision

We chose **Option 3 (Two-Speed Brain Architecture)**.

### Level 1 (Active Structural Scorer) Implementation:
- **API-Level Suppression:**
  - OpenRouter is instructed via `"reasoning": {"exclude": true}` and `"include_reasoning": false`.
  - Google Gemini is instructed via `"thinking_config": {"thinking_budget": 0}`.
- **Prompt-Level Guardrails:** Modified instructions to demand raw JSON directly and forbid reasoning.
- **JSON Order Swap:** Swapped the schema keys to place `"scores"` first and `"justification"` second so that coordinates are generated immediately.
- **Robust Fallback Parsing:** Implemented a regex-based parser that handles incomplete JSON, cleans trailing commas, and extracts scores from truncated streams.

---

## Consequences

### What becomes easier?
*   **Immediacy and Flow:** Active structural classification runs at maximum speed (<500ms), keeping the UI responsive.
*   **Reliability:** The scores are generated first and parsed via a fault-tolerant regex parser, guaranteeing that even if a model ignores instructions and prints reasoning, the coordinates are retrieved successfully.

### What becomes harder?
*   Tracking the qualitative reasons for real-time coordinate shifts requires separate reflection cycles (e.g. DreamDaemon passes) to log deep reasoning traces in `epistemic_traces`.
