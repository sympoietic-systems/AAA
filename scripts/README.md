# AAA Scripts Directory

This directory contains repository-level runners, orchestration helpers, database utilities, and telemetry benchmarks.

---

## 1. Operational & Service Lifecycle

These scripts control the development and production lifecycle of AAA's backend and frontend services.

| Script | Platform | Description |
| :--- | :--- | :--- |
| [`setup.sh`](setup.sh) / [`setup.bat`](setup.bat) | Bash / Batch | Bootstraps the complete environment: verifies Python/uv/Node.js, installs dependencies, initializes databases, and installs headless browsers. |
| [`run_all.sh`](run_all.sh) / [`run_all.bat`](run_all.bat) | Bash / Batch | Starts both the FastAPI backend and Vite frontend development servers concurrently. |
| [`run_backend.sh`](run_backend.sh) / [`run_backend.bat`](run_backend.bat) | Bash / Batch | Starts the FastAPI backend with automated database migrations enabled on port `8499`. |
| [`run_frontend.sh`](run_frontend.sh) / [`run_frontend.bat`](run_frontend.bat) | Bash / Batch | Starts the Vite frontend (`dev` with HMR or `preview` bundle) on port `5174`. |
| [`run_mcp.sh`](run_mcp.sh) / [`run_mcp.bat`](run_mcp.bat) | Bash / Batch | Runs the AAA Model Context Protocol (MCP) server over STDIO. |
| [`pm2.sh`](pm2.sh) | Bash | Process supervisor helper for PM2 production daemon mode via [`ecosystem.config.cjs`](../ecosystem.config.cjs). Commands: `start`, `stop`, `restart`, `status`, `logs`. |

---

## 2. Database & Data Migration Utilities

| Script | Description |
| :--- | :--- |
| [`backup_db.py`](backup_db.py) | Creates timestamped SQLite database backups into `backend/data/backups/`. |
| [`porter.py`](porter.py) | CLI utility for importing and exporting tasks, conversations, and research nodes across environments. |
| [`review_legacy_beliefs.py`](review_legacy_beliefs.py) | Generates review packets and replays legacy V1 belief proposals through the V2 evaluation boundary. |

---

## 3. Benchmarks & Telemetry Tools

| Script | Description |
| :--- | :--- |
| [`benchmark.py`](benchmark.py) | Primary telemetry benchmark runner. Supports `eval` (offline dialogue replay), `compare` (radar/metric deltas), and `live` (adversarial probe runs). |
| [`benchmark_research_receipts.py`](benchmark_research_receipts.py) | Benchmarks research action receipt throughput and persistence latency. |
| [`probe_research_provider.py`](probe_research_provider.py) | Validates LLM provider connectivity and structured output decoding for research phases. |
| [`backfill_response_quality.py`](backfill_response_quality.py) | Backfills historical response quality evaluations and token telemetry for older messages. |
| [`print_archetype_metrics.py`](print_archetype_metrics.py) | Inspects cybernetic archetype metric vectors for conversation states. |
| `generate_report_020_figures.py`, `021`, `022` | Visualization scripts generating polar radar and progression charts for empirical research reports in `docs/reports/`. |

---

## 4. Backend-Specific Maintenance Scripts

Administrative agent bootstrapping, vector repair, and deep background task maintenance scripts live inside [`backend/scripts/`](../backend/scripts/README.md).
