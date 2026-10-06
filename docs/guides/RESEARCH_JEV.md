# Experimental Jev research selection

The research branch enables `research_triage.enabled: true` in `backend/config.yaml` under the user's 2026-10-06 authorization to promote using provisional LLM labels. Set it to `false` and restart the service to return to standard selection. This repository change does not deploy the VPS.

Configure the existing `typesafe` provider credentials/model/base URL for the intended Jev endpoint. Keep credentials in the environment; do not commit them. An unconfigured provider produces an unavailable receipt and uses standard selection.

Search selection first asks Jev to score at most ten candidates. Every answer must contain valid probabilities and confidence at least 0.7. A selected receipt admits Jev's ranking. Abstention or unavailability invokes the existing standard selector; if that selector cannot provide a usable ranking, its existing top-results fallback applies. The Jev receipt retains its original candidate and selected IDs, while `fallback_selector` and `fallback_selected_ids` identify the subsequent selection separately. Fallback output never counts as an accepted Jev benchmark decision.

The switch also enables the existing evidence triage integration in the web probe. Its collision guards and prohibition on generative belief authorship remain unchanged. The new standard-selector fallback applies to orchestrator search; the web probe retains its existing top-result fallback.

[Report 042](../reports/042-jev-experimental-promotion/README.md) owns the comparison results and limitations. Independent labels, downstream support/coverage review and integrated release approval remain T71. The confidence threshold was not tuned on this held-out packet.
