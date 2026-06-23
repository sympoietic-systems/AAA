/**
 * Unified Design System Color Tokens.
 * Single source of truth for all JS/TS logic, Canvas drawing, and CSS variable lookups.
 */

export const COLOR_PALETTE = {
  // Action state colors
  actionDim: "#b37e5d",
  actionHover: "#ff6b00",

  // Semantic palette (desaturated)
  semanticRed: "#b86a6a",
  semanticBlue: "#6b88a3",
  semanticGold: "#b89553",
  semanticPurple: "#8f7ba8",
  semanticGreen: "#5c9e7a",
  semanticSand: "#c48956",
  semanticSlate: "#78909c",
  tag: "#5f8776",
  semanticHeader: "#8a7d74",

  // Core UI tokens
  uiPrimary: "#ccc",
  uiSecondary: "#bbb",
  uiDim: "#555",
  uiBorder: "#222",
  uiBg: "#0a0a0c",
  uiGrid: "#111115",
  uiLinkResonance: "#3f3f4e",
  uiGuideRings: "#4a576d",

  // Agential/speaker variations
  humanBg: "#152a1d",
  apparatusBg: "#211a36",
} as const

/**
 * CSS Variable mappings for React component styles.
 * Using CSS variables allows styling to dynamically respond to index.css customizations.
 */
export const CSS_VARS = {
  actionDim: "var(--color-action-dim)",
  actionHover: "var(--color-action-hover)",
  semanticRed: "var(--color-semantic-red)",
  semanticBlue: "var(--color-semantic-blue)",
  semanticGold: "var(--color-semantic-gold)",
  semanticPurple: "var(--color-semantic-purple)",
  semanticGreen: "var(--color-semantic-green)",
  semanticSand: "var(--color-semantic-sand)",
  semanticSlate: "var(--color-semantic-slate)",
  tag: "var(--color-tag)",
  semanticHeader: "var(--color-semantic-header)",
  uiPrimary: "var(--color-ui-primary)",
  uiSecondary: "var(--color-ui-secondary)",
  uiDim: "var(--color-ui-dim)",
  uiBorder: "var(--color-ui-border)",
} as const
