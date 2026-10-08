# Empirical Benchmark & Calibration Reports

This directory serves as the **Single Source of Truth (SSOT)** for all empirical benchmark evaluations, telemetry calibrations, and performance scorecards of the **Autopoietic Agentic Assemblage (AAA)**.

> **Canonical Protocol:** Adhere strictly to the workspace invariants in [`.agents/protocols/DOCUMENTATION.md`](../../.agents/protocols/DOCUMENTATION.md) and [`report-architect`](../../.agents/skills/report-architect/SKILL.md). All raw JSON receipts, oscilloscope recordings, and generated plots belong exclusively in their corresponding `NNN-<topic>/` subdirectories.

---

## Benchmark & Calibration Registry

| Report | Title & Scope | Primary Subsystem | Key Invariant / Outcome |
| :---: | :--- | :--- | :--- |
| **[050](050-research-digestion-provider-failure/README.md)** | Research digestion provider failure | Research / LLM pool | Upstream capacity preserves credentials; bounded cooldown recovery; explicit failed analysis |
| **[002](002-16d-structural-scoring-benchmark-report.md)** | **16D Structural Scorer Benchmark** | `backend/modules/` | Jev vs. LLM baseline: sub-600ms latency, dual-signal Power ($s_i$) & Confidence ($c_i$) across 16 cybernetic dimensions. |
| **[003](003-empirical-10-turn-benchmark-report.md)** | **10-Turn Adversarial Benchmark** | `backend/modules/metrics/` | Head-to-head pressure test: AAA apparatus vs. Google Gemini 3.7 Flash across 14 metrics. |
| **[004](004-conversation-metrics-calibration-report.md)** | **Conversation Metrics Calibration** | `backend/modules/metrics/` | Calibration of Coupling Coherence ($C_t$) & Divergence Resolution Ratio ($DRR_t$) on $\mathbb{S}^{383}$. |
| **[005](005-surprise-and-paskian-health-calibration-report.md)** | **Surprise & Paskian Health Calibration** | `backend/modules/metrics/` | Geodesic slerp surprise, Cobb-Douglas Paskian Vitality ($H_{\text{pask}}$), and interaction health. |
| **[006](006-velocity-and-collapse-pressure-calibration-report.md)** | **Velocity & Collapse Pressure Calibration** | `backend/modules/metrics/` | Instantaneous conceptual velocity and tangent Minkowski collapse pressure ($CP_t$). |
| **[007](007-perturbation-and-spectral-entropy-calibration-report.md)** | **Perturbation & Spectral Entropy Calibration** | `backend/modules/metrics/` | Transverse vector shear perturbation and participation ratio spectral entropy ($H_{\text{spec}}$). |
| **[008](008-resonance-and-self-divergence-calibration-report.md)** | **Resonance & Self-Divergence Calibration** | `backend/modules/metrics/` | Softmin subspace divergence and dual-horizon novelty ($N_t$). |
| **[009](009-cybernetic-conversation-metrics-meta-report.md)** | **14 Cybernetic Metrics Meta-Report** | `backend/modules/metrics/` | Master scorecard and radar sensitivity synthesis for all 14 calibrated sensors. |
| **[010](010-cybernetic-conversation-metrics-accessible-guide.md)** | **Accessible Guide to Cybernetic Sensors** | `docs/guides/` | How the machine senses, navigates, and feels dialogue movements (pedagogical guide). |
| **[011](011-divergence-resolution-ratio-geodesic-calibration-report.md)** | **DRR Geodesic Manifold Calibration** | `backend/modules/metrics/` | Geodesic parallel transport and temporal decay on spherical semantic space. |
| **[012](012-complete-14-metrics-calibration-and-scorecard-report.md)** | **Complete 14-Metrics Master Scorecard** | `backend/modules/metrics/` | Production scorecard across all 14 metrics across $\mathbb{S}^{383}$. |
| **[013](013-cybernetic-conversation-metrics-complete-accessible-guide.md)** | **The Inner Senses of Conversation** | `docs/guides/` | Comprehensive operational guide to conversational telemetry sensors. |
| **[014](014-boredom-detection-and-agential-resistance-calibration-report.md)** | **Boredom Detection & Resistance Calibration** | `backend/modules/boredom/` | Separation margin, discriminability benchmark, and allostatic sampling modulation. |
| **[015](015-empirical-15-turn-boredom-benchmark-report.md)** | **15-Turn Empirical Boredom Benchmark** | `backend/modules/boredom/` | 1:1 model parity on Gemini 3.7 Flash: 4-arm control ablation with raw JSON receipts. |
| **[016](016-backend-resource-and-concurrency-optimization-report.md)** | **Backend Resource & Concurrency Report** | `backend/` | Thread clamping, SQLite connection scopes, and zero event loop starvation. |
| **[017](017-agential-boredom-engine-and-socratic-rupture-report.md)** | **Agential Boredom Engine & Socratic Rupture** | `backend/modules/boredom/` | Two-stage progression (Socratic Seizure $\to$ Laconic Compression) & quadratic presence penalty. |
| **[018](018-afferent-sensory-membrane-and-skill-blueprint-report.md)** | **Afferent Sensory Membrane & Skill Blueprints** | `backend/modules/sensory/`, `backend/prompts/` | TypeSafe Jev System One afferent membrane, 0% contemplative false positives, and 5-phase SCAR skill blueprints. |
| **[019](019-dialogue-feedback-control-report.md)** | **Dialogue Feedback Control** | `backend/modules/metrics/`, `backend/modules/sensory/` | Causal receipts, adaptive retrieval gate, and rejected progressive intervention ablation. |
| **[020](020-paskian-teachback-and-operational-accommodation-report.md)** | **Paskian Teachback & Operational Accommodation** | `backend/modules/` | 3-beat Paskian controller ablation with Nemotron-3 Super 120B on NVIDIA NIM (+0.113 conceptual velocity). |
| **[021](021-long-horizon-dialogue-scenarios-report.md)** | **Long-Horizon Dialogue Feedback Scenarios** | `backend/modules/` | 20-turn adversarial stress test of Paskian homeostasis, semantic knot compaction, and simulator realism audits. |
| **[022](022-relational-conversational-archetypes-report.md)** | **Relational Conversational Archetypes & Phase Space** | `backend/modules/` | 5 relational archetypes benchmark on Nemotron-3 Super 120B: +33.8% DRR ($p=0.043$), -17.3% collapse pressure ($p=0.019$). |

---

### Additional Operational & Verification Reports

- [Report 021: Message tree integrity](021-message-tree-integrity-report.md)
- [Report 022: Skill vitality audit](022-skill-vitality-audit-report.md)
- [Report 023: Jev research triage](023-jev-research-triage-report.md)
- [Report 024: Jev belief routing and tension evidence](024-jev-belief-routing-and-tension-report.md)
- [Report 025: Four follow-ups delivery and integrated verification](025-four-followups-delivery-report.md)
- [Report 026: Post-merge usage and calibration plan](026-post-merge-usage-and-calibration-plan.md)
- [Report 027: Baseline quality gate repairs](027-baseline-quality-gates-report.md)
- [Report 028: Activation provenance and stale skill review](028-activation-provenance-and-stale-skill-review.md)
- [Report 029: Belief context and calibration workflow](029-belief-context-and-calibration-workflow.md)
- [Report 030: Research screening calibration workflow](030-research-screening-calibration-workflow.md)
- [Report 031: Next actions delivery](031-next-actions-delivery-report.md)
- [Report 032: Main release and remaining gates](032-main-release-and-remaining-gates.md)
- [Report 033: Research receipt contracts and offline baseline](033-research-receipt-baseline/README.md)
- [Report 034: Research provider reliability](034-research-provider-reliability/README.md)
- [Report 035: Research evidence substrate](035-research-evidence-substrate/README.md)
- [Report 036: Bounded research acquisition](036-research-acquisition/README.md)
- [Report 037: Finite research actions](037-research-finite-actions/README.md)
- [Report 038: Human branch proposals](038-research-branch-proposals/README.md)
- [Report 039: Approved research children](039-approved-research-children/README.md)
- [Report 040: Optional Docling fallback](040-docling-fallback/README.md)
- [Report 041: Provisional research labeling](041-research-provisional-labeling/README.md)
- [Report 045: Belief system month review](045-belief-month-review/README.md)
- [Report 046: Beliefs v2 baseline and creation-path inventory](046-belief-v2-baseline/README.md)
- [Report 047: Beliefs v2 measured quantities and decay accounting](047-belief-v2-quantities-and-decay/README.md)
