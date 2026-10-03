# ADR-103: Disable Metric-Triggered Thinking Escalation

**Date:** 2026-10-03
**Status:** accepted
**Deciders:** AAA maintainers

## Context

The chat homeostatic regulator treated collapse pressure above `0.65` as a reason to enable thinking, request high reasoning effort, and scale the recommended completion budget. Production observations include a Jev-flagged degraded reply that ended normally and separate provider-reported truncations. These observations do not establish that reasoning escalation caused either outcome, or that it improves recovery.

The metric describes conversation-level trajectory state. Applying that state to an individual generation request entangles intervention and observation, and can spend more of the completion budget on hidden reasoning. Explicit provider settings and per-call thinking overrides are separate controls used by other workflows and remain available.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Keep collapse-pressure-triggered thinking and token-budget escalation | Preserves the existing allostatic hypothesis | Production benefit is unverified; may increase latency, cost, or truncation without improving response quality |
| Disable automatic chat escalation; retain explicit provider/per-call thinking controls | Separates trajectory metrics from per-turn generation; keeps operator-controlled reasoning available | Removes an unvalidated automatic escape mechanism pending controlled evaluation |
| Disable thinking throughout the application | Simplifies generation behavior | Removes explicit reasoning capability from research and background workflows unnecessarily |

## Decision

Remove the chat homeostatic regulator's automatic `thinking_override`, reasoning-effort escalation, and completion-budget multiplier. Chat requests keep the configured `max_tokens` value. Collapse pressure continues to drive existing conversational interventions, temperature, and penalty recommendations. Provider-configured thinking and explicit per-call overrides remain supported.

Reassess the removed controller only through a matched ablation with provider receipts showing controls were applied. Compare Jev degraded-response rate and two-turn task progress or uptake; truncation must not increase, and latency must stay within an agreed bound. Track this in `TODO.md`.

## Consequences

- Boringness and collapse pressure no longer change the chat reasoning mode or increase its completion cap.
- Chat retains provider defaults; other workflows may continue to request thinking explicitly.
- This containment does not guarantee coherent replies or prevent provider-side truncation.
- Re-enabling automatic escalation requires evidence of improved response quality or task progress without a truncation or unacceptable latency regression.
