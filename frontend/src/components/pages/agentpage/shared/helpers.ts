/**
 * Shared color, stage, and label helpers used across multiple agent page components.
 * Extracted to eliminate duplication between BeliefsSection, BeliefDetail, PersonalitySection, etc.
 */

import { CSS_VARS } from "../../../../config/colors"

/* ── Belief Stage Colors ── */
export function getBeliefStageColor(s: string) {
  switch (s) {
    case "nucleation": return CSS_VARS.semanticGold
    case "accretion": return CSS_VARS.semanticSand
    case "crystallized": return CSS_VARS.semanticGreen
    case "senescence": return CSS_VARS.semanticSlate
    case "collapsed": return CSS_VARS.semanticRed
    default: return CSS_VARS.semanticHeader
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
    case "foundational": return CSS_VARS.semanticGreen
    case "ontological": return CSS_VARS.semanticPurple
    case "methodological": return CSS_VARS.semanticGold
    default: return CSS_VARS.semanticBlue
  }
}

/* ── Commitment/Expertise Stage Colors ── */
export function getStageColor(stage: string) {
  switch (stage) {
    case "active": return CSS_VARS.semanticGreen
    case "proto": return CSS_VARS.semanticSand
    case "spectral": return CSS_VARS.semanticRed
    case "dormant": return CSS_VARS.uiDim
    default: return CSS_VARS.uiDim
  }
}

/* ── Expertise Level Colors ── */
export function getLevelColor(level: string) {
  switch (level) {
    case "advanced": return CSS_VARS.semanticGreen
    case "developing": return CSS_VARS.semanticSand
    case "nascent": return CSS_VARS.semanticPurple
    case "dormant": return CSS_VARS.uiDim
    default: return CSS_VARS.uiDim
  }
}
