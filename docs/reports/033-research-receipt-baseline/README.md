# Report 033: Research Receipt Contracts and Offline Baseline

Date: 2026-10-05. Task: T62. Base commit: `9296611`.

T62 adds typed action/evidence/provider receipt contracts, additive storage, opt-in executor journaling and observable phase/public-provider timing. The architectural boundary and coverage limits are recorded in [ADR-105](../../decisions/ADR-105-research-action-journal.md). Runtime scheduling, provider recovery and source/span storage remain later tasks.

## Verification

The final focused run passed **73 tests**, covering the receipt repository, journal, provider observation, orchestrator state/phases/collaborators, task transactions and research API service. Tests use provider doubles and temporary databases. The focused strict mypy check passed for six implementation modules. Backend lint and changed-file formatting/diff checks passed.

Restart tests retain IDs, versions, dependencies, contract/policy hashes, resource fields and observations. Tests verify initialization policy persistence before execution, request persistence before provider work, late-output rejection, concurrent-start rejection, terminal checkpoint rollback, cancellation/failure recording, worker-thread execution, unknown telemetry and legacy compatibility. No receipt claims semantic support solely from a locator.

The sequential backend run stopped after 13 passes at `test_agential_boredom.py::test_continuous_collapse_pressure_coupling`: observed penalty delta `0.121 - 0.06` failed the expected minimum `0.15`. The same failure reproduced in an untouched worktree of base commit `9296611`. Global mypy also retains the existing missing `asyncio.Task` type argument in `keyed_lock.py`; the global format check identifies seven unchanged files. These failures remain visible and are outside T62.

An earlier full-suite run overlapped legacy tests using a shared test DB and was discarded. Verification then ran serially. No full-suite green result is claimed.

## Offline measurement

[receipts.json](receipts.json) is the canonical output of three isolated executions of the real receipt-enabled executor with a synthetic parser/provider fixture. Each sample records phase elapsed time, one public provider invocation, observed provider latency, and time from the first action start to the first fixture extraction result. Timings use the executing process clocks; they are measured values from this run.

The fixture supplies its own extracted text and performs no network retrieval, parsing benchmark or live LLM request. Model/provider identifiers identify the fixture. Usage and cost are unknown. These samples verify instrumentation; they cannot establish production speed, citation accuracy, full-document reading, budget enforcement or release non-inferiority. Reflection prose does not qualify as first useful evidence.

Reproduce from the repository root:

```powershell
uv run python -m scripts.benchmark_research_receipts --output .agents/scratch/receipt-baseline.json --repetitions 3
```

The harness creates and removes its own temporary test database. It accepts 1–20 repetitions. Historical receipts in this bundle remain unchanged; reruns use a separate output path.

## Remaining boundaries

Provider observations become durable with phase completion. A process crash inside a provider call leaves the action visibly running with unknown delivery; T63 owns durable in-flight attempts and bounded recovery. Pool-internal retries and provider calls outside the direct research-step wrapper are unobserved. Budgets/deadlines are recorded as request metadata without a claim of enforcement. T64 owns normalized source artifacts and claim support; T66 owns adaptive prerequisites and dependency-aware reruns.
