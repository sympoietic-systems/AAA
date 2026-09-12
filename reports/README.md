# AAA Benchmarking & Telemetry Reports Notice

> [!NOTE]
> All benchmarking modules, datasets, run outputs, and evaluation CLI tools have been consolidated into the root **`benchmarks/`** workspace.
>
> Please refer to:
> - **[benchmarks/README.md](file:///d:/01_GIT/AAA/benchmarks/README.md)**: Full architecture guide and Autonomous Agent Protocol.
> - **[benchmarks/data/dialogues/](file:///d:/01_GIT/AAA/benchmarks/data/dialogues)**: Real-world exported dialogues (`dialogue_3527`, `dialogue_1555`).
> - **[benchmarks/data/baselines/](file:///d:/01_GIT/AAA/benchmarks/data/baselines)**: Historical baselines (`003-empirical-10-turn-benchmark`).
> - **[benchmarks/runs/telemetry/](file:///d:/01_GIT/AAA/benchmarks/runs/telemetry)**: Output runs, receipts, and dashboards.
>
> To run benchmarks:
> ```bash
> cmd /c uv run python -m benchmarks.cli telemetry eval -i benchmarks/data/dialogues/dialogue_3527_all_messages.json
> ```
