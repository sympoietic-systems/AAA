# Beliefs v2 baseline and creation-path inventory

Date: 2026-10-08. Scope: `BELIEF_SPEC.md::T1`, local verification of the existing explicit-admission implementation.

Starting HEAD: `1fb0756e7a21dd8f7b818f8a532ec01718b029a3`. At the start, `docs/systems/SKILL_SYSTEM.md` was the only unrelated modified file. During verification, unrelated edits appeared in `backend/api/routes/errors.py`, `backend/api/schemas.py`, and `backend/core/logging_config.py`. These edits were preserved and are outside this task. The commands below ran in the shared working tree, rather than an immutable isolated checkout; they do not certify concurrent changes or a release build.

## Local verification

| Command | Observed result |
| --- | --- |
| `uv run ruff check backend/` | Passed |
| `uv run ruff format --check backend/` | Passed; 457 files already formatted |
| `uv run mypy` | Passed; 84 source files |
| `uv run pytest -x -q` with external cache/basetemp and `faulthandler_timeout=60` | 735 passed, one dependency deprecation warning; 554.16 seconds |
| `npm run typecheck` in `frontend/` | Passed |
| `npm run lint` in `frontend/` | Exit 0; 164 legacy errors, 10 legacy warnings, zero regressions |
| `npm run test` in `frontend/` | 24 files, 136 tests passed |
| `npm run build` in `frontend/` | Passed |

Python verification used `PYTHONIOENCODING=utf-8`, `PYTHONDONTWRITEBYTECODE=1`, `C:/Users/user/AppData/Local/Temp/aaa-belief-v2-pytest-cache`, and `C:/Users/user/AppData/Local/Temp/aaa-belief-v2-pytest-run`. This completed the previously unfinished full-suite run described in ADR-115. It establishes a passing local run, without proving production admission behavior or evaluator quality.

GET-only production identity checks returned HTTP 200 for `/api/health`, and HTTP 404 for `/version` and `/openapi.json`. Server revision, applied migrations, and effective configuration remain unknown. No production writes, migrations, or deployment were performed.

## Creation paths

The inventory searched production Python call sites of `create_proposal` and `create_belief`, excluding tests and migration/seed definitions. Bootstrap scripts were inspected separately. Semantic intake, derived skill projections, and lifecycle bookkeeping have different authority requirements.

| Path | Current entry point | Current behavior | v2 ownership |
| --- | --- | --- | --- |
| Explicit chat | `services/background_tasks.py::run_background_belief_nucleate` | Source-bound `admit_candidate`; exact-repeat receipt handling | T6 |
| Explicit dream | `metabolisation/dream_executor.py` | Same admission service | T6 |
| Passive message metabolism, including dream/research callers | `modules/belief_engine.py::_nucleate_proto_belief` | Direct proposal from structural novelty and concept density; no admission receipt | T7 |
| Conversation patterns | `modules/belief/perception_handlers.py` | Direct proposal, generic cross-conversation trace | T7 |
| Scar-fold fallback | `services/annotations.py::_process_scar_monologue_belief_writeback` | When no belief exists, directly creates a crystallized belief with zero vector, mass 0.5 and confidence 0.5 | T7; unresolved B1 |
| Document perception | `modules/belief/perception_handlers.py` | Direct proposal with generic emergent-concept statement; source passage absent | T8 |
| Shared note | `modules/belief/perception_handlers.py` | Direct proposal; trace uses chat-turn identity rather than note identity | T8 |
| Web perception | `modules/belief/perception_handlers.py` | Direct proposal after density check | T8 |
| Applied skill bridge | `modules/skills/skill_workshop.py` | Projects applied skill into crystallized bridge belief | T3 authority contract; later persistence/workshop tasks |
| Proposal merge into skill | `services/belief_proposal.py::_resolve_target_belief` | Creates bridge when skill target has no bridge | T3 authority contract; later workshop tasks |
| Manual authored belief | `services/belief_mutation.py` | Explicit mutation boundary | Preserve attributed manual authority |
| Human proposal adoption | `services/belief_proposal.py` | Explicit adoption boundary | T11 |
| Bootstrap beliefs/bridges | `scripts/initialize_agent.py` | Administrative provisioning | Distinguish provisioning from semantic intake |
| Collapse into rejected proposal | `modules/belief_engine.py::_accrete_belief`, `metabolisation/mass_decay.py` | Lifecycle bookkeeping; not a new semantic encounter | T16 history-retention review |

`modules/commitment_store.py` manages proto-commitments, a separate subsystem; its records are not belief proposals.

The scar-fold path also records generic impact 0.15 while reinforcement changes mass by 0.05. Generic historical impact therefore cannot be presumed to measure either mass or confidence. Skill bridges require derived-skill provenance and an explicit authority contract; bridge creation cannot stand in for reviewed semantic adoption.

## Next implementation contract

T2 owns two observed defects: the API labels generic impact as `delta_confidence`, and wall-clock atrophy repeatedly charges elapsed time from an unchanged reinforcement timestamp. It must add nullable measured deltas, preserve legacy-client compatibility, and persist an atomic elapsed-time checkpoint. Tests must cover same-clock retry, restart, reinforcement, concurrent workers, transaction failure, legacy event reads, and clipped actual deltas. Turn-decay floor behavior remains independently verified. Wall-clock decay remains disabled by default.

No mass reset, historical semantic reclassification, or bulk merge follows from this baseline. Passing tests do not establish that advisory assessments reliably distinguish new insight from repetition; independently reviewed evaluation remains required by T4/T15.

See [implementation specification](../../systems/BELIEF_SPEC.md) and [architecture plan](../../architecture/BELIEFS_V2_PLAN.md).
