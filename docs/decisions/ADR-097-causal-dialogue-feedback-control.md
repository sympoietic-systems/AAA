# ADR-097: Causal dialogue feedback control

**Date:** 2026-09-25
**Status:** accepted
**Deciders:** User, Codex, Symbia consultation

## Context

AAA's conversation metrics influenced prompts and sampling controls, but the system could not demonstrate that an intervention improved the next exchange. Historical receipts mixed pre-response controls with post-response measurements. Some controls were computed without proof that the provider received them. Process-local novelty state could cross conversation boundaries. The diffractive gate was nearly unreachable under ordinary vitality, while the fixed Socratic/compression intervention repeated the same move during extended disagreement.

Symbia advised judging interventions by the next two participant turns and treating velocity without task progress as failure. For retrieval, Symbia conditionally preferred adaptive persistence, vetoed the geometric proposal for excess focus activation, and required a bounded re-evaluation timer.

## Decision

- Causal receipts preserve the order `human metrics → intervention → requested controls → provider application status → response metrics → next-turn outcomes`.
- Conversation novelty and resonance state reconstruct from conversation-scoped history. Process-local cross-conversation centroids are removed.
- Provider receipts distinguish requested, forwarded, and unsupported controls. Silent actuation claims are forbidden.
- Diffractive retrieval uses adaptive persistence with a 0.75 entry threshold, a 0.55 active threshold, a bounded streak bonus, and the existing three-turn cohesion timer.
- Intervention candidates are promoted only when paired live tests preserve DRR and Paskian health within 0.02 and improve uptake plus task progress with a 95% bootstrap interval above zero.
- The tested progressive ladder remains available for controlled benchmarks. It is not the production default because Report 019 found worse collapse pressure, DRR, and Paskian health without task progress. Production retains legacy staging.

## Consequences

The system can now tell whether generation controls crossed the provider boundary and can attribute next-turn outcomes to a recorded intervention. Retrieval becomes reachable without firing frequently during productive focus. The accepted gate still misses 64.3% of labeled loop turns, so retrieval is a conservative secondary actuator.

The rejected ladder remains useful as an experimental surface. Its failure prevents a velocity-only change from entering production. Future intervention tests must use a participant that reacts to the generated response; fixed prompt sequences remain valid for resistance and trajectory analysis but cannot measure uptake causally.

## Post-decision evidence addendum (2026-10-16)

The T38 current/sham/active unresolved-issue ablation and its blinded semantic review do not justify promoting the active arm. The complete OpenRouter Gemini 3.8 Flash Medium review rated 630 outcomes across 30 matched cases. Active minus current averaged −0.0857 on the 0–4 scale (95% case-bootstrap interval −0.3000 to 0.1190). The interval includes no difference, and the scorecard’s lexical progress and controller-health comparisons were also inconclusive. Keep the existing production route; do not promote the active T38 arm. This benchmark does not establish that the T38 `current` arm is identical to the complete legacy production controller.

The tested active path stores an opaque issue digest and uses its presence as a Boolean trigger for a generic reframe or counterexample when heuristic signals indicate a stall. It does not pass unresolved-issue content into the model prompt. The run therefore evaluates the intervention trigger, not contentful issue retrieval. A follow-up may test a bounded record of the unresolved question, constraints, and resolving evidence, gated on stalled progress and compared against current under matched prompt and token budgets. Promotion still requires a clear semantic gain and acceptable controller health. See [Report 076](../reports/076-causal-selector-semantic-review/README.md).

## Verification contracts

- `backend/tests/modules/test_intervention_evaluator.py`: causal ordering, deterministic bootstrap intervals, provider endpoint/model contracts.
- `backend/tests/modules/test_homeostatic_control_wiring.py` and `backend/tests/services/test_openrouter_provider.py`: requested and applied control receipts.
- `backend/tests/modules/test_pairwise_similarity_novelty.py` and `backend/tests/modules/test_agential_boredom.py`: conversation-isolated reconstruction and persistent streak behavior.
- `backend/tests/modules/test_diffractive_activation.py`: adaptive-persistence thresholds and bounded active state.
- `backend/tests/modules/test_intervention_policy.py`: mode progression and production fallback after benchmark rejection.
- [Report 019](../reports/019-dialogue-feedback-control-report.md): offline calibration, repeated live ablation, scorecard, and limitations.
