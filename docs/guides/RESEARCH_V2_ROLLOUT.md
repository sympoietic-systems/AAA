# Research V2 rollout

The user authorized this release before independent research-quality calibration and will deploy it to the VPS. [Report 044](../reports/044-research-release-evaluation/README.md) records the tests and NVIDIA comparison. [ADR 113](../decisions/ADR-113-research-v2-authorized-rollout.md) records the authorization and branching boundaries.

## Update the VPS

Back up the application's SQLite database and uploaded files using your existing backup process, then update the checkout from `main`. Install dependencies using the existing deployment workflow, rebuild the frontend with `npm ci` and `npm run build`, and restart the backend through your existing service or Compose configuration. Backend startup runs the registered schema migrations; do not run a second ad hoc migration against the live database. Verify startup logs and a small newly created research task before launching a large batch.

No deployment command has been executed against the VPS. Service names, paths and orchestration commands depend on your installation.

## Defaults and task creation

`backend/config.yaml` enables `research_orchestrator.action_receipts_enabled: true` for new tasks. Existing tasks retain their frozen execution policy. Keep the orchestrator enabled. Jev research triage remains disabled (`research_triage.enabled: false`).

**Allow branching** is unchecked by default. Checked creation sends `subresearch_policy: bounded_auto`; unchecked sends `off`. The API also retains `propose` for a separate human review checkpoint. Dispatch consent allows qualified gathering under a versioned covenant, at most two children, no grandchildren and the parent deadline. Missing source witnesses or unsupported provider cost ceilings prevent branching. Model-authored dispatch cannot grant consent. Manual phase confirmation is a separate setting.

NVIDIA child reservations use zero-price ceilings for `nvidia` and `model_pool_nvidia`, based on the user's current free-provider assumption. Provider billing remains unknown when omitted. Configure conservative ceilings before admitting other provider families, and revisit the NVIDIA setting if pricing changes.

## PDF extraction

Keep `AAA_DOCLING_ENABLED=false` initially on the described 4-core/8-GB VPS. pdfplumber runs first. Optional Docling fallback runs only when standard extraction fails or is degraded; installation and bounded worker settings are documented in [Docling usage](DOCLING.md). Enabling it requires its separate runtime and model setup. The current corpus contains native text only; scanned-PDF accuracy and VPS resource suitability remain T75 work.

## Production review

Compare representative tasks with branching off and on. Check whether cited sources support each claim, whether useful coverage and contrary evidence survive synthesis, and whether child gathering adds evidence. Inspect partial/degraded status and provider receipts rather than interpreting a returned report as success. The final live replay was partial for V2 after a timeout; research quality superiority has not been demonstrated. Record examples and failures before changing limits or enabling optional parser routes.


## Smaller cycles and same-task recovery

New executions default to six search queries per cycle, including reflection followups. Set `AAA_RESEARCH_MAX_QUERIES` lower for shorter cycles and choose a higher research depth when more cycles are needed. Direct URLs remain a separate bounded group. Allow branching remains optional, with at most two qualified children and no grandchildren.

The safety watchdog defaults to 30 minutes, configurable with `AAA_RESEARCH_TIMEOUT_SECONDS`; provider attempts default to 128 per execution revision through `AAA_RESEARCH_MAX_ATTEMPTS`. Explicit **Rerun step** renews these limits while retaining the task ID, sources and completed analyses. For a timed-out Digest, select its rerun control after updating and restarting the backend. Automatic mode continues afterward; manual mode waits for the next click. Original failed receipts remain inspectable. See [configuration and recovery limits](CONFIG.md#research-cycle-and-recovery-limits).

The new-research form now defaults to depth 4, allowing more cycles than its previous depth 2. You can adjust depth before dispatch; evaluation and resource limits may stop the run earlier. Existing tasks retain their selected depth.
