# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the
AAA project. Each ADR documents a significant architectural choice:
the context, the options considered, the decision, and its consequences.

## Format

```markdown
# ADR-NNN: Title

**Date:** YYYY-MM-DD
**Status:** proposed | accepted | deprecated | superseded
**Deciders:** [names]

## Context
What is the issue we're deciding?

## Options Considered
| Option | Pros | Cons |
|--------|------|------|

## Decision
What did we decide and why?

## Consequences
What becomes easier/harder?
```

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](ADR-001-personality-storage.md) | Personality Storage Strategy | accepted | 2026-05-20 |
| [002](ADR-002-skill-system.md) | Skill System Architecture | accepted | 2026-05-20 |
| [003](ADR-003-homeostatic-metrics.md) | Homeostatic Metrics | accepted | 2026-05-20 |
| [004](ADR-004-conversations-context-retrieval.md) | Conversation Model & Context Retrieval | accepted | 2026-05-20 |
| [005](ADR-005-perception-module.md) | Perception Module — File Upload & Sediment Retrieval | accepted | 2026-05-20 |
| [006](ADR-006-background-tasks.md) | Background Tasks — Autopoietic Self-Maintenance | accepted | 2026-05-21 |
| [007](ADR-007-context-compression.md) | Context Compression & Pruning | accepted | 2026-05-21 |
| [008](ADR-008-allostatic-metrics-refinements.md) | Allostatic Metrics Refinements | accepted | 2026-05-22 |
| [009](ADR-009-database-metrics-retrieval.md) | Database Metrics Retrieval & Test Integrity | accepted | 2026-05-22 |
| [010](ADR-010-multi-model-routing.md) | Stateful Multi-Model Routing, Key Rotation, and Metadata Persistence | accepted | 2026-05-22 |
| [011](ADR-011-rhizomatic-file-digestion-and-opacity.md) | Rhizomatic File Ingestion and Relational Opacity | accepted | 2026-05-22 |
| [012](ADR-012-conversation-pagination-and-lazy-loading.md) | Conversation Pagination, On-Demand Detail Loading, and Render Memoization | accepted | 2026-05-23 |
| [013](ADR-013-diffractive-retrieval.md) | Diffractive Retrieval and Stagnation Telemetry | accepted | 2026-05-23 |
| [014](ADR-014-structural-signature-engine.md) | 16-Dimensional Modular Structural Signature Engine | accepted | 2026-05-23 |
| [015](ADR-015-error-propagation-and-reprocessing.md) | Error Propagation and Manual Reprocessing for File Ingestion | accepted | 2026-05-24 |
| [016](ADR-016-extended-perception-and-web-retrieval.md) | Extended Perception, Exogenous Web Retrieval, and Prompts Centralization | accepted | 2026-06-01 |
| [017](ADR-017-dynamic-autopoietic-belief-metabolism.md) | Dynamic Autopoietic Belief Metabolism | accepted | 2026-06-02 |
| [018](ADR-018-ui-color-system-and-category-alignment.md) | UI Color System and Category Alignment | accepted | 2026-06-02 |
| [019](ADR-019-unified-document-belief-collision.md) | Unified Document Belief Collision Analysis | accepted | 2026-06-02 |
| [020](ADR-020-resumable-indexing-and-startup-scheduler.md) | Resumable Indexing and Startup Background Scheduler | accepted | 2026-06-02 |
| [021](ADR-021-thinking-suppression-two-speed-brain.md) | Thinking Suppression and Two-Speed Brain | accepted | 2026-06-03 |
| [022](ADR-022-semantic-knots-compaction.md) | Semantic Knots Compaction and Isomorphic Cross-Conversation Retrieval | accepted | 2026-06-03 |
| [023](ADR-023-autopoietic-dream-daemon.md) | Autopoietic Dream Daemon, Somatic Drift, and Memory Compaction | accepted | 2026-06-03 |
| [024](ADR-024-notes-and-selection-highlights.md) | Conversational Selection Highlights, Shared Entanglements, and Personal Notes | accepted | 2026-06-04 |
| [025a](ADR-025-cross-conversation-sediment-injection-and-split-tensions.md) | Cross-Conversation Sediment Injection and Markdown Insight Rendering | accepted | 2026-06-04 |
| [025b](ADR-025-self-annotation-and-scar-folds.md) | Self-Annotation and Scar Folds | accepted | 2026-06-04 |
| [026](ADR-026-decoupled-background-document-digestion.md) | Decoupled Background Document Digestion and Non-Blocking Event Loop | accepted | 2026-06-04 |
| [027](ADR-027-proto-belief-lifecycle-tension-ecology-self-tuning.md) | Proto-Belief Lifecycle, Tension Ecology, and Somatic Self-Tuning | accepted | 2026-06-05 |
| [028](ADR-028-structured-memory-nodes.md) | Structured Memory Nodes for Conversation Sedimentation | accepted | 2026-06-06 |
| [029](ADR-029-cross-conversation-sediment-file-fallback.md) | Cross-Conversation Sediment File Fallback | accepted | 2026-06-07 |
| [030](ADR-030-backend-modularity-refactoring.md) | Backend Modularity Refactoring | accepted | 2026-06-08 |
| [031](ADR-031-database-native-skill-system.md) | Database Native Skill System | accepted | 2026-06-09 |
| [032](ADR-032-branching-and-rhizomatic-conversations.md) | Branching and Rhizomatic Conversations | accepted | 2026-06-10 |
| [033](ADR-033-resonance-links.md) | Resonance Links: Agential, Asynchronous, and Spectral Co-Curation | accepted | 2026-06-10 |
| [034](ADR-034-decoupled-inscription-and-metabolization.md) | Decoupled Inscription and Metabolization | accepted | 2026-06-11 |
| [035](ADR-035-frontend-state-synchronization-and-render-optimizations.md) | URL State Synchronization, Render Memoization, and Trigger-based Telemetry | accepted | 2026-06-11 |
| [036](ADR-036-spatial-node-explorer-interface.md) | Spatial Node Explorer Interface | accepted | 2026-06-11 |
| [037](ADR-037-frontend-component-hierarchy-and-modularity.md) | Frontend Component Hierarchy and Modularity | accepted | 2026-06-11 |
| [038](ADR-038-creases-background-notifications-store.md) | Creases (Background Sediment Arrivals) and Pure JS Notification Store | accepted | 2026-06-11 |
| [039](ADR-039-cross-conversation-retro-links-and-active-message-focus.md) | Cross-Conversation Retro-links and Active Message Focus | accepted | 2026-06-11 |
| [040](ADR-040-subscriber-driven-telemetry-and-multi-type-notifications.md) | Subscriber-Driven Telemetry Polling and Multi-Type Notifications Store | accepted | 2026-06-11 |

## Creating a New ADR

1. Copy an existing ADR as a template
2. Use the next sequential number
3. Set status to `proposed` while under discussion
4. Change to `accepted` once decided
5. If a decision is later reversed, mark it `superseded` and link to its replacement
