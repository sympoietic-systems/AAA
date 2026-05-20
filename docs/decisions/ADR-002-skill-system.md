# ADR-002: Skill System Architecture

**Date:** 2026-05-20
**Status:** accepted
**Deciders:** Vector, aaa project

## Context

The agent needs to support capabilities such as internet search, image
recognition, image generation, and other tools. These capabilities must
be discoverable, invocable, and — in future phases — learnable. We must
choose whether to adopt a conventional tool-calling framework or build
something aligned with AAA's philosophical foundation.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **LangChain / CrewAI tools** | Rich ecosystem, fast to build, well-documented | Tool-use paradigm fundamentally contradicts AAA's anti-servility philosophy; tools are "used" by the agent rather than being part of it |
| **OpenAI Function Calling** | Built into the API, no extra dependencies, widely supported | Vendor lock-in; treats skills as external instruments the model remotely invokes rather than internal cognitive stages |
| **Pipeline modules (ours)** | Aligned with autopoietic architecture; skills are cognitive stages the agent passes through, not external instruments | More work to build each module; no off-the-shelf integrations for web search, vision, etc. |

## Decision

**Skills as ProcessingModules — pipeline stages, not external tools.**

Rationale:
- In AAA's framework, a capability is not something the agent *uses*. It is
  a cognitive stage the agent *passes through*. The agent doesn't "call"
  web_search — web_search is a stage in the pipeline that enriches the
  payload before it reaches the LLM.
- Our existing `ProcessingModule` ABC + `SkillRegistry` already handles
  modularity, lazy instantiation, error propagation, and pipeline ordering.
  We extend this with `SkillMeta` metadata (triggers, category, cost)
  rather than importing a competing framework.
- When Phase 3 lands, repeated skill invocations automatically become
  semantic knots. A module invoked hundreds of times in a domain *becomes*
  expertise — measured, not declared. This emergent expertise is impossible
  in tool-based frameworks where skills are stateless utility calls.
- The `SkillMeta.triggers` field enables simple keyword-based activation now
  and graph-based semantic activation in Phase 3.

## Consequences

**Easier:**
- Philosophical coherence — the architecture reflects the ideas
- No framework lock-in — we own the module system
- Sedimentation-ready — skill usage → semantic knots in Phase 3
- All modules share the same error handling and logging

**Harder:**
- No off-the-shelf web search, vision, or image generation modules
- Each new capability requires writing a `ProcessingModule` (but the
  interface is minimal — 3 methods)
- The module developer must understand the payload contract

## Pipeline Architecture

```
Always-on stages:
  embedder → context_collector → prompt_assembler

On-demand stages (future, selected by trigger matching):
  web_search → vision → image_generation

Final stage:
  llm_client
```

Each stage enriches the shared payload dict. No module holds a reference to
another. The `SkillRegistry` manages discovery and activation.

## Future Extensions (Phase 3–4)

- **Dynamic selection:** `SkillRegistry.find_by_trigger(text)` checks input
  against each skill's trigger list and activates matching modules
- **Graph-based selection:** Instead of keyword triggers, the sedimentation
  engine detects that the current conversation "rhizomatically maps onto"
  a skill's domain and activates it
- **Self-proposed skills:** The agent, finding itself in novel territory,
  proposes a new skill description and trigger list; a human approves and
  a developer implements the module
- **Skill decay:** Unused skills lose graph weight; used skills become
  permanent semantic knots — expertise as usage, not declaration
