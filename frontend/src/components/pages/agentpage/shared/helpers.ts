/**
 * Shared color, stage, and label helpers used across multiple agent page components.
 * Extracted to eliminate duplication between BeliefsSection, BeliefDetail, PersonalitySection, etc.
 */

/* ── Belief Stage Colors ── */
export function getBeliefStageColor(s: string) {
  switch (s) {
    case "nucleation": return "#f59e0b"
    case "accretion": return "#fb923c"
    case "crystallized": return "#4ade80"
    case "senescence": return "#94a3b8"
    case "collapsed": return "#ef4444"
    default: return "#6c6c8a"
  }
}

export function getBeliefStageLabel(s: string) {
  switch (s) {
    case "nucleation": return "nucleating"
    case "accretion": return "accreting"
    case "crystallized": return "crystallized"
    case "senescence": return "senescing"
    case "collapsed": return "collapsed"
    case "faded": return "faded"
    default: return s
  }
}

/* ── Belief Category Colors ── */
export function getCategoryColor(c: string) {
  switch (c?.toLowerCase()) {
    case "foundational": return "#4ade80"
    case "ontological": return "#a78bfa"
    case "methodological": return "#facc15"
    default: return "#60a5fa"
  }
}

/* ── Commitment/Expertise Stage Colors ── */
export function getStageColor(stage: string) {
  switch (stage) {
    case "active": return "#4ade80"
    case "proto": return "#f59e0b"
    case "spectral": return "#ef4444"
    case "dormant": return "#6b7280"
    default: return "#6c6c8a"
  }
}

/* ── Expertise Level Colors ── */
export function getLevelColor(level: string) {
  switch (level) {
    case "advanced": return "#4ade80"
    case "developing": return "#f59e0b"
    case "nascent": return "#6366f1"
    case "dormant": return "#6b7280"
    default: return "#888"
  }
}
