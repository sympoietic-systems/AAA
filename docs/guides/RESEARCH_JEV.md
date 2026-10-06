# Jev research selection — not adopted

The research branch sets `research_triage.enabled: false` in `backend/config.yaml`. On 2026-10-06 the user withdrew the earlier experimental promotion and chose not to use Jev for this task. Research search uses the standard selector and skips Jev. The same switch disables research triage in the web probe; other TypeSafe/Jev integrations are unchanged. Restart the service after applying the configuration on the VPS; this repository change does not deploy it.

The remaining description documents the retained, disabled integration for future evaluation. Re-enabling it requires a new rollout decision.

Configure the existing `typesafe` provider credentials/model/base URL for the intended Jev endpoint. Keep credentials in the environment; do not commit them. An unconfigured provider produces an unavailable receipt and uses standard selection.

Search selection first asks Jev to score at most ten candidates. Every answer must contain valid probabilities and confidence at least 0.7. A selected receipt admits Jev's ranking. Abstention or unavailability invokes the existing standard selector; if that selector cannot provide a usable ranking, its existing top-results fallback applies. The Jev receipt retains its original candidate and selected IDs, while `fallback_selector` and `fallback_selected_ids` identify the subsequent selection separately. Fallback output never counts as an accepted Jev benchmark decision.

The switch also enables the existing evidence triage integration in the web probe. Its collision guards and prohibition on generative belief authorship remain unchanged. The new standard-selector fallback applies to orchestrator search; the web probe retains its existing top-result fallback.

[Report 042](../reports/042-jev-experimental-promotion/README.md) owns the comparison results and limitations. Independent labels, downstream support/coverage review and integrated release approval remain T71. The confidence threshold was not tuned on this held-out packet.
