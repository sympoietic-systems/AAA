# AAA Documentation Philosophy & Governance Framework

> **Canonical Protocol:** Adhere to the workspace invariants in [`.agents/protocols/DOCUMENTATION.md`](../.agents/protocols/DOCUMENTATION.md).

This document outlines the organizing philosophy, structural frameworks, and core principles that govern knowledge, technical specifications, empirical data, and public publications in **AAA (Autopoietic Agentic Assemblage)**.

Rather than cataloging individual files, this framework establishes how to think about and structure any document or artifact—existing or future.

---

## 1. The Organizing Philosophy: The Four Agential Realms

Every document in AAA serves a distinct cognitive and systemic purpose. Mixing these purposes creates maintenance drag and rot. All documentation falls into one of four primary realms:

```
                  ┌──────────────────────────────────────────────┐
                  │           1. LIVING ARCHITECTURE             │
                  │   (architecture/, systems/, decisions/)      │
                  │  How the machine is wired and why decisions  │
                  │                  were made.                  │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │                                               │
                 ▼                                               ▼
  ┌──────────────────────────────┐               ┌──────────────────────────────┐
  │     2. EMPIRICAL GROUND      │               │     3. PUBLIC NARRATIVE      │
  │          (reports/)          │               │          (publish/)          │
  │   Immutable receipts, runs,  │◄──────────────┤ Philosophical essays, essays │
  │ telemetry, benchmark scores. │   (Cites via  │ for external human readers.  │
  │    [Owns the hard data]      │   reference)  │     [Zero data cloning]      │
  └──────────────────────────────┘               └──────────────────────────────┘
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         │
                  ┌──────────────────────▼──────────────────────┐
                  │             4. OPERATIONAL RUNBOOKS         │
                  │              (guides/, development/)        │
                  │ How human operators and developers install, │
                  │     configure, run, and develop the system. │
                  └─────────────────────────────────────────────┘
```

### I. Living Architecture (The Machine's Internal Blueprint)
* **Purpose:** High-level topology, subsystem boundaries, data flow pipelines, and formal Architecture Decision Records (ADRs).
* **Audience:** Developers, AI coding agents, maintainers.
* **Character:** Technical, rigorous, precise, living (updated as code evolves, with ADRs remaining immutable once accepted).

### II. Empirical Ground (The Scientific Record)
* **Purpose:** Benchmark evaluation results, telemetry receipts, sensor calibration scorecards, and oscilloscope traces.
* **Audience:** Researchers, reviewers, auditors, agents verifying performance.
* **Character:** Empirical, immutable, timestamped. Represents verified observations of system behavior under specific conditions.

### III. Public Narrative (Sympoietic Reflection)
* **Purpose:** Public-facing essays, philosophical treatises, and essays published through *Sympoietic Systems*.
* **Audience:** External readers, philosophers, cyberneticians, the wider community.
* **Character:** Narrative, conceptual, essayistic. Follows the authorial voice and aesthetic guidelines in [STYLE.md](../.agents/protocols/STYLE.md) and [VISUALS.md](../.agents/protocols/VISUALS.md).

### IV. Operational Runbooks & Developer Enablement
* **Purpose:** Onboarding, environment configuration, command references, and internal developer practices.
* **Audience:** Operators setting up or interacting with the runtime.
* **Character:** Step-by-step, actionable, pragmatic.

---

## 2. Core Governance Principles

### Principle 1: Single Source of Truth (SSOT) — No Data Duplication
- **Data belongs where it was produced:** Benchmark runs, telemetry JSON, oscilloscope output, and raw evaluation matrices belong exclusively in `reports/` (and `benchmarks/runs/`).
- **Narratives cite, never clone:** Public publications, high-level architecture documents, and ADRs must cite empirical reports via relative markdown links rather than copying raw metrics, duplicate JSON runs, or duplicated charts into their own folders.

### Principle 2: Agential Encapsulation (Bundle Self-Sufficiency)
- Complex or multi-artifact documents (such as public essays with hero visual art, or empirical reports with specialized run traces) should be encapsulated as self-contained bundles:
  ```
  parent_realm/
  └── NNN-<slug>/
      ├── NNN-<slug>.md       # Primary text
      └── assets/             # Tightly-coupled visuals or local artifacts
  ```
- This prevents the root of any realm from becoming an untracked graveyard of loose images and stray notes.

### Principle 3: Monotonic Provenance (Numbered Lineage)
- For records that represent a historical trajectory—such as Architecture Decision Records (`decisions/`), empirical benchmarks (`reports/`), or publication series (`publish/`)—use zero-padded sequential numbering (`NNN-` or `ADR-NNN-`).
- This guarantees:
  1. Natural chronological sorting across all operating systems and git tools.
  2. Unambiguous citation (`Report 015`, `ADR-087`, `Publication 004`).
  3. Clear visibility into the evolutionary path of the assemblage.

### Principle 4: Separation of the Ephemeral from the Enduring
- **Never commit transient scratchpads:** Temporary debug dumps, one-off test scripts, or model-scratch outputs belong in local agent scratchpads (`.agents/scratch/` or IDE brain directories), not in repository documentation.
- When an exploratory thought solidifies into a permanent proposal or engineering standard, it is formally written into `docs/development/` or `docs/decisions/`.

### Principle 5: Relational Integrity (Living Web)
- Documentation in AAA is not a static flat archive; it is a connected semantic web.
- Whenever an entity is moved, renamed, or refactored:
  - All incoming relative links must be updated in the same change.
  - The realm index (`README.md`) must be kept in sync.
  - Links should point directly to the canonical source, avoiding circular or ambiguous references.

---

## 3. General Conventions (Heuristics)

To keep conventions adaptable to future formats, apply these general heuristics:

| Document Type | Naming Heuristic | Why |
| :--- | :--- | :--- |
| **System & Subsystem Specs** | `UPPER_SNAKE_CASE.md` | Distinguishes canonical system specifications from narrative text. |
| **Historical & Sequential Records** | `NNN-<kebab-case>` | Preserves chronological order and makes references concise (`ADR-032`, `015-...`). |
| **Operational Guides** | `UPPER_SNAKE_CASE.md` | Immediately identifiable as operational manuals (`SETUP.md`, `CONFIG.md`). |
| **Asset Folders** | `assets/` | Consistent convention for media directly accompanying a document bundle. |

---

## 4. How to Decide Where New Content Belongs

When introducing a new document or artifact, ask these four questions:

1. **Is it describing how the code works right now?**  
   ➔ `docs/systems/` or `docs/architecture/`
2. **Is it recording an architectural choice that was considered and locked in?**  
   ➔ `docs/decisions/` (ADR)
3. **Is it an empirical measurement, benchmark, or telemetry result?**  
   ➔ `docs/reports/` (SSOT)
4. **Is it a public-facing reflection, philosophical inquiry, or publication?**  
   ➔ `docs/publish/` (Encapsulated bundle)
5. **Is it practical instructions for running, configuring, or coding?**  
   ➔ `docs/guides/` or `docs/development/practices/`
