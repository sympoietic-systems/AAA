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
  - Anthropic/DeepSeek-Anthropic is instructed via `"thinking": {"type": "disabled"}`.
  - Generic OpenAI-compatible endpoints support `thinking_budget=0` per-call opt-in.
- **Prompt-Level Guardrails:** Compact instructions demand raw JSON directly and forbid reasoning.
- **JSON Order Swap:** Swapped the schema keys to place `"scores"` first and `"justification"` second so that coordinates are generated immediately.
- **Robust Fallback Parsing:** Implemented a regex-based parser that handles incomplete JSON, cleans trailing commas, and extracts scores from truncated streams.
- **Token Budget:** `max_tokens` increased to 3000 to prevent truncation even with verbose justifications.
- **Fallback Value:** `generate_unified` receives a `fallback_value` so JSON parse failures return default scores instead of propagating exceptions.

### 2026-06-16 Update — Prompt Compaction & Token Budget Hardening

Despite API-level thinking suppression, truncated scorer responses (`'\n  "scores"'`) were observed. Root cause: `max_tokens=1000` was insufficient for verbose model output. Changes:
1. **Prompt shortened ~55%** — dimension descriptions compacted from verbose multi-line to single-line `01:Homeostatic(stability,dampening) 02:Amplifying(...)` format. System prompt hardened to "Output ONLY raw JSON, no markdown".
2. **`max_tokens` 1000 → 3000** — tripled response budget.
3. **`fallback_value` added** — `generate_unified` now gets `{"scores": [0.25]*16}` default, preventing exception propagation through `CompositeStructuralScorer`.
4. **Per-call `thinking_budget` opt-in** — generic OpenAI-compatible endpoints now support `thinking_budget=0` as a per-call parameter. For known providers (OpenRouter/Google/Anthropic), suppression already works via global `thinking: enabled: false` config. No change to normal chat calls.

### 2026-06-17 Update — Per-Request `thinking_override`

The two-speed brain was previously all-or-nothing at the provider level: global `thinking.enabled` applied to ALL calls. This forced a trade-off — either fast responses everywhere (no thinking) or expensive reasoning everywhere (thinking on). The research orchestrator needs thinking for planning (high-quality query decomposition) but fast responses for synthesis and reflection.

Changes:
1. **`OpenAIComposableProvider.generate()`** now pops `thinking_override` from `**params`. If present and truthy, it enables thinking mode for that specific request, overriding the provider-level `self._thinking` flag. If falsy, it disables thinking for that request. If absent (`None`), the provider-level default applies.
2. **Prompt YAML support** — `orchestrator_planner.yaml` declares `thinking: {enabled: true, effort: "high"}`. The orchestrator reads this and passes `thinking_override=True` + `reasoning_effort` to `generate_unified()`.
3. **Global default unchanged** — `config.yaml` keeps `thinking.enabled: false`. Only prompts that opt in via their YAML get thinking mode.

Usage: add `thinking: {enabled: true, effort: "high"}` to any prompt YAML to enable deep reasoning for that specific phase. Omit the block to keep the default (fast/no thinking).

---

## Consequences

### What becomes easier?
*   **Immediacy and Flow:** Active structural classification runs at maximum speed (<500ms), keeping the UI responsive.
*   **Reliability:** The scores are generated first and parsed via a fault-tolerant regex parser, guaranteeing that even if a model ignores instructions and prints reasoning, the coordinates are retrieved successfully.

### What becomes harder?
*   Tracking the qualitative reasons for real-time coordinate shifts requires separate reflection cycles (e.g. DreamDaemon passes) to log deep reasoning traces in `epistemic_traces`.
