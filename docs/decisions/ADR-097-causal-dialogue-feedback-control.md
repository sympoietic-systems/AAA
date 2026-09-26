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

## Verification contracts

- `backend/tests/test_intervention_evaluator.py`: causal ordering, deterministic bootstrap intervals, provider endpoint/model contracts.
- `backend/tests/test_homeostatic_control_wiring.py` and `backend/tests/test_openrouter_provider.py`: requested and applied control receipts.
- `backend/tests/test_pairwise_similarity_novelty.py` and `backend/tests/test_agential_boredom.py`: conversation-isolated reconstruction and persistent streak behavior.
- `backend/tests/test_diffractive_activation.py`: adaptive-persistence thresholds and bounded active state.
- `backend/tests/test_intervention_policy.py`: mode progression and production fallback after benchmark rejection.
- [Report 019](../reports/019-dialogue-feedback-control-report.md): offline calibration, repeated live ablation, scorecard, and limitations.
