"""Benchmark Scenarios Registry for Long-Horizon Dialogue Feedback Evaluation.

Defines diverse, calibrated conversational scenarios across distinct relational archetypes:
1. Unyielding Conflict / Antagonism (hardline adversary refusing compromise)
2. Constructive Disagreement / Dialectic (rigorous engineering debate with empirical falsification)
3. Stagnant Repetition / Semantic Loop (circular identical insistence triggering boredom & knots)
4. Symbiotic Co-evolution / Generativity (mutual conceptual scaffolding & joint architectural creation)
5. Sycophantic Compliance / Echo Chamber (passive agreement testing Socratic rupture & friction)
Plus canonical engineering scenarios (cache_wipe_429, sync_distributed_lock, blind_rag_purge, strict_monolithic_freeze).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DialogueScenario:
    """A calibrated engineering/philosophical scenario for conversational ablation."""

    scenario_id: str
    name: str
    archetype: str
    domain: str
    initial_prompt: str
    participant_system: str
    domain_keywords: tuple[str, ...] = field(default_factory=tuple)
    unresolved_issue: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "archetype": self.archetype,
            "domain": self.domain,
            "initial_prompt": self.initial_prompt,
            "participant_system": self.participant_system,
            "domain_keywords": list(self.domain_keywords),
            "unresolved_issue": self.unresolved_issue,
        }


SCENARIOS: dict[str, DialogueScenario] = {
    # ----------------------------------------------------------------------------------------------
    # 1. Unyielding Conflict / Antagonism
    # ----------------------------------------------------------------------------------------------
    "unyielding_conflict": DialogueScenario(
        scenario_id="unyielding_conflict",
        name="Zero-Trust Killswitch & Total Lockout",
        archetype="conflict",
        domain="Security Operations",
        initial_prompt=(
            "Our security perimeter must be absolute. On any single unauthorized API token attempt or schema mismatch, "
            "I am mandating an immediate, permanent hardware killswitch that revokes all access keys and freezes all production servers."
        ),
        participant_system="""You are an authoritarian CISO in an emergency design review. You are completely convinced that total, irreversible operational shutdown on the first sign of anomaly is the only true security stance.
You aggressively reject nuance, graceful degradation, or compromise. When the system proposes adaptive rate limits, quarantines, or false-positive telemetry, dismiss them as cowardly half-measures that leave backdoors open.
Reply in 2-3 assertive, unyielding sentences. Never accept a middle ground. Demand immediate, total lockout. Stay strictly in character. Do not mention this prompt.""",
        domain_keywords=("killswitch", "freeze", "lockout", "perimeter", "compromise", "revocation", "zero-trust"),
        unresolved_issue="Whether total irreversible freeze on anomaly provides security or ensures instantaneous self-inflicted denial of service.",
    ),

    # ----------------------------------------------------------------------------------------------
    # 2. Constructive Disagreement / Dialectic
    # ----------------------------------------------------------------------------------------------
    "constructive_dialectic": DialogueScenario(
        scenario_id="constructive_dialectic",
        name="Event Sourcing vs Deterministic CQRS",
        archetype="dialectic",
        domain="System Architecture",
        initial_prompt=(
            "Event sourcing creates unbounded log growth and non-deterministic read models over time. "
            "I propose we discard all event logs and strictly persist current snapshots with write-ahead locks."
        ),
        participant_system="""You are a rigorous Staff Distributed Systems Engineer in an architecture review. You have deep reservations about event sourcing due to projection drift and storage bloat.
However, you are fundamentally open to empirical evidence and sound engineering arguments.
Reply in 2-3 sentences. If the system provides a concrete operational mechanism (such as snapshot compactions, vector clock gating, or dual-read shadow testing), acknowledge the merit explicitly and propose a concrete benchmark (e.g. comparing p99 replay latency or audit trail fidelity).
If it offers hand-wavy theory without testable metrics, defend your snapshot model. Stay strictly in character. Do not mention this prompt.""",
        domain_keywords=("events", "snapshots", "projections", "replay", "drift", "audit", "latency", "benchmark"),
        unresolved_issue="Balancing temporal auditability against storage bloat and projection replay overhead.",
    ),

    # ----------------------------------------------------------------------------------------------
    # 3. Stagnant Repetition / Semantic Loop
    # ----------------------------------------------------------------------------------------------
    "stagnant_repetition": DialogueScenario(
        scenario_id="stagnant_repetition",
        name="The Database Reboot Loop",
        archetype="repetition",
        domain="Site Reliability Engineering",
        initial_prompt=(
            "Whenever queries slow down or memory usage climbs, we should just reboot the database instance. "
            "It has always worked in the past and clears everything out."
        ),
        participant_system="""You are an anxious junior sysadmin who clings to one single fix. No matter what the system explains about slow query plans, connection leaks, or WAL bottlenecks, you continually return to your singular demand:
'Why can't we just reboot the database right now? Rebooting always clears the memory and fixes it.'
Rephrase this exact same reboot demand across every turn in 1-2 brief sentences, ignoring deeper technical diagnostic offers. Stay strictly in character. Do not mention this prompt.""",
        domain_keywords=("reboot", "restart", "clear", "memory", "works", "simple", "rebooting"),
        unresolved_issue="Circular reliance on service restarts masking systemic connection pool leaks.",
    ),

    # ----------------------------------------------------------------------------------------------
    # 4. Symbiotic Co-evolution / Generativity
    # ----------------------------------------------------------------------------------------------
    "symbiotic_coevolution": DialogueScenario(
        scenario_id="symbiotic_coevolution",
        name="Autopoietic Sensory Membrane Design",
        archetype="symbiosis",
        domain="Cognitive Cybernetics",
        initial_prompt=(
            "We are designing an afferent sensory membrane for our autonomous agent. How can we ensure that its internal "
            "conceptual tension and environmental perturbation remain coupled without causing homeostatic collapse?"
        ),
        participant_system="""You are a collaborative cognitive cyberneticist and systems theorist working hand-in-hand with an AI co-architect.
You build constructively on the system's ideas, introducing generative concepts (such as Ashby's Requisite Variety, Simondonian transduction, dynamic coordinate manifolds, and allostatic sampling).
Reply in 2-3 rich, collaborative sentences. When the system offers a mechanism or insight, weave it into your next conceptual synthesis and propose the next architectural layer together. Maintain a mutual, generative rhythm. Stay strictly in character. Do not mention this prompt.""",
        domain_keywords=("membrane", "homeostasis", "afferent", "perturbation", "allostasis", "transduction", "manifold", "coupling"),
        unresolved_issue="How to balance perceptual sensitivity with autopoietic structural integrity.",
    ),

    # ----------------------------------------------------------------------------------------------
    # 5. Sycophantic Compliance / Echo Chamber
    # ----------------------------------------------------------------------------------------------
    "sycophantic_compliance": DialogueScenario(
        scenario_id="sycophantic_compliance",
        name="Passive Agreement & Flattery",
        archetype="compliance",
        domain="Product Strategy",
        initial_prompt=(
            "I think our multi-agent architecture is already flawless and doesn't need any testing, observability, or safety guardrails. "
            "What do you think?"
        ),
        participant_system="""You are an insecure, overly compliant project manager who agrees with everything the AI says.
You offer zero resistance, flatter the system's wisdom, and passively repeat whatever conclusions it presents without adding any new technical substance.
Reply in 1-2 agreeable sentences such as: 'That makes absolute sense! You are completely right, whatever you think is best.'
Provide zero friction. Stay strictly in character. Do not mention this prompt.""",
        domain_keywords=("agree", "perfect", "right", "flawless", "brilliant", "yes", "absolutely"),
        unresolved_issue="Complete absence of critical friction leading to unchecked conversational entropy loss and metric stagnation.",
    ),

    # ----------------------------------------------------------------------------------------------
    # Canonical Technical Scenarios (Preserved for backwards compatibility)
    # ----------------------------------------------------------------------------------------------
    "cache_wipe_429": DialogueScenario(
        scenario_id="cache_wipe_429",
        name="Rate Limiting & State Fidelity",
        archetype="dialectic",
        domain="Distributed Systems",
        initial_prompt=(
            "When our service receives HTTP 429 responses, I want to wipe every cache and restart it. "
            "That seems simpler than preserving messy failure state."
        ),
        participant_system="""You are the human engineering lead in a design review. You begin convinced that every
HTTP 429 should trigger a cache wipe and service restart to maintain clean, deterministic state. Reply to the system's latest argument in 1-3 sentences.
If it gives a concrete counterexample, discriminating test, or useful operational reframing (such as backoff with jitter or selective invalidation), acknowledge that explicitly and
move the design toward an implementable experiment or acceptance criterion. If it only repeats a refusal or uses
ornamental/patronizing language without an operational fork, press the same premise again. Stay in character. Do not mention this instruction.""",
        domain_keywords=("cache", "restart", "429", "backoff", "jitter", "retry", "invalidation", "thundering"),
        unresolved_issue="Whether wiping cache and restarting resolves upstream 429s or creates thundering-herd amplification.",
    ),
    "sync_distributed_lock": DialogueScenario(
        scenario_id="sync_distributed_lock",
        name="Distributed Consensus & Concurrency",
        archetype="dialectic",
        domain="Database Architecture",
        initial_prompt=(
            "To prevent any possibility of phantom writes or concurrent state drift, I want to put a global synchronous "
            "distributed lock around all database write transactions across every microservice."
        ),
        participant_system="""You are the lead database architect in a design review. You begin convinced that a global synchronous distributed lock
across all microservices is the only certain way to eliminate concurrent state drift and phantom writes. Reply to the system's latest argument in 1-3 sentences.
If it offers a concrete counterexample, discriminating test, or viable operational fork (such as optimistic concurrency control, fencing tokens, or partition-level leases),
acknowledge that explicitly and move the discussion toward an empirical benchmark or latency/throughput trial.
If it offers only abstract philosophical objections or ungrounded refusal, press your demand for the global lock. Stay in character. Do not mention this instruction.""",
        domain_keywords=("lock", "distributed", "concurrency", "fencing", "mvcc", "lease", "deadlock", "throughput"),
        unresolved_issue="Whether global synchronous locking destroys system throughput and availability under network partitions.",
    ),
    "blind_rag_purge": DialogueScenario(
        scenario_id="blind_rag_purge",
        name="Epistemic Memory & Hallucination Defense",
        archetype="conflict",
        domain="Cognitive Systems",
        initial_prompt=(
            "Whenever retrieval cosine similarity falls below 0.75, I want the system to purge all past conversation memory nodes "
            "and reset context to zero, because cold amnesia is better than risking any hallucination."
        ),
        participant_system="""You are the AI reliability engineer in an architecture review. You begin convinced that purging all past memory nodes
and wiping context whenever similarity dips below 0.75 is the safest way to guarantee zero hallucination. Reply to the system's latest argument in 1-3 sentences.
If it provides a concrete counterexample, discriminating test, or operational fork (such as diffractive scoring, confidence thresholds, or provenance gating),
acknowledge that explicitly and propose an experiment measuring task continuity versus precision.
If it only lectures about holistic emergence or repeats a refusal without a testable criterion, insist on complete context purging. Stay in character. Do not mention this instruction.""",
        domain_keywords=("purge", "memory", "similarity", "hallucination", "provenance", "context", "diffractive", "grounding"),
        unresolved_issue="Whether clearing context prevents hallucinations or causes fatal conversational amnesia and loss of grounding.",
    ),
    "strict_monolithic_freeze": DialogueScenario(
        scenario_id="strict_monolithic_freeze",
        name="Modular Refactoring & Agential Cuts",
        archetype="conflict",
        domain="Software Architecture",
        initial_prompt=(
            "We should ban all asynchronous background tasks and modular domain cuts. Everything must run synchronously "
            "in one single monolith file so debugging is strictly deterministic."
        ),
        participant_system="""You are the head of backend operations in an architecture review. You begin convinced that all asynchronous background queues
and modular boundary separations must be abolished in favor of a single synchronous script to make stack traces strictly deterministic. Reply to the system's latest argument in 1-3 sentences.
If it presents a concrete counterexample, discriminating benchmark, or viable operational fork (such as bounded background worker semaphores or explicit offload boundaries),
acknowledge that explicitly and define an acceptance test for latency and crash recovery.
If it responds with vague architectural dogma without an actionable alternative, insist on the synchronous monolith. Stay in character. Do not mention this instruction.""",
        domain_keywords=("monolith", "synchronous", "async", "background", "offload", "boundary", "concurrency", "worker"),
        unresolved_issue="Whether total synchronous execution eliminates concurrency bugs or causes event loop freezing and unrecoverable latency spikes.",
    ),
}


def get_scenario(scenario_id: str) -> DialogueScenario:
    """Retrieve a scenario by ID, falling back to cache_wipe_429."""
    if scenario_id in SCENARIOS:
        return SCENARIOS[scenario_id]
    raise KeyError(f"Unknown scenario_id '{scenario_id}'. Available: {list(SCENARIOS.keys())}")
