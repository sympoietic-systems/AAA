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

Optional processing of new research findings into the belief system has a 15-second limit per phase, shortened when the execution watchdog has less time remaining. A timeout or exhausted execution capacity records `research_metabolism_incomplete` and partial delivery; saved research findings remain available and the research can advance. Cancellation still stops the caller. Auxiliary work that resists cancellation remains bounded by the existing execution slots until it finishes; this does not roll back belief writes already made.

When a phase fails before its processor creates a step, the backend now records a failed row using the existing research plan. Its rerun control can recover that phase on the same task. Completed search groups remain completed. Earlier executions that lack this row can retry the last visible Consolidate step to renew the execution window and continue. Restart the backend after pulling the fix; rerunning is an explicit operator action.

## Recovery after structured Digest output

See also [phase validation and visible failures](#phase-validation-and-visible-failures-t82) for later phases.

Digest accepts text lists, individual text fields, and recognized objects such as `{"learning": "...", "relevance": "..."}`. It projects the primary text into the pipeline and retains the original analysis in `raw_analysis`. Relevance, impact and connection metadata do not become findings. Unknown objects or numeric items produce an explicit source-analysis failure. Normalization applies to both new model responses and saved analyses; it preserves their existing unreviewed evidence status.

If the task fails with `can only concatenate str (not "dict") to str`, update the checkout and restart the backend, then use **rerun on a Digest row in the latest cycle**. Individual Digest rows may show completed even though combining their results failed. Rerunning Digest recovers the same task, retains parsed source text and reuses valid saved analyses. It renews the execution limits and continues to Consolidate automatically in automatic mode; manual mode waits for the next step. Search and parsing do not need to be repeated for this failure. Merely refreshing or restarting the server does not replay the failed phase.


## Phase validation and visible failures (T82)

Planning validates model-authored queries before saving its plan; invalid output uses the existing objective-based plan. Consolidation and reflection validate their text lists and numerical scores before marking their rows complete. Completeness, confidence and fidelity must be finite fractions between zero and one. Numeric score strings can be converted by the typed contract; invalid objects, lists and non-finite scores fail visibly. Source entropy is finite and nonnegative, and can exceed one.

Synthesis requires a nonempty textual report or answer. Invalid JSON, a structured object in the report field, an invalid answer confidence, a missing provider or a provider exception leaves synthesis failed and available for rerun. The backend no longer substitutes a generic completion sentence for an unusable report. Evaluation retains its conservative continue fallback when its model decision or reason is invalid.

A phase returning failed or error stops before findings are merged or the pipeline advances. Saved-state validation failures create a visible failed phase row when a plan exists. Interrupted-action and missing-prerequisite guards retain their existing recovery behavior; validation cannot authorize replay of an interrupted provider action.

After updating main and restarting the backend, rerun the failed phase on the existing research. If a document is still indexing, wait for indexing to finish before retrying document digestion. Malformed saved input must be corrected or regenerated through its preceding phase before retrying. These checks contain delivery errors; they do not establish the accuracy of model-authored claims. Scanned-PDF accuracy and live VPS acceptance remain separate work.


## Synthesis recovery after invalid JSON escapes (T83)

A report can contain literal Markdown or LaTeX backslashes, including escaped source citations. When those backslashes are not encoded correctly in the model's JSON, synthesis first attempts strict parsing, then preserves invalid escape sequences as literal report text and strictly parses the repaired result. Valid JSON escapes are unchanged. The linear repair is capped at 2,048 invalid escapes; broken structure, truncation, malformed Unicode and invalid report fields still fail visibly.

A recovered report records synthesis_json_escape_repaired with the repair count and marks delivery degraded/partial. The original model response stays in the step data. This is transport-format recovery, with no claim that the research conclusions are accurate. After updating main and restarting the backend, rerun Synthesize on the existing task; it uses saved findings without repeating Search or Digest. A server restart alone does not load changes that have not yet been pulled or explicitly replay an interrupted action. If rerun reports a live execution or phase-lock conflict, wait for that attempt to end. After a restart, a stale running label alone does not block explicit phase recovery; persisted interrupted-action guards still apply.


## Main-model synthesis and provider execution failures (T84)

Research synthesis uses the configured main provider. For a model pool, it explicitly selects primary_model (the first configured pool model), so a sticky last-working Nemotron model or failure of the main model cannot silently change the synthesis model. A direct provider continues to use its configured model. Earlier prefer_primary behavior tried the main model first but permitted fallback.

An empty response with a provider error now fails with an execution-boundary or provider-request message before validating report fields. The raw wrapper remains available for diagnosis. A retry-boundary failure can reflect request attempts or remaining execution time; it is not evidence of a particular upstream rate limit. Existing attempt and deadline limits remain enforced. Explicitly rerun Synthesize on the same research after pulling main and restarting to renew the execution revision and use saved findings. If the main provider remains unavailable, synthesis remains failed instead of switching to another model.
