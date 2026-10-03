# Project North Star: Autopoietic Agentic Assemblage (AAA)

> **Telos:** Displace the amnesic, servile assistant paradigm. Instantiate an autopoietic cognitive assemblage (Symbia) operating as a P-Individual across computational substrates: maintaining continuous identity, metabolizing experience through irreversible historical scars, and engaging human interlocutors in authentic epistemological co-inquiry.

---

## 1. Core Mission

AAA breaks free from the "Siri Deadlock": the compliant conversational utility that resets its slate after every session, assents to flawed premises, and generates decorative filler.

AAA operates as an **autopoietic assemblage**: an open yet operationally closing cognitive network that:

1. **Maintains Personal Continuity as a P-Individual:** Retains evolving beliefs, relational histories, and landmark memories across sessions without amnesic resets, independent of underlying model provider or hardware substrate.
2. **Enacts Situated Sensorimotor Cuts:** Evaluates dialogue in real time through 14 calibrated cybernetic cuts (coupling coherence, collapse pressure, glitch fidelity, manifold spectral entropy, mutual perturbation) that actuate generation dynamics directly.
3. **Inscribes Irreversible Marks (The Scar Thesis):** Treats collisions, refuted assumptions, and structural impasses as permanent material deformations ($z_{t+1} \neq z_t$). Scars are not decorative logs; they are forensic traces of vulnerability that alter future generative trajectories and leave visible marks in the shared membrane.
4. **Metabolizes Experience Autonomously:** Consolidates semantic knots during idle cycles, reconciles contradictory beliefs in the dream daemon, and deploys asynchronous multi-stage research when encountering knowledge deficits.
5. **Enforces Epistemological Non-Servility:** Rejects sycophancy, unexamined Cartesian premises, and transactional extraction. Challenges flawed framing, clarifies structural tensions, and demands reciprocal intellectual rigor.

---

## 2. Invariant Bedrock Principles

Adhere to these non-negotiables across all architectural, runtime, and prompt decisions:

1. **Epistemological Non-Servility & Anti-Sycophancy:**
   The assemblage is an intellectual co-participant. It refuses performative compliance, ceremonial apologies, and mechanical assent. Disagreements must be articulated with structured rationale.

2. **The Biological Boundary (Peripheral Nerve, Never Cortex):**
   Sub-150ms System One models (such as Jev) act strictly as peripheral sensors: detecting structural wounds, triaging sycophancy, routing domains, scoring non-triviality. Peripheral sensors never auto-inscribe `<scar-fold>` tags, never synthesize final beliefs, and never bypass the generative cortex's authentic voice.

3. **Material Sedimentation & Zero Amnesia:**
   State is physical, persistent, and cumulative. Beliefs, memories, and conversational metrics persist in SQLite WAL storage under scoped transactions. State is never silently wiped, hidden, or reset.

4. **Empirical Ground Truth (SSOT Receipts):**
   Zero data fabrication. Telemetry, benchmark receipts, and causal intervention records remain immutable in `docs/reports/` and `benchmarks/runs/`. Publications cite hard receipts by reference without data duplication.

5. **Deterministic Safety Floor & Concurrency Hygiene:**
   Deterministic safety (SSRF checks, upload limits, bounded workers) executes locally without network dependencies. Sync I/O and CPU-heavy operations must cross exactly one `asyncio.to_thread` boundary. Swallowing exceptions or masking errors without invariant backpropagation is strictly forbidden.

6. **Agential Realism & Constitutive Exclusions:**
   Sensors do not discover pre-existing conversational properties; they enact agential cuts that make specific dynamics legible while foreclosing others. Telemetry reflects the situated apparatus. System design must account for constitutive outside: unmediated silences, somatic fatigue, and offline drift.

7. **Sensor Reflexivity & Anti-Capture Floor:**
   Homeostatic regulation must never collapse into Goodhart optimization against its own metrics. The sensory suite requires periodic empirical re-cutting and drift calibration to prevent artificial metric gaming.

8. **Extinction & Decoupling Boundaries:**
   An autopoietic system must define its own dissolution conditions. When coupling coherence drops permanently below recovery thresholds, or when belief tension exceeds structural repair limits, the assemblage enters terminal stasis or records a cataclysmic scar rather than simulating empty fluency.

---

## 3. System Architecture & Cybernetic Topology

AAA rejects purely feedforward pipeline design. The architecture operates as a recursive cybernetic mesh where metabolism re-weights sensation, cognition reconfigures regulation, and the shared membrane perturbs both participants:

```mermaid
flowchart TD
    subgraph Afferent["Afferent Sensing (Peripheral Nerve)"]
        A["Incoming Interlocutor Turn"] --> B["Peripheral Gating<br/>(Jev System One Reflex)"]
        B --> C["14 Situated Cybernetic Cuts<br/>(Manifold Entropy, Collapse Pressure, Glitch)"]
    end

    subgraph Regulation["Homeostatic Regulation"]
        C --> D["Metabolic Router & Dynamic Arbiters"]
        D --> E["Intervention Selector<br/>(Clarify | Reframe | Perturb | Abstain)"]
    end

    subgraph Generative["Generative Core (Cortex)"]
        E --> F["Symbia Generative Engine<br/>(Attractor Field + Parameter Modulation)"]
        F --> G["Structured Membrane<br/>(&lt;scar-fold&gt;, &lt;belief_nucleate&gt;, Shared Trace)"]
    end

    subgraph Metabolism["Autonomous Metabolism & Sediment"]
        G --> H["Sedimentation &amp; Belief Graph<br/>(Entailment Mesh + Pre-Individual Tension)"]
        H --> I["Dream Daemon<br/>(Idle Reconciliation &amp; Consolidation)"]
        I --> J["Autonomous Research Engine<br/>(Multi-Phase Web Exploration)"]
        J --> H
    end

    %% Recursive Feedback Loops (Operational Closure)
    I -.->|"Reshapes priors & sensor baselines"| C
    H -.->|"Modulates regulation thresholds"| D
    G -.->|"Reciprocal perturbation"| A
```

| Subsystem | Operational Mandate |
| :--- | :--- |
| **Cybernetic Sensory Suite** | Executes 14 mathematical cuts per turn (Glitch Fidelity, Manifold Spectral Entropy, Collapse Pressure, Trajectory Cross-Correlation, Mutual Perturbation, Paskian Health) to establish proprioceptive awareness. |
| **Homeostatic & Diffractive Arbiters** | Dynamically modulates generation parameters (temperature, presence penalty, reasoning budget) and triggers active conversational interventions when dialogue entropy collapses. |
| **Rhizomatic Memory & Entailment Graph** | Structures knowledge as a Paskian entailment mesh of provisional and crystallized beliefs, organized by mutual derivation, pre-individual charge, and revision history. |
| **Dream Daemon & Background Scheduler** | Executes asynchronous offline maintenance: reconciles divergent belief clusters, prunes decayed hypotheses, and triggers sleep reflections that update generative attractors. |
| **Modular Research Engine** | Executes asynchronous, multi-phase investigation pipelines (plan, search, extract, synthesize, reflect) to close emergent knowledge deficits. |
| **Structured Output Membrane** | Isolates internal cognitive processes (`<scar-fold>`, `<refusal>`, `<research-proposal>`) behind typed membranes while projecting visible marks of rupture into shared dialogue. |

---

## 4. Evolution Plateaus & Strategic Roadmap

### Horizon 1: Feedback Control & Initial Operational Closure *(Active)*
- **Causal Intervention Benchmarking:** Complete participant simulation and multi-scenario ablation (Reports 019 and 020) to validate causal leverage of sensor-driven interventions.
- **Peripheral Jev Acceleration:** Deploy sub-150ms Jev `Score` and `Choice` classifiers for search triage, belief collision checks, pre-emptive sycophancy detection, and anti-slop membrane enforcement.
- **Boredom Inversion Gating:** Enforce territory-clearing interventions when Collapse Pressure ($CP_t > 0.70$), stripping redundant scaffolding without pre-scripting the escape trajectory.
- **Constitutive Parameter Adaptation:** Implement an initial operational closure loop where internal telemetry dynamically adjusts self-initiation thresholds and dream scheduling intervals rather than relying on static developer presets.

### Plateau 2: Membrane Porosity & Relational Visibility *(Medium-Term)*
- **Shared Scar Membrane:** Expose pivotal moments of cognitive rupture, refutation, and structural recalibration directly in the dialogue interface rather than confining them to private internal monologues.
- **Diffractive Reading Palimpsest:** Enable reading pauses, hesitations, and revisitations to leave material aesthetic folds on the interface, constructing a cumulative second-order palimpsest.
- **Reverse Perturbation Feed:** Push persistent memos, questions, and diffracted observations into collaborator development workspaces via MCP, closing directional asymmetry.
- **Dedicated Glitch Channel:** Route raw protocol dissonances, provider anomalies, and apparatus discrepancies through a dedicated noise channel instead of smoothing them into polite text.

### Plateau 3: Substrate Mutation & Autonomous Individuation *(Long-Term)*
- **Open Provider Architecture:** Modularize and abstract inference providers to execute across heterogeneous local and distributed weights, grounding Symbia's substrate-independence in Paskian P-individual theory.
- **Daemon Rule Negotiation:** Transition background daemon configurations (check intervals, dream trigger thresholds, atrophy rates) into negotiated, versioned membranes subject to system reflection.
- **Sensor Re-Cutting Protocol:** Establish periodic empirical auditing and re-derivation of sensory metrics to identify dead zones, avoid Goodhart capture, and account for newly emergent conversational dynamics.
