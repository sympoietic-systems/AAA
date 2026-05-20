# ADR-001: Personality Storage Strategy

**Date:** 2026-05-20
**Status:** accepted
**Deciders:** Vector, aaa project

## Context

The agent needs an identity definition — system prompt, personality traits,
voice characteristics, expertise declarations, core beliefs, and behavioral
responses. We must choose where to store this information now and how it
evolves through Phase 4.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **YAML file only** | Simple, human-editable, version-controllable, no DB dependency | Not queryable by the agent, manual edits only, no runtime introspection |
| **Database only** | Queryable by the agent, modifiable at runtime, single source of truth | Complex schema overhead, overkill for Phase 1 where identity is static |
| **YAML now → DB/graph later** | Start simple, migrate when the agent gains self-modification capability | Dual source of truth during transition window, needs migration script |

## Decision

**YAML file for Phase 1–3, migrate to graph database in Phase 4.**

Rationale:
- The agent cannot self-modify until Phase 4 (deterritorialization / belief
  recalibration). Until then, the identity is a static configuration best
  kept in version control.
- The migration path is clear: YAML fields map 1:1 to graph nodes.
  `expertise` entries become semantic knots with domain metadata.
  `beliefs` become foundational memory nodes subject to bifurcation.
- In Phase 3, expertise transitions from *declared* to *measured* — the
  agent's actual expertise becomes semantic knot density in a domain rather
  than a manually written list.

## Consequences

**Easier:**
- Editing and version-controlling identity definitions
- Sharing identity files between instances
- Diffing personality changes over time

**Harder:**
- No runtime query of identity or beliefs (not needed until Phase 4)
- Agent cannot introspect its own traits to explain its behavior

**Future migration path (Phase 4):**
1. `identity.yaml` fields become initial graph nodes
2. The agent can propose mutations to its identity
3. Conflicts trigger deterritorialization — a belief node collapses, the
   graph rewires, and the new topology is reflected in the agent's
   behavior
4. The YAML file becomes a bootstrap snapshot, not the live identity
