# ADR-016: Extended Perception and Exogenous Web Retrieval

## Status
Accepted

## Context
The AAA (Autopoietic Aesthetic Agent) system was previously limited to digesting standard textual assets in the perception loop. To fulfill its cybernetic goals, the agent needs to perceive visual artifacts (such as handwritten journal pages, flowcharts, diagrams, and artistic media) and retrieve real-time facts or external reference materials via the internet. These perception capabilities must remain highly modular, easily toggleable, and free of complex or heavy external dependencies (e.g., Selenium, Playwright, or external OCR APIs).

## Decision
1. **Tripartite Vision Pipeline**: Route uploaded files categorized as `image` (PNG, JPEG, WebP, etc.) through a multi-phase vision ingestion process in the background. Using the designated vision model (configured as an OpenAI-compatible multimodal endpoint), categorize the image, extract any text via OCR, generate aesthetic/somatic notes, identify belief node collisions (`belief_nodes_implicated`), and perform a diffractive analysis of the visual structure.
2. **Somatic 16D Signature Warping**: Dynamic aesthetic telemetry—specifically Glitch Fidelity ($G_f$) and Aesthetic Dissidence ($A_d$)—will warp the default 16-dimensional cybernetic coordinate signature of the image chunks before embedding. 
   - High $G_f$ dampens Homeostatic ($s_{01}$) and Cyclic ($s_{03}$) coordinates while magnifying Bifurcated ($s_{04}$) and Rhizomatic ($s_{06}$) coordinates.
   - High $A_d$ dampens Variety Filtering ($s_{09}$) and Temporal Latency ($s_{11}$) while magnifying Nomadic ($s_{14}$) and Boundary Permeability ($s_{07}$) coordinates.
3. **Rhizome Web Probe**: Implement `WebRetrievalModule` as an active pipeline step executing before the prompt assembler. Utilize standard library `html.parser` to parse DuckDuckGo (HTML and Lite versions) query responses, fetch the top result, and scrape HTML-to-markdown text asynchronously.
4. **Context Injection**: Exogenous web context and direct URL crawl payloads are injected as boundary system blocks (`--- BEGIN EXOGENOUS WEB CONTEXT ---`) into the prompt assembler to extend the LLM context dynamically.
5. **Exogenous & Somatic UI Telemetry**: Expand the Right Panel file summary rendering to replace raw JSON metadata blocks with structured, custom-designed layouts:
   - For image files: Display Somatic Ingestion Records containing classification badges, G_f/A_d aesthetic scores, somatic notes, diffractive analyses, OCR transcriptions, and a visual sparkline representing the 16D structural signature with an interactive hover inspector showing value descriptions.
   - For web probes: Display Exogenous Search Telemetry detailing queries, clickable URLs, interference metrics, and belief node outline tag pills (e.g. `autopoiesis`, `somatic_exhaustion`, etc.) styled as violet outline pills.
6. **Pipeline Metadata & Submodule Registry**: Enriched the core `SkillMeta` definitions in the `SkillRegistry` initialization with granular children submodules (e.g. `text_encoder`, `signature_generator`, `tripartite_vision`, `rhizome_web_probe`, `allostatic_parameter_adjuster`, etc.) to provide comprehensive operational visibility within the client UI.
7. **Vision Model Pool & API Key Rotation**: Extended LLM client initialization to support a prioritized pool of vision-capable models (`AAA_VISION_MODELS` and `AAA_VISION_FALLBACK_MODEL`) running on endpoints such as OpenRouter or Google. Implement automatic API key rotation and model failover to gracefully handle HTTP 503 errors and rate limits during ingestion.
8. **Centralized Prompts Configuration**: Refactored the codebase to move all inline and local module system and user prompts into a centralized, single-source directory (`backend/prompts/`) structured by subsystem (`perception/`, `web_retrieval/`, `structural_engine/`, `background_tasks/`). Implement robust Python runtime loaders that dynamically read from these YAML templates but preserve safe, backwards-compatible default prompt string fallbacks.

## Consequences
- **Robustness & Performance**: Dependency-free scraping prevents maintenance drift and ensures rapid async executions.
- **Aesthetic Telemetry**: Images containing artistic glitches or dissident diagrams are automatically routed to nomadic/rhizomatic semantic spaces, causing them to interfere differently with the agent's core belief networks.
- **UI Diagnostics**: Users can instantly analyze image classifications, aesthetic indexes, 16D signatures with interactive hover descriptors, and web probe queries directly in the UI.
- **Submodule Visibility**: The right panel exposes sub-system activity (like OCR, crawling, and regulation), showing precisely which sub-components executed.
- **Toggleability**: Both vision processing and web retrieval can be toggled or re-routed via settings in `config.yaml`.
- **System Service Reliability**: With model failover pooling and Google API key rotation, the perception ingestion pipeline will not crash or fail during high-traffic or rate-limiting events.
- **Prompt Maintainability**: System prompts, query routing schemas, and summarization guidelines can now be customized directly in YAML without modifying python backend scripts. Fallback logic prevents crash conditions if configuration files are missing.
